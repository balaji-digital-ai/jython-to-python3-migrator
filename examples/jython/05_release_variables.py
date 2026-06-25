# Example 05 - The release, folder and global variable maps (guide section 8)
#
# Plain reads/writes become get*/set* helpers. The Java HashMap, augmented assignment,
# and iterating the map have no getter/setter form, so they are flagged ERROR/TODO.
from java.util import HashMap

# Seed the variables this example reads so it runs standalone.
releaseVariables["buildNumber"] = "42"
releaseVariables["targetEnv"] = "PROD"
releaseVariables["deployCount"] = 0
globalVariables["global.pipelineOwner"] = "platform-team"

# Read inputs straight from the release variable map.
buildNumber = releaseVariables["buildNumber"]
targetEnv = releaseVariables["targetEnv"]

# A java.util.HashMap does not run in the container ...
legacyMeta = HashMap()
legacyMeta.put("build", buildNumber)

# ... a plain dict is the portable choice, stored back as a Map variable.
releaseVariables["buildMetadata"] = {"build": buildNumber, "env": targetEnv}

# Folder- and global-scoped maps; keys keep their folder. / global. prefix.
folderVariables["folder.lastGoodBuild"] = buildNumber
owner = globalVariables["global.pipelineOwner"]

# Augmented assignment is a read and a write, so it has no single getter/setter form.
releaseVariables["deployCount"] += 1

# Iterating the whole map has no getter/setter form either.
for varName in releaseVariables:
    print "configured variable:", varName

print "Recorded build", buildNumber, "for", owner
