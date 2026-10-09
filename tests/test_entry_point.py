"""The documented entry point: running the driver directly.

The README tells people to run ``python3 sdr.py`` (or the installed copy under
``bin/user``). Because the driver is a package, that only works if ``sdr.py``
puts the package context in place itself.
"""

import os
import subprocess
import sys
from pathlib import Path

SDR_SCRIPT = Path(__file__).resolve().parent.parent / 'bin' / 'user' / 'sdr.py'

# Deliberately without PYTHONPATH, so the script has to find its own package.
ENV = {key: value for key, value in os.environ.items() if key != 'PYTHONPATH'}


def run_script(*args):
    return subprocess.run(
        [sys.executable, str(SDR_SCRIPT), *args], capture_output=True, text=True, env=ENV
    )


def test_the_driver_runs_as_a_script():
    result = run_script('--version')

    assert 'sdr driver version' in result.stdout
    assert 'Traceback' not in result.stderr


def test_the_script_can_list_the_supported_packets():
    # exercises the package imports, since the brand classes live in user.brands
    result = run_script('--action', 'list-supported')

    assert 'known packet types' in result.stdout
    assert 'Traceback' not in result.stderr
