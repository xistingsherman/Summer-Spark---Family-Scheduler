"""Entry point invoked by the summer-schedule-designer skill.

Kept as a thin wrapper so the agent-facing invocation
(``python generate_schedule.py --location ... --profiles-file ...``)
stays stable while the implementation lives in cli.py/geocode.py/
weather.py/schedule.py/ui.py.
"""

import sys

from cli import main

if __name__ == "__main__":
    sys.exit(main())
