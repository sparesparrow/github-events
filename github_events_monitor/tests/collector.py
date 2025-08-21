# Compatibility shim so `from ..collector` (from unit tests in `github_events_monitor/tests/unit`) works
# Re-export from the package root
from ..collector import *  # noqa: F401,F403
