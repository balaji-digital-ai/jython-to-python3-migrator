{
  "tool": "jython2py3",
  "version": "0.1.0",
  "files": [
    {
      "source": "C:\\work\\repos\\balaji\\jython-to-python3-migrator\\examples\\jython\\new\\01_release_variable_management.py",
      "output": "examples\\python3\\new\\01_release_variable_management.py",
      "changed": true,
      "transform_count": 9,
      "todo_count": 0,
      "todos": [],
      "error_count": 0,
      "errors": [],
      "tasks_converted": null,
      "failure": null
    },
    {
      "source": "C:\\work\\repos\\balaji\\jython-to-python3-migrator\\examples\\jython\\new\\02_release_task_management.py",
      "output": "examples\\python3\\new\\02_release_task_management.py",
      "changed": true,
      "transform_count": 3,
      "todo_count": 0,
      "todos": [],
      "error_count": 0,
      "errors": [],
      "tasks_converted": null,
      "failure": null
    },
    {
      "source": "C:\\work\\repos\\balaji\\jython-to-python3-migrator\\examples\\jython\\new\\03_external_rest_api.py",
      "output": "examples\\python3\\new\\03_external_rest_api.py",
      "changed": true,
      "transform_count": 2,
      "todo_count": 2,
      "todos": [
        "# TODO[jython2py3] removed Jython import `from xlrelease.HttpRequest import HttpRequest`; use the `requests` library instead (guide section 9)",
        "# TODO[jython2py3] rewrite this HttpRequest call using the `requests` library (guide section 9)"
      ],
      "error_count": 0,
      "errors": [],
      "tasks_converted": null,
      "failure": null
    },
    {
      "source": "C:\\work\\repos\\balaji\\jython-to-python3-migrator\\examples\\jython\\new\\04_release_summary_report.py",
      "output": "examples\\python3\\new\\04_release_summary_report.py",
      "changed": true,
      "transform_count": 7,
      "todo_count": 0,
      "todos": [],
      "error_count": 0,
      "errors": [],
      "tasks_converted": null,
      "failure": null
    },
    {
      "source": "C:\\work\\repos\\balaji\\jython-to-python3-migrator\\examples\\jython\\new\\05_java_interop_examples.py",
      "output": "examples\\python3\\new\\05_java_interop_examples.py",
      "changed": true,
      "transform_count": 0,
      "todo_count": 9,
      "todos": [
        "# TODO[jython2py3] removed Java import `from java.util import Date`; replace its usages with a Python 3 equivalent (guide section 11)",
        "# TODO[jython2py3] removed Java import `from java.text import SimpleDateFormat`; replace its usages with a Python 3 equivalent (guide section 11)",
        "# TODO[jython2py3] removed Java import `from java.util import Properties`; replace its usages with a Python 3 equivalent (guide section 11)",
        "# TODO[jython2py3] removed Java import `from java.util import Arrays`; replace its usages with a Python 3 equivalent (guide section 11)",
        "# TODO[jython2py3] removed Java import `from java.util import UUID`; replace its usages with a Python 3 equivalent (guide section 11)",
        "# TODO[jython2py3] removed Java import `from java.security import MessageDigest`; replace its usages with a Python 3 equivalent (guide section 11)",
        "# TODO[jython2py3] removed Java import `from java.util.regex import Pattern`; replace its usages with a Python 3 equivalent (guide section 11)",
        "# TODO[jython2py3] removed Java import `from java.math import BigDecimal`; replace its usages with a Python 3 equivalent (guide section 11)",
        "# TODO[jython2py3] removed Java import `from java.lang import System`; replace its usages with a Python 3 equivalent (guide section 11)"
      ],
      "error_count": 9,
      "errors": [
        "# ERROR[jython2py3] don't use Java in Python 3: `SimpleDateFormat` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)",
        "# ERROR[jython2py3] don't use Java in Python 3: `Date` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)",
        "# ERROR[jython2py3] don't use Java in Python 3: `Properties` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)",
        "# ERROR[jython2py3] don't use Java in Python 3: `Arrays` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)",
        "# ERROR[jython2py3] don't use Java in Python 3: `UUID` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)",
        "# ERROR[jython2py3] don't use Java in Python 3: `MessageDigest` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)",
        "# ERROR[jython2py3] don't use Java in Python 3: `Pattern` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)",
        "# ERROR[jython2py3] don't use Java in Python 3: `BigDecimal` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)",
        "# ERROR[jython2py3] don't use Java in Python 3: `System` is a JVM class that the container cannot load - replace it with a Python 3 equivalent (guide section 11)"
      ],
      "tasks_converted": null,
      "failure": null
    },
    {
      "source": "C:\\work\\repos\\balaji\\jython-to-python3-migrator\\examples\\jython\\new\\06_validation_and_exception.py",
      "output": "examples\\python3\\new\\06_validation_and_exception.py",
      "changed": true,
      "transform_count": 4,
      "todo_count": 0,
      "todos": [],
      "error_count": 0,
      "errors": [],
      "tasks_converted": null,
      "failure": null
    }
  ]
}