# Work with the Jython variable maps - release, folder and global. Each plain
# read/write becomes the matching get*/set* helper in Python 3. The Java HashMap, the
# augmented assignment, and iterating the map itself have no one-to-one container
# equivalent, so they are flagged (ERROR and TODOs respectively) for a human to resolve.
# TODO[jython2py3] removed Java import `from java.util import HashMap`; replace its usages with a Python 3 equivalent (guide section 11)

# Read inputs straight from the release variable map.
buildNumber = getReleaseVariable("buildNumber")
targetEnv = getReleaseVariable("targetEnv")

# The Jython way to build a map value (java.util.HashMap) - does not run in the
# container ...
# ERROR[jython2py3] don't use Java in Python 3: `HashMap` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
legacyMeta = HashMap()
legacyMeta.put("build", buildNumber)

# ... a plain dict is the portable choice, stored back as a Map variable.
setReleaseVariable("buildMetadata", {"build": buildNumber, "env": targetEnv})

# Folder- and global-scoped variables use their own maps.
setFolderVariable("lastGoodBuild", buildNumber)
owner = getGlobalVariable("pipelineOwner")

# A running counter: augmented assignment is a read *and* a write, so it cannot
# collapse into a single getter/setter call.
# TODO[jython2py3] augmented assignment on releaseVariables[...] is read+write; split into getReleaseVariable/setReleaseVariable (guide section 8)
releaseVariables["deployCount"] += 1

# Iterating the map itself (rather than a single key) has no getter/setter form, so
# the whole loop header is flagged for a manual rewrite.
# TODO[jython2py3] `releaseVariables` has no direct getter/setter form here; rewrite this use with getReleaseVariable/setReleaseVariable by hand (guide section 8)
for varName in releaseVariables:
    print("configured variable:", varName)

print("Recorded build", buildNumber, "for", owner)
