# A health-check task that calls an external API. In Jython this used the bundled
# `HttpRequest` helper, plus `java.net` for a fallback ping. The migrator flags the
# HttpRequest call with a TODO (rewrite with `requests`) and the Java `URL` use with
# an ERROR (no JVM in the container) - a realistic mix of both annotation kinds.
from xlrelease.HttpRequest import HttpRequest
from java.net import URL

endpoint = releaseVariables["healthEndpoint"]

# Tier 2 TODO: the original pulls its URL/credentials from a shared HTTP Server
# configuration, so the rewrite needs a human decision.
response = HttpRequest({"url": endpoint}).get("/health")
if not response.isSuccessful():
    raise Exception("Health check failed: %d" % response.getStatus())

# Tier 2 ERROR: opening the URL through Java cannot run in the container.
connection = URL(endpoint).openConnection()
print "Ping status", connection.getResponseCode()

print "Health check OK for", endpoint
