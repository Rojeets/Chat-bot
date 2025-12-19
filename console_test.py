#Initialize Generative-AI
from pyexpat import model
import google.generativeai as genai
import os

#Initialize the Gemini API with your API Key 
GOOGLE_API_KEY=os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("No API key found. Please set the GOOGLE_API_KEY environment variable.")
genai.configure(api_key=GOOGLE_API_KEY)

#list models of Gemini
# for m in genai.list_models():
#   if 'generateContent' in m.supported_generation_methods:
#     print(m.name)

#Load model
model= genai.GenerativeModel('gemini-1.0-pro-latest')

# Create a chat session
chat=model.start_chat(history=[])

while True:
    prompt = input("Ask me anything: ")
    if (prompt == "exit"):
        break
    response = chat.send_message(prompt, stream=True)
    for chunk in response:
        if chunk.text:
          print(chunk.text)