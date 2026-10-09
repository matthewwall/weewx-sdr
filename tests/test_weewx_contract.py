"""The driver as WeeWX sees it.

WeeWX loads a driver by the name configured in weewx.conf - ``user.sdr`` - via the
module-level ``loader()``, then drives it through the ``weewx.drivers.AbstractDevice``
interface.  These tests play the role of WeeWX: they check the packets the driver
hands over, the way it signals that the device has gone away, and the configuration
stanza it ships.
"""

import json

import configobj
import pytest
import weewx
import weewx.drivers

import user.sdr as sdr
from user.brands import Acurite5n1Packet

# A real rtl_433 json line (the shape the driver's own captured examples use).
TOWER = {
    'time': '2018-07-21 01:53:56',
    'model': 'Acurite tower sensor',
    'id': 13009,
    'sensor_id': 13009,
    'channel': 'A',
    'temperature_C': 15.000,
    'humidity': 16,
    'battery_low': 1,
}

TOWER_SENSOR_MAP = {
    'outTemp': 'temperature.*.AcuriteTowerPacket',
    'outHumidity': 'humidity.*.AcuriteTowerPacket',
}


def drain(driver):
    """Run genLoopPackets() until the (fake) rtl_433 process stops.

    WeeWX expects a driver to end a run by raising WeeWxIOError, which the
    engine treats as 'the device went away, reconnect and try again'.
    """
    packets = []
    with pytest.raises(weewx.WeeWxIOError):
        for pkt in driver.genLoopPackets():
            packets.append(pkt)
    return packets


# --- the device interface ---------------------------------------------------


def test_loader_returns_a_weewx_device(stub_rtl433, load_driver):
    driver = load_driver()
    assert isinstance(driver, weewx.drivers.AbstractDevice)
    assert driver.hardware_name == 'SDR'


def test_the_configured_model_is_reported_as_the_hardware_name(stub_rtl433, load_driver):
    assert load_driver(model='my station').hardware_name == 'my station'


def test_closePort_stops_the_device(stub_rtl433, load_driver):
    driver = load_driver()
    driver.closePort()
    assert stub_rtl433['shutdown'] is True


def test_a_dead_device_is_reported_as_weewx_io_error(stub_rtl433, load_driver):
    driver = load_driver(sensor_map=TOWER_SENSOR_MAP)
    with pytest.raises(weewx.WeeWxIOError):
        next(driver.genLoopPackets())


def test_an_unusable_command_is_reported_as_weewx_io_error(load_driver):
    with pytest.raises(weewx.WeeWxIOError):
        load_driver(cmd='/nonexistent/rtl_433 -M utc -F json')


# --- the packets handed to WeeWX --------------------------------------------


def test_genLoopPackets_yields_weewx_loop_packets(stub_rtl433, load_driver):
    stub_rtl433['blocks'] = [[json.dumps(TOWER)]]
    packets = drain(load_driver(sensor_map=TOWER_SENSOR_MAP))

    assert len(packets) == 1
    pkt = packets[0]
    # only the mapped observations, plus the two fields WeeWX requires
    assert set(pkt) == {'outTemp', 'outHumidity', 'dateTime', 'usUnits'}
    assert pkt['outTemp'] == pytest.approx(59.0)
    assert pkt['outHumidity'] == pytest.approx(16.0)
    assert isinstance(pkt['dateTime'], int)
    assert pkt['usUnits'] == weewx.US


def test_no_sensor_map_means_no_data_is_collected(stub_rtl433, load_driver):
    stub_rtl433['blocks'] = [[json.dumps(TOWER)]]
    assert drain(load_driver()) == []


def test_duplicate_readings_are_ignored(stub_rtl433, load_driver):
    line = json.dumps(TOWER)
    stub_rtl433['blocks'] = [[line], [line]]
    assert len(drain(load_driver(sensor_map=TOWER_SENSOR_MAP))) == 1


def test_a_cumulative_total_is_reported_as_a_per_period_delta(stub_rtl433, load_driver):
    # Acurite 5n1 reports rain as a cumulative counter; WeeWX wants the amount
    # since the last reading.
    base = dict(Acurite5n1Packet.EXAMPLES[0])
    stub_rtl433['blocks'] = [
        [json.dumps(base)],
        [
            json.dumps(
                {
                    **base,
                    'time': '2017-01-16 02:35:12',
                    'raincounter_raw': base['raincounter_raw'] + 22,  # +0.22 inch
                }
            )
        ],
    ]
    packets = drain(load_driver(sensor_map={'rain_total': 'rain_total.*.Acurite5n1Packet'}))

    assert len(packets) == 2
    assert packets[0]['rain'] is None  # nothing to compare against yet
    assert packets[1]['rain'] == pytest.approx(0.22)


# --- the configuration stanza ----------------------------------------------


def test_confeditor_ships_a_usable_sdr_stanza():
    editor = sdr.confeditor_loader()
    assert isinstance(editor, weewx.drivers.AbstractConfEditor)

    parsed = configobj.ConfigObj(editor.default_stanza.splitlines())
    assert parsed['SDR']['driver'] == 'user.sdr'
