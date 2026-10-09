"""Fixtures for the integration tests.

The integration tests treat the driver the way WeeWX does: they load it through
the public ``loader()`` entry point and drive it through ``genLoopPackets()``.

Two ways of standing in for rtl_433 are provided:

* ``make_fake_rtl433`` - the command line that runs a real executable
  (``tests/fake_rtl433.py``), for tests that need real pipes, real reader
  threads and a real process to kill.
* ``stub_rtl433`` - a mocked process manager for tests about how the driver
  behaves, with no process at all.
"""

import contextlib
import json
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

import user.core as core
import user.sdr as sdr

FAKE_RTL433 = Path(__file__).parent / 'fake_rtl433.py'


# ---------------------------------------------------------------------------
# a real stand-in for the rtl_433 executable
# ---------------------------------------------------------------------------


@pytest.fixture
def make_fake_rtl433(monkeypatch):
    """Return the command line of a fake rtl_433 that emits the output asked for."""

    def make(stdout=(), stderr=(), stay_alive=False):
        monkeypatch.setenv(
            'FAKE_RTL433_SPEC',
            json.dumps(
                {
                    'stdout': list(stdout),
                    'stderr': list(stderr),
                    'stay_alive': stay_alive,
                }
            ),
        )
        return '%s %s' % (sys.executable, FAKE_RTL433)

    return make


# ---------------------------------------------------------------------------
# a mocked process manager
# ---------------------------------------------------------------------------


def _canned_blocks(state):
    """Yield the queued output blocks, one per read, then stop."""
    while state['blocks']:
        yield state['blocks'].pop(0)


@pytest.fixture
def stub_rtl433(monkeypatch):
    """Replace ProcManager with a mock; set ``state['blocks']`` before use."""
    state = {'blocks': [], 'started': None, 'shutdown': False}

    def build():
        manager = Mock()
        manager.startup.side_effect = lambda cmd, path=None, ld_library_path=None: state.update(
            started={'cmd': cmd, 'path': path, 'ld_library_path': ld_library_path}
        )
        manager.running.side_effect = lambda: bool(state['blocks'])
        manager.get_stdout.side_effect = lambda: _canned_blocks(state)
        manager.get_stderr.return_value = []
        manager.shutdown.side_effect = lambda: state.update(shutdown=True)
        return manager

    # The driver looks ProcManager up in user.core's globals, so the stub must
    # be installed there; patching the user.sdr re-export would do nothing.
    monkeypatch.setattr(core, 'ProcManager', build)
    return state


# ---------------------------------------------------------------------------
# the driver, loaded the way WeeWX loads it
# ---------------------------------------------------------------------------


@pytest.fixture
def load_driver():
    """Load the driver through the module-level ``loader()``, as WeeWX does.

    WeeWX imports the driver by the name in weewx.conf, ``user.sdr``, so that is
    the module the tests go through.  The driver is not closed for you; prefer
    ``open_driver`` unless the test is itself about shutting the driver down.
    """

    def load(**stanza):
        return sdr.loader({'SDR': stanza}, None)

    return load


@pytest.fixture
def open_driver(load_driver):
    """Open a driver for a ``with`` block and close it on the way out.

    This is a context manager rather than a plain yield fixture because the
    stanza differs from test to test - and is sometimes built at runtime, from
    the fake rtl_433 command line - so it is not known when the fixture runs.
    """

    @contextlib.contextmanager
    def open_driver(**stanza):
        driver = load_driver(**stanza)
        try:
            yield driver
        finally:
            driver.closePort()

    return open_driver


@pytest.fixture
def manager():
    """A process manager, shut down when the test finishes."""
    manager = core.ProcManager()
    yield manager
    manager.shutdown()
