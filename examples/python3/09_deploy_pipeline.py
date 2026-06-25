# Example 09 - A representative deploy task exercising several rules at once.
#
# A capstone mixing a Java import (removed, with a breadcrumb), an HttpRequest call
# (flagged TODO), reserved objects, a releaseVariables read/write, an API loop and a
# result output - the kind of script a real migration runs into.
release = getCurrentRelease()
# TODO[jython2py3] removed Java import `from java.util import HashMap`; replace its usages with a Python 3 equivalent (guide section 11)

print("Release:", release.title, "status", release.status)

# Seed the variable this example reads so it runs standalone.
setReleaseVariable("buildNumber", "42")

build = getReleaseVariable("buildNumber")
setReleaseVariable("artifactPath", "/builds/%s/app.jar" % build)

for t in releaseApi.getActiveTasks(release.id):
    print("active task:", t.title)

# TODO[jython2py3] rewrite this HttpRequest call using the `requests` library (guide section 9)
response = HttpRequest({"url": "https://www.githubstatus.com"}).get("/api/v2/status.json")
if not response.isSuccessful():
    raise Exception("Health check failed: %d" % response.getStatus())

result = "deployed " + build
