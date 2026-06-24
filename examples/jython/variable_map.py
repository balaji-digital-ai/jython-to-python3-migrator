# Work with the Jython variable maps - release, folder and global. Each plain
# read/write becomes the matching get*/set* helper in Python 3. The Java HashMap
# and the augmented assignment have no one-to-one container equivalent, so they are
# flagged (ERROR and TODO respectively) for a human to resolve.
from java.util import HashMap

# Read inputs straight from the release variable map.
buildNumber = releaseVariables["buildNumber"]
targetEnv = releaseVariables["targetEnv"]

# The Jython way to build a map value (java.util.HashMap) - does not run in the
# container ...
legacyMeta = HashMap()
legacyMeta.put("build", buildNumber)

# ... a plain dict is the portable choice, stored back as a Map variable.
releaseVariables["buildMetadata"] = {"build": buildNumber, "env": targetEnv}

# Folder- and global-scoped variables use their own maps.
folderVariables["lastGoodBuild"] = buildNumber
owner = globalVariables["pipelineOwner"]

# A running counter: augmented assignment is a read *and* a write, so it cannot
# collapse into a single getter/setter call.
releaseVariables["deployCount"] += 1

print "Recorded build", buildNumber, "for", owner
