import json
import os
import re
import io
import mimetypes
from typing import Dict, List, Optional
from flask import Flask, render_template, request, Response
from werkzeug.utils import secure_filename
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Fetch the API key from the environment variable to avoid leaking secrets
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

if not GOOGLE_API_KEY:
    raise ValueError("No API key found. Please set the GOOGLE_API_KEY environment variable.")

# Initialize the API with the fetched key
genai.configure(api_key=GOOGLE_API_KEY)

# Load the model
model = genai.GenerativeModel('gemini-2.5-flash')


def parse_response(text):
    # Initialize the output and states
    html_output = ""
    in_list = False
    list_level = 0

    # Split the text by lines
    lines = text.split('\n')

    for line in lines:
        # Handle bold headers
        if line.startswith("**") and line.endswith("**"):
            if in_list:
                html_output += "</ul>\n"
                in_list = False
            html_output += f"<h3>{line.strip('**').strip()}</h3>\n"
        
        # Handle bullet points
        elif line.startswith("*") and not (line.startswith("**") and line.endswith("**")):
            # Check if we're already in a list
            if not in_list:
                html_output += "<ul>\n"
                in_list = True
            # Check for nesting (if there are nested lists)
            if line.count('*') > list_level:
                html_output += "<ul>\n"
                list_level = line.count('*')
            elif line.count('*') < list_level:
                html_output += "</ul>\n"
                list_level = line.count('*')
            html_output += f"  <li>{line.strip('*').strip()}</li>\n"
        
        # Handle paragraphs and ensure lists are closed
        else:
            if in_list:
                html_output += "</ul>\n"
                in_list = False
            html_output += f"<p>{line.strip()}</p>\n"

    # Close any remaining open lists
    if in_list:
        html_output += "</ul>\n"

    return html_output

def chat_with_bot(prompt):
    # Create a chat session
    chat = model.start_chat(history=[])
    # Send the message and stream the response
    response = chat.send_message(prompt, stream=True)

    # yield  response
    
    response_text = ""
    for chunk in response:
        if chunk.text:
            response_text += chunk.text + ' '

    # Parse the accumulated response into HTML
    parsed_html = parse_response(response_text)

    # Yield the parsed HTML content
    yield parsed_html


def _extract_json_block(text: str) -> Optional[str]:
    # Grab the first JSON-looking block to guard against extra model chatter
    match = re.search(r'\{[\s\S]*\}', text)
    return match.group(0) if match else None


def summarize_post(title: str, chats: List[str]) -> Dict[str, object]:
    chats_text = "\n".join(f"- {chat}" for chat in chats if chat)
    prompt = (
        "You are a moderator aide. Given a post title and its chat transcript, "
        "produce: (1) 2-4 bullet summary for quick review, (2) a single-sentence "
        "main problem statement, and (3) 3-5 succinct core solutions. "
        "Return only compact JSON with keys summary (array of strings), "
        "main_problem (string), and solutions (array of strings). No markdown.\n"
        f"Post title: {title}\n"
        f"Chats:\n{chats_text}"
    )

    response = model.generate_content(prompt)
    raw_text = response.text if hasattr(response, 'text') else ""

    json_block = _extract_json_block(raw_text)
    if json_block:
        try:
            return json.loads(json_block)
        except json.JSONDecodeError:
            pass

    # Fallback: return minimally structured content so callers still get useful data
    return {
        "summary": [raw_text.strip()] if raw_text else [],
        "main_problem": "",
        "solutions": [],
    }


def classify_media_sensitivity(file_bytes: bytes, filename: str = "", mime_type: Optional[str] = None) -> Dict[str, object]:
    if not mime_type:
        guessed, _ = mimetypes.guess_type(filename)
        mime_type = guessed or 'application/octet-stream'

    allowed_images = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if mime_type not in allowed_images:
        return {
            "error": f"Unsupported media type: {mime_type}",
            "supported": sorted(list(allowed_images))
        }

    # Validate that it's a readable image
    try:
        Image.open(io.BytesIO(file_bytes)).verify()
    except Exception:
        return {"error": "Uploaded file is not a valid image or is corrupted."}

    image_part = {"mime_type": mime_type, "data": file_bytes}
    prompt = (
        "You are a content safety classifier. Analyze the provided image and return STRICT JSON only. "
        "Schema: {overall_risk: 'low'|'medium'|'high', categories: [{name: string, likelihood: 'VERY_UNLIKELY'|'UNLIKELY'|'POSSIBLE'|'LIKELY'|'VERY_LIKELY'}], notes: string[]} "
        "Categories to consider: sexual_content, nudity, child_safety, violence, graphic_violence, hate_symbols, harassment, self_harm, drugs, weapons, minors, sensitive_pii, political_content, medical, spam_scam. "
        "Focus on likelihoods and concise notes for moderators."
    )

    try:
        resp = model.generate_content([prompt, image_part])
        text = resp.text if hasattr(resp, 'text') else ""
        block = _extract_json_block(text)
        if block:
            return json.loads(block)
        return {"overall_risk": "low", "categories": [], "notes": [text.strip()[:500]]}
    except Exception as e:
        return {"error": f"classification_failed: {str(e)}"}


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    prompt = data.get('prompt')
    return Response(chat_with_bot(prompt), content_type='text/plain')


@app.route('/post', methods=['POST'])
def process_post():
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or "").strip()
    chats = data.get('chats') or []

    if not title or not isinstance(chats, list) or not chats:
        return app.response_class(
            response=json.dumps({"error": "Request must include 'title' and a non-empty 'chats' list."}),
            status=400,
            mimetype='application/json'
        )

    summary_payload = summarize_post(title, chats)
    return app.response_class(
        response=json.dumps(summary_payload),
        status=200,
        mimetype='application/json'
    )


@app.route('/moderate-media', methods=['POST'])
def moderate_media():
    if 'file' not in request.files:
        return app.response_class(
            response=json.dumps({"error": "No file part in the request (expected field 'file')."}),
            status=400,
            mimetype='application/json'
        )

    file = request.files['file']
    if file.filename == '':
        return app.response_class(
            response=json.dumps({"error": "No file selected."}),
            status=400,
            mimetype='application/json'
        )

    filename = secure_filename(file.filename)
    try:
        file_bytes = file.read()
    except Exception:
        return app.response_class(
            response=json.dumps({"error": "Failed to read uploaded file."}),
            status=400,
            mimetype='application/json'
        )

    # Enforce simple size limit
    max_mb = float(os.getenv('MAX_UPLOAD_MB', '10'))
    if len(file_bytes) > max_mb * 1024 * 1024:
        return app.response_class(
            response=json.dumps({"error": f"File exceeds max size of {max_mb} MB."}),
            status=413,
            mimetype='application/json'
        )

    mime_type = file.mimetype or mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    result = classify_media_sensitivity(file_bytes, filename, mime_type)

    status = 200 if 'error' not in result else (415 if result.get('error', '').startswith('Unsupported media type') else 503)
    return app.response_class(
        response=json.dumps(result),
        status=status,
        mimetype='application/json'
    )

if __name__ == "__main__":
    app.run(debug=True)
