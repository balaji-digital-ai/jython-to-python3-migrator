# Example 08 - Java interoperability (guide section 11)
#
# A grab-bag of the Java standard-library classes Release scripts commonly reach for.
# None of it runs in the Python 3 container: there is no JVM, so the migrator drops
# every `from java.* import ...` line (leaving a TODO breadcrumb) and stamps each Java
# *use* with an ERROR. Rewrite each block with its Python equivalent - `datetime`,
# `dict`, `list`, `uuid`, `hashlib`, `re`, `decimal`, `os.environ` and so on.
from java.util import Date, Calendar
from java.text import SimpleDateFormat
from java.util import Properties
from java.util import Arrays
from java.util import UUID
from java.security import MessageDigest
from java.util.regex import Pattern
from java.math import BigDecimal
from java.lang import System

# Dates and formatting -> Python's `datetime`.
now = Date()
formatter = SimpleDateFormat("yyyy-MM-dd HH:mm")
stamp = formatter.format(now)

# Calendar arithmetic -> `datetime` + `timedelta`. Both the factory call and the
# constant reference are Java.
calendar = Calendar.getInstance()
calendar.add(Calendar.DAY_OF_MONTH, 7)
nextWeek = calendar.getTime()

# Properties -> a plain dict.
props = Properties()
props.setProperty("environment", "QA")
environment = props.getProperty("environment")

# Fixed-size arrays -> a list.
servers = Arrays.asList("DEV", "QA", "UAT", "PROD")

# UUID -> the `uuid` module.
requestId = UUID.randomUUID().toString()

# Message digests -> `hashlib`. (`"DigitalAI".getBytes()` is a Java method on a string.)
digester = MessageDigest.getInstance("MD5")
digester.update("DigitalAI".getBytes())
checksum = digester.digest()

# Regular expressions -> the `re` module.
matcher = Pattern.compile("\\d+").matcher("Build123")
if matcher.find():
    print "first number:", matcher.group()

# Arbitrary-precision decimals -> the `decimal` module.
total = BigDecimal("12.50").add(BigDecimal("7.25"))

# Environment and system properties -> `os.environ` / the `platform` module.
print "JAVA_HOME:", System.getenv("JAVA_HOME")
print "OS:", System.getProperty("os.name")

print "Report generated at", stamp, "for", environment, "->", total
# A fully-qualified Java reference written inline is flagged just the same.
print "Follow-up due", java.text.SimpleDateFormat("yyyy-MM-dd").format(nextWeek)
