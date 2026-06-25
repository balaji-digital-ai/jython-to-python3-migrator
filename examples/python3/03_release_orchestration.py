# Example 03 - Provisioning a release through the API objects
#
# Create template -> add phase -> add task -> start release, using the reserved API
# objects (templateApi / phaseApi / taskApi / releaseApi). The java.util.Date schedule
# is auto-converted to datetime, so this migrates with no markers left.

# Java classes, imported by their XL Release package names.
from com.xebialabs.xlrelease.domain import Release
from com.xebialabs.xlrelease.domain.status import ReleaseStatus
from com.xebialabs.xlrelease.api.v1.forms import CreateRelease
import datetime

# Seed a couple of sample inputs into the reserved releaseVariables map.
setReleaseVariable("appName", "petclinic")
setReleaseVariable("targetEnv", "production")

# Read the inputs back from the map.
appName = getReleaseVariable("appName")
targetEnv = getReleaseVariable("targetEnv")

# 1. Create a template (status must be TEMPLATE, with a scheduled start and due date).
scheduledStart = datetime.datetime.now(datetime.timezone.utc)
dueDate = scheduledStart + datetime.timedelta(milliseconds=7 * 24 * 60 * 60 * 1000)
template = templateApi.createTemplate(
    Release(
        title="Deploy %s" % appName,
        status=ReleaseStatus.TEMPLATE,
        scheduledStartDate=scheduledStart,
        dueDate=dueDate,
    ),
    None,
)
print("Created template", template.id)

# 2. Add a phase to the template.
phase = phaseApi.addPhase(template.id, phaseApi.newPhase("Deploy to %s" % targetEnv))
print("Added phase", phase.title)

# 3. Add a task to that phase.
task = taskApi.addTask(phase.id, taskApi.newTask("xlrelease.Task"))
print("Added task", task.id)

# 4. Create a release from the template and start it.
release = templateApi.create(
    template.id, CreateRelease(releaseTitle="Deploy %s to %s" % (appName, targetEnv)))
releaseApi.start(release.id)
print("Started release", release.id)
