# Generative AI Chatbot with Flask
## Description
This project is a simple web application using Flask that integrates with Google’s Generative AI to generate responses based on user input. It processes the AI’s output and renders it as HTML, supporting basic formatting like headers, bullet points, and paragraphs.

## Features
1. Interact with a generative AI model using a web interface.
2. Converts the AI-generated text into formatted HTML.
3. Supports headers, bullet points, and nested lists.

## Installation
Follow these steps to set up the project locally:

1. Clone the Repository:

Copy code
' git clone https://github.com/Rojeets/Chat-bot.git '
' cd Chat-bot '


2. Set Up a Virtual Environment:

Copy code
'python -m venv venv'
# on linux 
'source venv/bin/activate ' 
# On Windows use 
'venv\Scripts\activate'


3. Install Dependencies:

Copy code
'pip install -r requirements.txt'


4. Set Up Environment Variables:

Ensure you have the Google API key set up in your environment. You can set the environment variable directly or include it in a .env file.
Copy code
" export GOOGLE_API_KEY='your-google-api-key-here' "


5. Run the Application:

Copy code
'python app.py'
** The application will be running at http://127.0.0.1:5000/. **

## Usage
1. Navigate to the Web Interface:

Open your browser and go to http://127.0.0.1:5000/.

2. Chat with the Bot:

Send a POST request to /chat with JSON payload:

Copy code
{
  "prompt": "Your question or message here"
}
You can use tools like Postman or write a simple HTML form to interact with this endpoint.

## Code Explanation
app.py: The main application file which sets up Flask, initializes the Generative AI model, and defines routes for rendering the home page and handling chat requests.
parse_response(text): Parses the AI-generated text into HTML, handling headers, bullet points, and nested lists.
chat_with_bot(prompt): Manages the chat session with the AI model and streams the response.


## Contributing
1. Fork the repository.
2. Create a new branch (git checkout -b feature-branch).
3. Make your changes.
4. Commit your changes (git commit -am 'Add new feature').
5. Push to the branch (git push origin feature-branch).
6. Create a new Pull Request.


## Contact
For any questions or feedback, you can reach out to pokharelrojit45@gmail.com.

