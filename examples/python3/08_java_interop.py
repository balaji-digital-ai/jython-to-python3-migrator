# Example 08 - Java interoperability (guide section 11)
#
# A grab-bag of the Java standard-library classes Release scripts commonly reach for.
# None of it runs in the Python 3 container: there is no JVM, so the migrator drops
# every `from java.* import ...` line (leaving a TODO breadcrumb) and stamps each Java
# *use* with an ERROR. Rewrite each block with its Python equivalent - `datetime`,
# `dict`, `list`, `uuid`, `hashlib`, `re`, `decimal`, `os.environ` and so on.
# TODO[jython2py3] removed Java import `from java.util import Date, Calendar`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.text import SimpleDateFormat`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.util import Properties`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.util import Arrays`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.util import UUID`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.security import MessageDigest`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.util.regex import Pattern`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.math import BigDecimal`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.lang import System`; replace its usages with a Python 3 equivalent (guide section 11)

# Dates and formatting -> Python's `datetime`.
# ERROR[jython2py3] don't use Java in Python 3: `Date` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
now = Date()
# ERROR[jython2py3] don't use Java in Python 3: `SimpleDateFormat` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
formatter = SimpleDateFormat("yyyy-MM-dd HH:mm")
stamp = formatter.format(now)

# Calendar arithmetic -> `datetime` + `timedelta`. Both the factory call and the
# constant reference are Java.
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

# UUID -> the `uuid` module.
# ERROR[jython2py3] don't use Java in Python 3: `UUID` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
requestId = UUID.randomUUID().toString()

# Message digests -> `hashlib`. (`"DigitalAI".getBytes()` is a Java method on a string.)
# ERROR[jython2py3] don't use Java in Python 3: `MessageDigest` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
digester = MessageDigest.getInstance("MD5")
digester.update("DigitalAI".getBytes())
checksum = digester.digest()

# Regular expressions -> the `re` module.
# ERROR[jython2py3] don't use Java in Python 3: `Pattern` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
matcher = Pattern.compile("\\d+").matcher("Build123")
if matcher.find():
    print("first number:", matcher.group())

# Arbitrary-precision decimals -> the `decimal` module.
# ERROR[jython2py3] don't use Java in Python 3: `BigDecimal` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
total = BigDecimal("12.50").add(BigDecimal("7.25"))

# Environment and system properties -> `os.environ` / the `platform` module.
# ERROR[jython2py3] don't use Java in Python 3: `System` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
print("JAVA_HOME:", System.getenv("JAVA_HOME"))
# ERROR[jython2py3] don't use Java in Python 3: `System` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
print("OS:", System.getProperty("os.name"))

print("Report generated at", stamp, "for", environment, "->", total)
# A fully-qualified Java reference written inline is flagged just the same.
# ERROR[jython2py3] don't use Java in Python 3: `java.text.SimpleDateFormat` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
print("Follow-up due", java.text.SimpleDateFormat("yyyy-MM-dd").format(nextWeek))
