from flask import Flask, request
import requests
from transformers import AutoTokenizer

app = Flask(__name__)
tokenizer = AutoTokenizer.from_pretrained("TheBloke/Vigostral-7B-Chat-AWQ")


import nltk
nltk.download('punkt')
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
        return 'File content: ' + str(get_chunks(text)), 200


def get_chunks(content):
    sentences = nltk.tokenize.sent_tokenize(content)
    print(max([len(tokenizer.tokenize(sentence)) for sentence in sentences]))

    # TODO: vig  
    #tokenizer_context_len = tokenizer.max_len_single_sentence
    tokenizer_context_len = 10

    length = 0
    chunk = ""
    chunks = []
    count = -1
    for sentence in sentences:
        count += 1
        combined_length = len(tokenizer.tokenize(sentence)) + length # add the no. of sentence tokens to the length counter

        if combined_length  <= tokenizer_context_len: # if it doesn't exceed
            chunk += sentence + " " # add the sentence to the chunk
            length = combined_length # update the length counter

            # if it is the last sentence
            if count == len(sentences) - 1:
                chunks.append(chunk.strip()) # save the chunk
            
        else: 
            chunks.append(chunk.strip()) # save the chunk
            # reset 
            length = 0 
            chunk = ""

            # take care of the overflow sentence
            chunk += sentence + " "
            length = len(tokenizer.tokenize(sentence))
    return chunks



if __name__ == '__main__':
    FileContent = """Vous êtes un chargé de mission hautement qualifié. Vous rédigez des comptes rendus de réunions et de conférences avec des interlocuteurs extérieurs qui sont diffusés aux hauts fonctionnaires. Vous utilisez toujours les conventions orthographiques du français. Vous attachez de l'importance à une écriture correcte et formelle. Vous écrivez de manière concise tout en offrant une lecture agréable. 
    Sur la base de la transcription de la conférence, vous rédigerez le procès-verbal en suivant ces lignes directrices :
    fournir un résumé de la transcription qui soit détaillé, complet, approfondi et complexe, tout en restant clair et concis.
    intégrer les idées principales et les informations essentielles, en éliminant les éléments superflus et en se concentrant sur les aspects critiques
    Toujours attribuer les idées et les informations essentielles au locuteur, à l'orateur ou au participant concerné. Chaque tour de parole est présenté sous une forme "spk1 : 00:0.00 - 00:15.22 :" suivi de la transcription attribuée. Ici spk1 est le nom du locuteur suivi de l'horodatage de ses propos.
    S'appuyer strictement sur la transcription fournie en entrée sans inclure d'informations externes.
    Présenter le résumé sous forme de paragraphes pour en faciliter la compréhension.
    à la fin du compte rendu, fournir les points d'action clés ou les conclusions de la réunion ou de la conférence.
    la transcription à traiter est fournie ci après entre trois `"""
    #print(get_chunks(FileContent))
    app.run(port=5000)


