"""How the driver drives the rtl_433 executable.

Two levels:

* With ``pytest-subprocess`` (the ``fp`` fixture) we check what the driver
  *asks for* - the command line and the environment - without running anything.
* With a real fake executable we check what it does *with* the process: reading
  its output, noticing when it dies, and killing it on shutdown.
"""

import itertools
import time

import pytest

# Real rtl_433 text output.  rtl_433 in text mode emits one timestamped line per
# packet, which is what the process manager groups on.
TOWER_TEXT = (
    '2016-08-30 23:57:20 Acurite tower sensor 0x37FC Ch A: 26.7 C 80.1 F 16 % RH',
    '2016-08-30 23:57:21 Acurite tower sensor 0x37FC Ch A: 27.0 C 80.6 F 15 % RH',
)

TOWER_SENSOR_MAP = {
    'outTemp': 'temperature.*.AcuriteTowerPacket',
    'outHumidity': 'humidity.*.AcuriteTowerPacket',
}


def wait_until(predicate, timeout=5.0):
    """Poll until the predicate holds (or give up)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def collect_until(getter, timeout=5.0):
    """Repeatedly drain ``getter()`` until it yields something."""
    collected = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        collected.extend(getter())
        if collected:
            break
        time.sleep(0.02)
    return collected


# --- what we ask rtl_433 to do (no process involved) ------------------------


def test_the_driver_runs_the_configured_command(fp, open_driver):
    fp.register(['rtl_433', '-M', 'utc', '-F', 'json'])

    with open_driver(cmd='rtl_433 -M utc -F json'):
        assert list(fp.calls) == [['rtl_433', '-M', 'utc', '-F', 'json']]


def test_the_driver_starts_rtl_433_exactly_once(fp, open_driver):
    fp.register(['rtl_433', '-M', 'utc', '-F', 'json'])

    with open_driver(cmd='rtl_433 -M utc -F json'):
        assert len(fp.calls) == 1


def test_the_driver_passes_path_and_ld_library_path(fp, open_driver, monkeypatch):
    monkeypatch.setenv('PATH', '/usr/bin')
    recorder = fp.register(['rtl_433', '-M', 'utc', '-F', 'json'])

    with open_driver(
        cmd='rtl_433 -M utc -F json',
        path='/opt/rtl-433/bin',
        ld_library_path='/opt/rtl-sdr/lib',
    ):
        env = recorder.calls[0].kwargs['env']

    assert env['PATH'] == '/opt/rtl-433/bin:/usr/bin'
    assert env['LD_LIBRARY_PATH'] == '/opt/rtl-sdr/lib'


# --- what we do with the process --------------------------------------------


def test_it_notices_when_the_process_is_gone(make_fake_rtl433, manager):
    cmd = make_fake_rtl433()  # exits immediately
    manager.startup(cmd)

    assert wait_until(lambda: not manager.running())


def test_stderr_from_rtl_433_is_surfaced(make_fake_rtl433, manager):
    cmd = make_fake_rtl433(stderr=['rtl_433: no tuner'], stay_alive=True)
    manager.startup(cmd)

    lines = collect_until(manager.get_stderr)

    assert any('no tuner' in line for line in lines)


def test_a_packet_is_read_end_to_end_from_rtl_433(make_fake_rtl433, open_driver):
    cmd = make_fake_rtl433(stdout=TOWER_TEXT, stay_alive=True)

    with open_driver(cmd=cmd, sensor_map=TOWER_SENSOR_MAP) as driver:
        packets = list(itertools.islice(driver.genLoopPackets(), 1))

    assert packets[0]['outTemp'] == pytest.approx(26.7)
    assert packets[0]['outHumidity'] == pytest.approx(16.0)


# --- what we do to it on the way out ----------------------------------------


def test_closePort_terminates_rtl_433(make_fake_rtl433, load_driver):
    # closePort is the subject here, so this test manages the driver itself
    cmd = make_fake_rtl433(stay_alive=True)
    driver = load_driver(cmd=cmd, sensor_map=TOWER_SENSOR_MAP)

    process = driver._mgr._process
    assert process.poll() is None  # running

    driver.closePort()

    assert process.poll() is not None  # killed


def test_closePort_can_be_called_twice(make_fake_rtl433, load_driver):
    # closePort is the subject here too, so this test manages the driver itself
    cmd = make_fake_rtl433(stay_alive=True)
    driver = load_driver(cmd=cmd, sensor_map=TOWER_SENSOR_MAP)
    process = driver._mgr._process

    driver.closePort()
    driver.closePort()  # a second close is a no-op, not an AttributeError

    assert process.poll() is not None  # still killed


def test_a_manager_that_never_started_shuts_down_safely(manager):
    # shutdown() and running() must not assume that startup() succeeded
    assert manager.running() is False

    manager.shutdown()

    assert manager.running() is False
