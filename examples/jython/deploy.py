# A representative Jython (xlrelease.ScriptTask) script exercising several
# migration rules at once. Run it through the migrator to see the result:
#     jython2py3 migrate examples/jython/deploy.py -o examples/python3/deploy.py
from java.util import Date
from xlrelease.HttpRequest import HttpRequest

print "Release:", release.title, "status", release.status

build = releaseVariables["buildNumber"]
releaseVariables["artifactPath"] = "/builds/%s/app.jar" % build

for t in releaseApi.getActiveTasks(release.id):
    print "active task:", t.title

response = HttpRequest({"url": "https://api.example.com"}).get("/health")
if not response.isSuccessful():
    raise Exception("Health check failed: %d" % response.getStatus())

result = "deployed " + build
