# Example 05 - The release, folder and global variable maps (guide section 8)
#
# Each plain read/write becomes the matching get*/set* helper in Python 3. The Java
# HashMap, the augmented assignment, and iterating the map itself have no one-to-one
# container equivalent, so they are flagged (ERROR and TODOs respectively) for a human
# to resolve.
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

# Folder- and global-scoped variables use their own maps; their keys carry the
# required `folder.` / `global.` prefix (guide section 8), which the rewrite preserves.
folderVariables["folder.lastGoodBuild"] = buildNumber
owner = globalVariables["global.pipelineOwner"]

# A running counter: augmented assignment is a read *and* a write, so it cannot
# collapse into a single getter/setter call.
releaseVariables["deployCount"] += 1

# Iterating the map itself (rather than a single key) has no getter/setter form, so
# the whole loop header is flagged for a manual rewrite.
for varName in releaseVariables:
    print "configured variable:", varName

print "Recorded build", buildNumber, "for", owner
