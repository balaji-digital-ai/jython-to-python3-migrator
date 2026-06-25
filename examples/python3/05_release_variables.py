# Example 05 - The release, folder and global variable maps (guide section 8)
#
# Plain reads/writes become get*/set* helpers. The Java HashMap, augmented assignment,
# and iterating the map have no getter/setter form, so they are flagged ERROR/TODO.
# TODO[jython2py3] removed Java import `from java.util import HashMap`; replace its usages with a Python 3 equivalent (guide section 11)

# Seed the variables this example reads so it runs standalone.
setReleaseVariable("buildNumber", "42")
setReleaseVariable("targetEnv", "PROD")
setReleaseVariable("deployCount", 0)
setGlobalVariable("global.pipelineOwner", "platform-team")

# Read inputs straight from the release variable map.
buildNumber = getReleaseVariable("buildNumber")
targetEnv = getReleaseVariable("targetEnv")

# A java.util.HashMap does not run in the container ...
# ERROR[jython2py3] don't use Java in Python 3: `HashMap` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
legacyMeta = HashMap()
legacyMeta.put("build", buildNumber)

# ... a plain dict is the portable choice, stored back as a Map variable.
setReleaseVariable("buildMetadata", {"build": buildNumber, "env": targetEnv})

# Folder- and global-scoped maps; keys keep their folder. / global. prefix.
setFolderVariable("folder.lastGoodBuild", buildNumber)
owner = getGlobalVariable("global.pipelineOwner")

# Augmented assignment is a read and a write, so it has no single getter/setter form.
# TODO[jython2py3] augmented assignment on releaseVariables[...] is read+write; split into getReleaseVariable/setReleaseVariable (guide section 8)
releaseVariables["deployCount"] += 1

# Iterating the whole map has no getter/setter form either.
# TODO[jython2py3] `releaseVariables` has no direct getter/setter form here; rewrite this use with getReleaseVariable/setReleaseVariable by hand (guide section 8)
for varName in releaseVariables:
    print("configured variable:", varName)

print("Recorded build", buildNumber, "for", owner)
