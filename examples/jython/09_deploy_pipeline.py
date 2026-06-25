# Example 09 - A representative deploy task exercising several rules at once.
#
# A capstone that mixes a Java import (removed, with a breadcrumb), an HttpRequest
# call (flagged TODO), reserved objects, releaseVariables read/write, an API loop and a
# `result` output - the kind of script a real migration runs into. See the per-concern
# examples above for each rule in isolation.
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
