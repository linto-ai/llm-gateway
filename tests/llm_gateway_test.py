# curl -X POST
# "http://localhost:8001/keyword_extraction" -H "accept: application/json"
# -H "Content-Type: application/json" -d @tests/keyword.json


import requests
import json

url = "http://localhost:8000"
headers = {"accept": "application/json"}
with open("tests/summarization.json", "r") as file:
    data = json.load(file)

jobid = requests.post(url+"/services/mixtral/generate", json=data, headers=headers)
print(jobid.text)