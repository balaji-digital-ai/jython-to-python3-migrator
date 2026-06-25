# Example 09 - A representative deploy task exercising several rules at once.
#
# A capstone that mixes a Java import (removed, with a breadcrumb), an HttpRequest
# call (flagged TODO), reserved objects, releaseVariables read/write, an API loop and a
# `result` output - the kind of script a real migration runs into. See the per-concern
# examples above for each rule in isolation.
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
