# A health-check task that calls an external API. In Jython this used the bundled
# `HttpRequest` helper, plus `java.net` for a fallback ping. The migrator flags the
# HttpRequest call with a TODO (rewrite with `requests`) and the Java `URL` use with
# an ERROR (no JVM in the container) - a realistic mix of both annotation kinds.
# TODO[jython2py3] removed Jython import `from xlrelease.HttpRequest import HttpRequest`; use the `requests` library instead (guide section 9)
# TODO[jython2py3] removed Java import `from java.net import URL`; replace its usages with a Python 3 equivalent (guide section 11)

endpoint = getReleaseVariable("healthEndpoint")

# Tier 2 TODO: the original pulls its URL/credentials from a shared HTTP Server
# configuration, so the rewrite needs a human decision.
# TODO[jython2py3] rewrite this HttpRequest call using the `requests` library (guide section 9)
response = HttpRequest({"url": endpoint}).get("/health")
if not response.isSuccessful():
    raise Exception("Health check failed: %d" % response.getStatus())

# Tier 2 ERROR: opening the URL through Java cannot run in the container.
# ERROR[jython2py3] don't use Java in Python 3: `URL` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)
connection = URL(endpoint).openConnection()
print("Ping status", connection.getResponseCode())

print("Health check OK for", endpoint)
