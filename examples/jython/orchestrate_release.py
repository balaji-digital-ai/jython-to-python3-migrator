# Provision and launch a release from a Jython Script task, using the Release API
# objects (templateApi / phaseApi / taskApi / releaseApi). Shows the
# create-template -> add-phase -> add-task -> start-release flow end to end.
#
# The `com.xebialabs.xlrelease.*` API imports are valid in *both* Jython and the
# Python 3 client, so the migrator leaves them untouched - only the Python 2 print
# statements and the releaseVariables map accesses change.
from com.xebialabs.xlrelease.domain.release import Release
from com.xebialabs.xlrelease.domain.forms import CreateRelease

# Inputs come from this release's variable map.
appName = releaseVariables["appName"]
targetEnv = releaseVariables["targetEnv"]

# 1. Create a template to hold the new pipeline.
template = templateApi.createTemplate(Release(title="Deploy %s" % appName))
print "Created template", template.id

# 2. Add a phase to the template.
phase = phaseApi.addPhase(template.id, phaseApi.newPhase("Deploy to %s" % targetEnv))
print "Added phase", phase.title

# 3. Add a task to that phase.
task = taskApi.addTask(phase.id, taskApi.newTask("xlrelease.Task"))
print "Added task", task.id

# 4. Create a release from the template and start it.
release = templateApi.create(
    template.id, CreateRelease(releaseTitle="Deploy %s to %s" % (appName, targetEnv)))
releaseApi.start(release.id)
print "Started release", release.id
