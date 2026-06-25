# Java interoperability examples

from java.util import Date
from java.text import SimpleDateFormat
from java.util import Properties
from java.util import Arrays
from java.util import UUID
from java.security import MessageDigest
from java.util.regex import Pattern
from java.math import BigDecimal
from java.lang import System

# Date
formatter = SimpleDateFormat("yyyy-MM-dd HH:mm:ss")
releaseVariables["executionTime"] = formatter.format(Date())

# Properties
props = Properties()
props.setProperty("environment", "QA")
releaseVariables["environment"] = props.getProperty("environment")

# Arrays
servers = Arrays.asList("DEV", "QA", "UAT", "PROD")
releaseVariables["serverCount"] = len(servers)

# UUID
releaseVariables["requestId"] = UUID.randomUUID().toString()

# MD5
md = MessageDigest.getInstance("MD5")
md.update("DigitalAI".getBytes())
digest = md.digest()

# Regex
matcher = Pattern.compile("\\d+").matcher("Build123")
if matcher.find():
    print matcher.group()

# BigDecimal
total = BigDecimal("12.50").add(BigDecimal("7.25"))
print total

# Environment
print System.getenv("JAVA_HOME")
