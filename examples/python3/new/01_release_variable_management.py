# Migrated from Jython by jython2py3 v0.1.0.
# Search "# TODO[jython2py3]" / "# ERROR[jython2py3]" for items needing review;
# safe (Tier-1) transforms were applied silently.

# Jython Script Task Sample
release = getCurrentRelease()
print("=== Build Validation ===")

print("Release: %s" % release.title)

buildNumber = getReleaseVariable("buildNumber")
environment = getReleaseVariable("environment")

artifactPath = "/artifacts/%s/application.zip" % buildNumber
setReleaseVariable("artifactPath", artifactPath)

if environment == "production":
    setReleaseVariable("approvalRequired", True)
else:
    setReleaseVariable("approvalRequired", False)

print("Artifact Path: %s" % artifactPath)
