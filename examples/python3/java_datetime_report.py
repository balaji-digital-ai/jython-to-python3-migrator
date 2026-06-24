# A reporting script that leans on the Java standard library for date handling.
# None of it runs in the Python 3 container, so the migrator drops the imports
# (leaving breadcrumbs) and stamps every Java use with an ERROR - rewrite the whole
# block with Python's `datetime` module.
# TODO[jython2py3] removed Java import `from java.util import Date, Calendar`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.text import SimpleDateFormat`; replace its usages with a Python 3 equivalent (guide section 11)

# `Date` and `SimpleDateFormat` are Java classes: each use is flagged.
# ERROR[jython2py3] don't use Java in Python 3: `Date` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
now = Date()
# ERROR[jython2py3] don't use Java in Python 3: `SimpleDateFormat` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
formatter = SimpleDateFormat("yyyy-MM-dd HH:mm")
stamp = formatter.format(now)

# `Calendar` too - both the factory call and the constant reference are Java.
# ERROR[jython2py3] don't use Java in Python 3: `Calendar` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
calendar = Calendar.getInstance()
# ERROR[jython2py3] don't use Java in Python 3: `Calendar` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
calendar.add(Calendar.DAY_OF_MONTH, 7)
nextWeek = calendar.getTime()

print("Report generated at", stamp)
# A fully-qualified Java reference written inline is flagged just the same.
# ERROR[jython2py3] don't use Java in Python 3: `java.text.SimpleDateFormat` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
print("Follow-up due", java.text.SimpleDateFormat("yyyy-MM-dd").format(nextWeek))
