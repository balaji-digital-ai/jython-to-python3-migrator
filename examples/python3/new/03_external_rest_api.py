# Migrated from Jython by jython2py3 v0.1.0.
# Search "# TODO[jython2py3]" / "# ERROR[jython2py3]" for items needing review;
# safe (Tier-1) transforms were applied silently.

# TODO[jython2py3] removed Jython import `from xlrelease.HttpRequest import HttpRequest`; use the `requests` library instead (guide section 9)
import json

params = {"url": "https://jsonplaceholder.typicode.com"}

# TODO[jython2py3] rewrite this HttpRequest call using the `requests` library (guide section 9)
request = HttpRequest(params)
response = request.get("/todos/1")

print(response.getStatus())

if response.isSuccessful():
    data = json.loads(response.getResponse())
    setReleaseVariable("todoTitle", data["title"])
else:
    raise Exception("Request Failed")
