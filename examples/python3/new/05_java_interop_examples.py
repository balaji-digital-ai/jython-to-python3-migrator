# Migrated from Jython by jython2py3 v0.1.0.
# Search "# TODO[jython2py3]" / "# ERROR[jython2py3]" for items needing review;
# safe (Tier-1) transforms were applied silently.

# Java interoperability examples

# TODO[jython2py3] removed Java import `from java.util import Date`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.text import SimpleDateFormat`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.util import Properties`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.util import Arrays`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.util import UUID`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.security import MessageDigest`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.util.regex import Pattern`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.math import BigDecimal`; replace its usages with a Python 3 equivalent (guide section 11)
# TODO[jython2py3] removed Java import `from java.lang import System`; replace its usages with a Python 3 equivalent (guide section 11)

# Date
# ERROR[jython2py3] don't use Java in Python 3: `SimpleDateFormat` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
formatter = SimpleDateFormat("yyyy-MM-dd HH:mm:ss")
# ERROR[jython2py3] don't use Java in Python 3: `Date` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
setReleaseVariable("executionTime", formatter.format(Date()))

# Properties
# ERROR[jython2py3] don't use Java in Python 3: `Properties` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
props = Properties()
props.setProperty("environment", "QA")
setReleaseVariable("environment", props.getProperty("environment"))

# Arrays
# ERROR[jython2py3] don't use Java in Python 3: `Arrays` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
servers = Arrays.asList("DEV", "QA", "UAT", "PROD")
setReleaseVariable("serverCount", len(servers))

# UUID
# ERROR[jython2py3] don't use Java in Python 3: `UUID` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
setReleaseVariable("requestId", UUID.randomUUID().toString())

# MD5
# ERROR[jython2py3] don't use Java in Python 3: `MessageDigest` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
md = MessageDigest.getInstance("MD5")
md.update("DigitalAI".getBytes())
digest = md.digest()

# Regex
# ERROR[jython2py3] don't use Java in Python 3: `Pattern` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
matcher = Pattern.compile("\\d+").matcher("Build123")
if matcher.find():
    print(matcher.group())

# BigDecimal
# ERROR[jython2py3] don't use Java in Python 3: `BigDecimal` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
total = BigDecimal("12.50").add(BigDecimal("7.25"))
print(total)

# Environment
# ERROR[jython2py3] don't use Java in Python 3: `System` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
print(System.getenv("JAVA_HOME"))
