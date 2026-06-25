# Example 07 - HttpRequest health check (guide section 9)
#
# A health-check task using the bundled HttpRequest helper. The migrator flags the
# HttpRequest call with a TODO (rewrite with requests). The json module migrates
# unchanged.
import json

# Seed the variable this example reads so it runs standalone.
releaseVariables["healthEndpoint"] = "https://www.githubstatus.com"

endpoint = releaseVariables["healthEndpoint"]

# Tier 2 TODO: URL/credentials come from a shared HTTP Server config - needs a human.
response = HttpRequest({"url": endpoint}).get("/api/v2/status.json")
if not response.isSuccessful():
    raise Exception("Health check failed: %d" % response.getStatus())

# json is portable, so parsing the body and storing a field is Tier 1.
payload = json.loads(response.getResponse())
releaseVariables["healthStatus"] = payload["status"]

print "Health check OK for", endpoint
