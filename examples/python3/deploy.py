# A representative Jython (xlrelease.ScriptTask) script exercising several
# migration rules at once. Run it through the migrator to see the result:
#     jython2py3 migrate examples/jython/deploy.py -o examples/python3/deploy.py
release = getCurrentRelease()
# TODO[jython2py3] removed Java import `from java.util import Date`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Jython import `from xlrelease.HttpRequest import HttpRequest`; use the `requests` library instead (guide section 9)

print("Release:", release.title, "status", release.status)

build = getReleaseVariable("buildNumber")
setReleaseVariable("artifactPath", "/builds/%s/app.jar" % build)

for t in releaseApi.getActiveTasks(release.id):
    print("active task:", t.title)

# TODO[jython2py3] rewrite this HttpRequest call using the `requests` library (guide section 9)
response = HttpRequest({"url": "https://api.example.com"}).get("/health")
if not response.isSuccessful():
    raise Exception("Health check failed: %d" % response.getStatus())

result = "deployed " + build
