# A reporting script that leans on the Java standard library for date handling.
# None of it runs in the Python 3 container, so the migrator drops the imports
# (leaving breadcrumbs) and stamps every Java use with an ERROR - rewrite the whole
# block with Python's `datetime` module.
from java.util import Date, Calendar
from java.text import SimpleDateFormat

# `Date` and `SimpleDateFormat` are Java classes: each use is flagged.
now = Date()
formatter = SimpleDateFormat("yyyy-MM-dd HH:mm")
stamp = formatter.format(now)

# `Calendar` too - both the factory call and the constant reference are Java.
calendar = Calendar.getInstance()
calendar.add(Calendar.DAY_OF_MONTH, 7)
nextWeek = calendar.getTime()

print "Report generated at", stamp
# A fully-qualified Java reference written inline is flagged just the same.
print "Follow-up due", java.text.SimpleDateFormat("yyyy-MM-dd").format(nextWeek)
