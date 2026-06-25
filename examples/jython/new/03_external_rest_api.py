from xlrelease.HttpRequest import HttpRequest
import json

params = {"url": "https://jsonplaceholder.typicode.com"}

request = HttpRequest(params)
response = request.get("/todos/1")

print response.getStatus()

if response.isSuccessful():
    data = json.loads(response.getResponse())
    releaseVariables["todoTitle"] = data["title"]
else:
    raise Exception("Request Failed")
