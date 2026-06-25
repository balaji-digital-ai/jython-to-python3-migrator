# Example 08 - Java interoperability (guide section 11)
#
# A grab-bag of Java standard-library classes Release scripts reach for. None run in
# the Python 3 container (no JVM), so the migrator drops every from java.* import
# (TODO breadcrumb) and stamps each Java use with an ERROR. Rewrite each block with its
# Python equivalent - datetime, dict, list, uuid, re, decimal.
import java
from java.util import Date
from java.util import Calendar
from java.text import SimpleDateFormat
from java.util import Properties
from java.util import Arrays
from java.util import UUID
from java.util.regex import Pattern
from java.math import BigDecimal

# Dates and formatting -> Python's datetime.
now = Date()
formatter = SimpleDateFormat("yyyy-MM-dd HH:mm")
stamp = formatter.format(now)

# Calendar arithmetic -> datetime + timedelta.
calendar = Calendar.getInstance()
calendar.add(Calendar.DAY_OF_MONTH, 7)
nextWeek = calendar.getTime()

# Properties -> a plain dict.
props = Properties()
props.setProperty("environment", "QA")
environment = props.getProperty("environment")

# Fixed-size arrays -> a list.
servers = Arrays.asList("DEV", "QA", "UAT", "PROD")

# UUID -> the uuid module.
requestId = UUID.randomUUID().toString()

# Regular expressions -> the re module.
matcher = Pattern.compile("\\d+").matcher("Build123")
if matcher.find():
    print "first number:", matcher.group()

# Arbitrary-precision decimals -> the decimal module.
total = BigDecimal("12.50").add(BigDecimal("7.25"))

print "Report generated at", stamp, "for", environment, "->", total
# A fully-qualified Java reference written inline is flagged just the same.
print "Follow-up due", java.text.SimpleDateFormat("yyyy-MM-dd").format(nextWeek)
