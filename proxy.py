from flask import Flask, request
import requests
from chunker import get_chunks, get_prompts

app = Flask(__name__)


# Tokenizer instance of polymorphic class to select appropriate tokenizer ?

#@app.route('/summarize', methods=['GET'])
# Read the text file.
# Tokenize the text from file.
# Initialize a string with the prompt. TO DEFINE
# Add tokens to the prompt until reaching the max token context size.
# Make a 1st LLM API call, get summarized result
# Intialize a string with a new rollingPrompt : TO DEFINE
# While there are still tokens left:
  # Make a request to the LLM API with the rollingPrompt.
  # Get the response from the API and add it to rollingPrompt
  # Remove the used tokens from the intial text text list.
# interate
# Return the final prompt (which now includes the summarized text).

@app.route('/summarize', methods=['POST'])
def summarize_file():
    if 'file' not in request.files:
        return 'No file part in the request', 400
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400
    if file:
        text = file.read().decode('utf-8')
        chunks = get_chunks(text)
        intermediate_prompts = get_prompts(chunks)
        return 'File content: ' + str(intermediate_prompts), 200



if __name__ == '__main__':
    app.run(port=5000)


