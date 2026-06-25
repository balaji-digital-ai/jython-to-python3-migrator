# Example 08 - Java interoperability (guide section 11)
#
# A grab-bag of Java standard-library classes Release scripts reach for. None run in
# the Python 3 container (no JVM), so the migrator drops every from java.* import
# (TODO breadcrumb) and stamps each Java use with an ERROR. Rewrite each block with its
# Python equivalent - datetime, dict, list, uuid, re, decimal.
# TODO[jython2py3] removed Java import `import java`; replace its usages with a Python 3 equivalent (guide section 11)
import datetime
# TODO[jython2py3] removed Java import `from java.util import Calendar`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.text import SimpleDateFormat`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.util import Properties`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.util import Arrays`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.util import UUID`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.util.regex import Pattern`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.math import BigDecimal`; replace its usages with a Python 3 equivalent (guide section 11)

# Dates and formatting -> Python's datetime.
now = datetime.datetime.now(datetime.timezone.utc)
# ERROR[jython2py3] don't use Java in Python 3: `SimpleDateFormat` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
formatter = SimpleDateFormat("yyyy-MM-dd HH:mm")
stamp = formatter.format(now)

# Calendar arithmetic -> datetime + timedelta.
# ERROR[jython2py3] don't use Java in Python 3: `Calendar` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
calendar = Calendar.getInstance()
# ERROR[jython2py3] don't use Java in Python 3: `Calendar` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
calendar.add(Calendar.DAY_OF_MONTH, 7)
nextWeek = calendar.getTime()

# Properties -> a plain dict.
# ERROR[jython2py3] don't use Java in Python 3: `Properties` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
props = Properties()
props.setProperty("environment", "QA")
environment = props.getProperty("environment")

# Fixed-size arrays -> a list.
# ERROR[jython2py3] don't use Java in Python 3: `Arrays` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
servers = Arrays.asList("DEV", "QA", "UAT", "PROD")

# UUID -> the uuid module.
# ERROR[jython2py3] don't use Java in Python 3: `UUID` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
requestId = UUID.randomUUID().toString()

# Regular expressions -> the re module.
# ERROR[jython2py3] don't use Java in Python 3: `Pattern` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
matcher = Pattern.compile("\\d+").matcher("Build123")
if matcher.find():
    print("first number:", matcher.group())

# Arbitrary-precision decimals -> the decimal module.
# ERROR[jython2py3] don't use Java in Python 3: `BigDecimal` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
total = BigDecimal("12.50").add(BigDecimal("7.25"))

print("Report generated at", stamp, "for", environment, "->", total)
# A fully-qualified Java reference written inline is flagged just the same.
# ERROR[jython2py3] don't use Java in Python 3: `java.text.SimpleDateFormat` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
print("Follow-up due", java.text.SimpleDateFormat("yyyy-MM-dd").format(nextWeek))
