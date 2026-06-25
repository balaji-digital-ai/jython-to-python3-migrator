# Example 09 - A representative deploy task exercising several rules at once.
#
# A capstone mixing a Java import (removed, with a breadcrumb), an HttpRequest call
# (flagged TODO), reserved objects, a releaseVariables read/write, an API loop and a
# result output - the kind of script a real migration runs into.
from java.util import HashMap

print "Release:", release.title, "status", release.status

# Seed the variable this example reads so it runs standalone.
releaseVariables["buildNumber"] = "42"

build = releaseVariables["buildNumber"]
releaseVariables["artifactPath"] = "/builds/%s/app.jar" % build

for t in releaseApi.getActiveTasks(release.id):
    print "active task:", t.title

response = HttpRequest({"url": "https://www.githubstatus.com"}).get("/api/v2/status.json")
if not response.isSuccessful():
    raise Exception("Health check failed: %d" % response.getStatus())

result = "deployed " + build
