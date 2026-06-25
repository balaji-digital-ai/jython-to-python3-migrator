# Jython Script Task Sample
print "=== Build Validation ==="

print "Release: %s" % release.title

buildNumber = releaseVariables["buildNumber"]
environment = releaseVariables["environment"]

artifactPath = "/artifacts/%s/application.zip" % buildNumber
releaseVariables["artifactPath"] = artifactPath

if environment == "production":
    releaseVariables["approvalRequired"] = True
else:
    releaseVariables["approvalRequired"] = False

print "Artifact Path: %s" % artifactPath
