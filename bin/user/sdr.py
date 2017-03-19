#!/usr/bin/env python
# Copyright 2016-2017 Matthew Wall
# Distributed under the terms of the GNU Public License (GPLv3)
"""
Collect data from stl-sdr.  Run rtl_433 on a thread and push the output onto
a queue.

The SDR detects many different sensors and sensor types, so this driver
includes a mechanism to filter the incoming data, and to map the filtered
data onto the weewx database schema and identify the type of data from each
sensor.

Sensors are filtered based on a tuple that identifies uniquely each sensor.
A tuple consists of the observation name, a unique identifier for the hardware,
and the packet type, separated by periods:

  <observation_name>.<hardware_id>.<packet_type>

The filter and data types are specified in a sensor_map stanza in the driver
stanza.  For example:

[SDR]
    driver = user.sdr
    [[sensor_map]]
        inTemp = temperature.25A6.AcuriteTowerPacket
        outTemp = temperature.24A4.AcuriteTowerPacket
        rain_total = rain_total.A52B.Acurite5n1Packet

If no sensor_map is specified, no data will be collected.

The deltas stanza indicates which observations are cumulative measures and
how they should be split into delta measures.

[SDR]
    ...
    [[deltas]]
        rain = rain_total

In this case, the value for rain will be a delta calculated from sequential
rain_total observations.

To identify sensors, run the driver directly.  Alternatively, use the options
log_unknown_sensors and log_unmapped_sensors to see data from the SDR that are
not yet recognized by your configuration.

[SDR]
    driver = user.sdr
    log_unknown_sensors = True
    log_unmapped_sensors = True

The default for each of these is False.

Eventually we would prefer to have all rtl_433 output as json.  Unfortunately,
many of the rtl_433 decoders do not emit this format yet (as of January 2017).
So this driver is designed to look for json first, then fall back to single-
or multi-line plain text format.

WARNING: Handling of units and unit systems in rtl_433 is a mess.  Although
there is an option to request SI units, there is no indicate in the decoder
output whether that option is respected, nor does rtl_433 specify exactly
which SI units are used for various types of measure.
"""

from __future__ import with_statement
from calendar import timegm
import Queue
import fnmatch
import os
import re
import subprocess
import syslog
import threading
import time

try:
    import cjson as json
    setattr(json, 'dumps', json.encode)
    setattr(json, 'loads', json.decode)
except (ImportError, AttributeError):
    try:
        import simplejson as json
    except ImportError:
        import json

import weewx.drivers
from weeutil.weeutil import tobool


DRIVER_NAME = 'SDR'
DRIVER_VERSION = '0.24'

# The default command requests json output from every decoder
# -q - suppress non-data messages
# -U - print timestamps in UTC
# -F json - emit data in json format (not all rtl_433 decoders support this)
# -G - emit data for all rtl decoder (only available in newer rtl_433)
# Use the -R option instead of -G to indicate specific decoders.
DEFAULT_CMD = 'rtl_433 -q -U -F json -G'


def loader(config_dict, _):
    return SDRDriver(**config_dict[DRIVER_NAME])

def confeditor_loader():
    return SDRConfigurationEditor()


def logmsg(level, msg):
    syslog.syslog(level, 'sdr: %s: %s' %
                  (threading.currentThread().getName(), msg))

def logdbg(msg):
    logmsg(syslog.LOG_DEBUG, msg)

def loginf(msg):
    logmsg(syslog.LOG_INFO, msg)

def logerr(msg):
    logmsg(syslog.LOG_ERR, msg)


class AsyncReader(threading.Thread):

    def __init__(self, fd, queue, label):
        threading.Thread.__init__(self)
        self._fd = fd
        self._queue = queue
        self._running = False
        self.setDaemon(True)
        self.setName(label)

    def run(self):
        logdbg("start async reader for %s" % self.getName())
        self._running = True
        for line in iter(self._fd.readline, ''):
            self._queue.put(line)
            if not self._running:
                break

    def stop_running(self):
        self._running = False


class ProcManager():
    TS = re.compile('^\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d[\s]+')

    def __init__(self):
        self._cmd = None
        self._process = None
        self.stdout_queue = Queue.Queue()
        self.stdout_reader = None
        self.stderr_queue = Queue.Queue()
        self.stderr_reader = None

    def startup(self, cmd, path=None, ld_library_path=None):
        self._cmd = cmd
        loginf("startup process '%s'" % self._cmd)
        env = os.environ.copy()
        if path:
            env['PATH'] = path + ':' + env['PATH']
        if ld_library_path:
            env['LD_LIBRARY_PATH'] = ld_library_path
        try:
            self._process = subprocess.Popen(cmd.split(' '),
                                             env=env,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
            self.stdout_reader = AsyncReader(
                self._process.stdout, self.stdout_queue, 'stdout-thread')
            self.stdout_reader.start()
            self.stderr_reader = AsyncReader(
                self._process.stderr, self.stderr_queue, 'stderr-thread')
            self.stderr_reader.start()
        except (OSError, ValueError), e:
            raise weewx.WeeWxIOError("failed to start process: %s" % e)

    def shutdown(self):
        loginf('shutdown process %s' % self._cmd)
        logdbg('waiting for %s' % self.stdout_reader.getName())
        self.stdout_reader.stop_running()
        self.stdout_reader.join(10.0)
        if self.stdout_reader.isAlive():
            loginf('timed out waiting for %s' % self.stdout_reader.getName())
        self.stdout_reader = None
        logdbg('waiting for %s' % self.stderr_reader.getName())
        self.stderr_reader.stop_running()
        self.stderr_reader.join(10.0)
        if self.stderr_reader.isAlive():
            loginf('timed out waiting for %s' % self.stderr_reader.getName())
        self.stderr_reader = None
        logdbg("close stdout")
        self._process.stdout.close()
        logdbg("close stderr")
        self._process.stderr.close()
        logdbg('kill process')
        self._process.kill()
        if self._process.poll() is None:
            logerr('process did not respond to kill, shutting down anyway')
        self._process = None

    def running(self):
        return self._process.poll() is None

    def get_stderr(self):
        lines = []
        while not self.stderr_queue.empty():
            lines.append(self.stderr_queue.get())
        return lines

    def get_stdout(self):
        lines = []
        while self.running():
            try:
                line = self.stdout_queue.get(True, 3)
                m = ProcManager.TS.search(line)
                if m and lines:
                    yield lines
                    lines = []
                lines.append(line)
            except Queue.Empty:
                yield lines
                lines = []
        yield lines


class Packet:

    def __init__(self):
        pass

    @staticmethod
    def parse_text(ts, payload, lines):
        return None

    @staticmethod
    def parse_json(obj):
        return None

    TS_PATTERN = re.compile('(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d)')

    @staticmethod
    def parse_time(line):
        ts = None
        try:
            m = Packet.TS_PATTERN.search(line)
            if m:
                utc = time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                ts = timegm(utc)
        except Exception, e:
            logerr("parse timestamp failed for '%s': %s" % (line, e))
        return ts

    @staticmethod
    def get_float(obj, key_):
        if key_ in obj:
            try:
                return float(obj[key_])
            except ValueError:
                pass
        return None

    @staticmethod
    def get_int(obj, key_):
        if key_ in obj:
            try:
                return int(obj[key_])
            except ValueError:
                pass
        return None

    @staticmethod
    def parse_lines(lines, parseinfo=None):
        # parse each line, splitting on colon for name:value
        # tuple in parseinfo is label, pattern, lambda
        # if there is a label, use it to transform the name
        # if there is a pattern, use it to match the value
        # if there is a lamba, use it to convert the value
        if parseinfo is None:
            parseinfo = dict()
        packet = dict()
        for line in lines[1:]:
            if line.count(':') == 1:
                try:
                    (name, value) = [x.strip() for x in line.split(':')]
                    if name in parseinfo:
                        if parseinfo[name][1]:
                            m = parseinfo[name][1].search(value)
                            if m:
                                value = m.group(1)
                            else:
                                logdbg("regex failed for %s:'%s'" %
                                       (name, value))
                        if parseinfo[name][2]:
                            value = parseinfo[name][2](value)
                        if parseinfo[name][0]:
                            name = parseinfo[name][0]
                        packet[name] = value
                    else:
                        logdbg("ignoring %s:%s" % (name, value))
                except Exception, e:
                    logerr("parse failed for line '%s': %s" % (line, e))
            else:
                logdbg("skip line '%s'" % line)
        while lines:
            lines.pop(0)
        return packet

    @staticmethod
    def add_identifiers(pkt, sensor_id='', packet_type=''):
        # qualify each field name with details about the sensor.  not every
        # sensor has all three fields.
        # observation.<sensor_id>.<packet_type>
        packet = dict()
        if 'dateTime' in pkt:
            packet['dateTime'] = pkt.pop('dateTime', 0)
        if 'usUnits' in pkt:
            packet['usUnits'] = pkt.pop('usUnits', 0)
        for n in pkt:
            packet["%s.%s.%s" % (n, sensor_id, packet_type)] = pkt[n]
        return packet


class Acurite(object):
    @staticmethod
    def insert_ids(pkt, pkt_type):
        # there should be a sensor_id field in the packet to identify sensor.
        # ensure the sensor_id is upper-case - it should be 4 hex characters.
        sensor_id = pkt.pop('hardware_id', '0000').upper()
        return Packet.add_identifiers(pkt, sensor_id, pkt_type)


class AcuriteTowerPacket(Packet):
    # initial implementation was single-line
    # 2016-08-30 23:57:20 Acurite tower sensor 0x37FC Ch A: 26.7 C 80.1 F 16 % RH
    #
    # multi-line was introduced nov2016 - only single line is supported here
    # 2017-01-12 02:55:10 : Acurite tower sensor : 12391 : B
    # Temperature: 18.0 C
    # Humidity: 68
    # Battery: 0
    # : 68

    IDENTIFIER = "Acurite tower sensor"
    PATTERN = re.compile('0x([0-9a-fA-F]+) Ch ([A-C]): ([\d.-]+) C ([\d.-]+) F ([\d]+) % RH')

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        m = AcuriteTowerPacket.PATTERN.search(lines[0])
        if m:
            pkt['dateTime'] = ts
            pkt['usUnits'] = weewx.METRIC
            pkt['hardware_id'] = m.group(1)
            pkt['channel'] = m.group(2)
            pkt['temperature'] = float(m.group(3))
            pkt['temperature_F'] = float(m.group(4))
            pkt['humidity'] = float(m.group(5))
            pkt = Acurite.insert_ids(pkt, AcuriteTowerPacket.__name__)
        else:
            loginf("AcuriteTowerPacket: unrecognized data: '%s'" % lines[0])
        lines.pop(0)
        return pkt

    # {"time" : "2017-01-12 03:43:05", "model" : "Acurite tower sensor", "id" : 521, "channel" : "A", "temperature_C" : 0.800, "humidity" : 68, "battery" : 0, "status" : 68}
    # {"time" : "2017-01-12 03:43:11", "model" : "Acurite tower sensor", "id" : 5585, "channel" : "C", "temperature_C" : 21.100, "humidity" : 32, "battery" : 0, "status" : 68}

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['hardware_id'] = "%04x" % obj.get('id', 0)
        pkt['channel'] = obj.get('channel')
        pkt['battery'] = 0 if obj.get('battery') == 0 else 1
        pkt['status'] = obj.get('status')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        return Acurite.insert_ids(pkt, AcuriteTowerPacket.__name__)


class Acurite5n1Packet(Packet):
    # 2016-08-31 16:41:39 Acurite 5n1 sensor 0x0BFA Ch C, Msg 31, Wind 15 kmph / 9.3 mph 270.0^ W (3), rain gauge 0.00 in
    # 2016-08-30 23:57:25 Acurite 5n1 sensor 0x0BFA Ch C, Msg 38, Wind 2 kmph / 1.2 mph, 21.3 C 70.3 F 70 % RH
    # 2016-09-27 17:09:34 Acurite 5n1 sensor 0x062C Ch A, Total rain fall since last reset: 2.00
    #
    # the 'rain fall since last reset' seems to be emitted once when rtl_433
    # starts up, then never again.  the rain measure in the type 31 messages
    # is a cumulative value, but not the same as rain since last reset.

    IDENTIFIER = "Acurite 5n1 sensor"
    PATTERN = re.compile('0x([0-9a-fA-F]+) Ch ([A-C]), (.*)')
    RAIN = re.compile('Total rain fall since last reset: ([\d.]+)')
    MSG = re.compile('Msg (\d+), (.*)')
    MSG31 = re.compile('Wind ([\d.]+) kmph / ([\d.]+) mph ([\d.]+).*rain gauge ([\d.]+) in')
    MSG38 = re.compile('Wind ([\d.]+) kmph / ([\d.]+) mph, ([\d.-]+) C ([\d.-]+) F ([\d.]+) % RH')

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        m = Acurite5n1Packet.PATTERN.search(lines[0])
        if m:
            pkt['dateTime'] = ts
            pkt['usUnits'] = weewx.METRIC
            pkt['hardware_id'] = m.group(1)
            pkt['channel'] = m.group(2)
            payload = m.group(3)
            m = Acurite5n1Packet.MSG.search(payload)
            if m:
                msg_type = m.group(1)
                payload = m.group(2)
                if msg_type == '31':
                    m = Acurite5n1Packet.MSG31.search(payload)
                    if m:
                        pkt['wind_speed'] = float(m.group(1))
                        pkt['wind_speed_mph'] = float(m.group(2))
                        pkt['wind_dir'] = float(m.group(3))
                        pkt['rain_total'] = float(m.group(4))
                    else:
                        loginf("Acurite5n1Packet: no match for type 31: '%s'"
                               % payload)
                elif msg_type == '38':
                    m = Acurite5n1Packet.MSG38.search(payload)
                    if m:
                        pkt['wind_speed'] = float(m.group(1))
                        pkt['wind_speed_mph'] = float(m.group(2))
                        pkt['temperature'] = float(m.group(3))
                        pkt['temperature_F'] = float(m.group(4))
                        pkt['humidity'] = float(m.group(5))
                    else:
                        loginf("Acurite5n1Packet: no match for type 38: '%s'"
                               % payload)
                else:
                    loginf("Acurite5n1Packet: unknown message type %s"
                           " in line '%s'" % (msg_type, lines[0]))
            else:
                m = Acurite5n1Packet.RAIN.search(payload)
                if m:
                    total = float(m.group(1))
                    pkt['rain_since_reset'] = total
                    loginf("Acurite5n1Packet: rain since reset: %s" % total)
                else:
                    loginf("Acurite5n1Packet: unknown message format: '%s'" %
                           lines[0])
        else:
            loginf("Acurite5n1Packet: unrecognized data: '%s'" % lines[0])
        lines.pop(0)
        return Acurite.insert_ids(pkt, Acurite5n1Packet.__name__)

    # {"time" : "2017-01-16 02:34:12", "model" : "Acurite 5n1 sensor", "sensor_id" : 3066, "channel" : "C", "sequence_num" : 1, "battery" : "OK", "message_type" : 49, "wind_speed" : 0.000, "wind_dir_deg" : 67.500, "wind_dir" : "ENE", "rainfall_accumulation" : 0.000, "raincounter_raw" : 8978}
    # {"time" : "2017-01-16 02:37:33", "model" : "Acurite 5n1 sensor", "sensor_id" : 3066, "channel" : "C", "sequence_num" : 1, "battery" : "OK", "message_type" : 56, "wind_speed" : 0.000, "temperature_F" : 27.500, "humidity" : 56}

    # FIXME: verify that wind speed is mph

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.US
        pkt['hardware_id'] = "%04x" % obj.get('sensor_id', 0)
        pkt['channel'] = obj.get('channel')
        pkt['battery'] = 0 if obj.get('battery') == 'OK' else 1
        pkt['status'] = obj.get('status')
        msg_type = obj.get('message_type')
        if msg_type == 49: # 0x31
            pkt['wind_speed'] = Packet.get_float(obj, 'wind_speed') # mph?
            pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
            pkt['rain_counter'] = Packet.get_int(obj, 'raincounter_raw')
        elif msg_type == 56: # 0x38
            pkt['wind_speed'] = Packet.get_float(obj, 'wind_speed') # mph?
            pkt['temperature'] = Packet.get_float(obj, 'temperature_F')
            pkt['humidity'] = Packet.get_float(obj, 'humidity')
        # put some units on the rain total - each tip is 0.01 inch
        if 'rain_counter' in pkt:
            pkt['rain_total'] = pkt['rain_counter'] * 0.01 # inch
        return Acurite.insert_ids(pkt, Acurite5n1Packet.__name__)


class Acurite986Packet(Packet):
    # 2016-10-31 15:24:29 Acurite 986 sensor 0x2c87 - 2F: 16.7 C 62 F
    # 2016-10-31 15:23:54 Acurite 986 sensor 0x85ed - 1R: 16.7 C 62 F

    # The 986 hardware_id changes, so using the 2F and 1R as the hardware
    # identifer.  As long as you only have one set of sendors and your 
    # close neighbors have none.

    # FIXME: battery monitor

    IDENTIFIER = "Acurite 986 sensor"
    PATTERN = re.compile('0x([0-9a-fA-F]+) - (1R|2F): ([\d.-]+) C ([\d.-]+) F')

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        m = Acurite986Packet.PATTERN.search(lines[0])
        if m:
            pkt['dateTime'] = ts
            pkt['usUnits'] = weewx.METRIC
            pkt['hardware_id'] = m.group(2)
            pkt['channel'] = m.group(1)
            pkt['temperature'] = float(m.group(3))
            pkt['temperature_F'] = float(m.group(4))
        else:
            loginf("Acurite986Packet: unrecognized data: '%s'" % lines[0])
        lines.pop(0)
        return Acurite.insert_ids(pkt, Acurite986Packet.__name__)


class AcuriteLightningPacket(Packet):
    # with rtl_433 update of 19mar2017
    # 2017-03-19 16:48:31 Acurite lightning 0x976F Ch A Msg Type 0x02: 66.2 F 25 % RH Strikes 1 Distance 0 L_status 0x02 - c0 97* 6f  99  50  72  81  c0  62*
    # 2017-03-19 16:48:47 Acurite lightning 0x976F Ch A Msg Type 0x02: 66.2 F 25 % RH Strikes 1 Distance 0 L_status 0x02 - c0  97* 6f  99  50  72  81  c0  62*

    # pre-19mar2017
    # 2016-11-04 04:34:58 Acurite lightning 0x536F Ch A Msg Type 0x51: 15 C 58 % RH Strikes 50 Distance 69 - c0  53  6f  3a  d1  0f  b2  c5  13*
    # 2016-11-04 04:43:14 Acurite lightning 0x536F Ch A Msg Type 0x51: 15 C 58 % RH Strikes 55 Distance 5 - c0  53  6f  3a  d1  0f  b7  05  58*
    # 2016-11-04 04:43:22 Acurite lightning 0x536F Ch A Msg Type 0x51: 15 C 58 % RH Strikes 55 Distance 69 - c0  53  6f  3a  d1  0f  b7  c5  18
    # 2017-01-16 02:37:39 Acurite lightning 0x526F Ch A Msg Type 0x11: 67 C 38 % RH Strikes 47 Distance 81 - dd  52* 6f  a6  11  c3  af  d1  98*

    IDENTIFIER = "Acurite lightning"
    PATTERN = re.compile('0x([0-9a-fA-F]+) Ch (.) Msg Type 0x([0-9a-fA-F]+): ([\d.-]+) ([CF]) ([\d.]+) % RH Strikes ([\d]+) Distance ([\d.]+)')

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        m = AcuriteLightningPacket.PATTERN.search(lines[0])
        if m:
            pkt['dateTime'] = ts
            units = m.group(5)
            if units == 'C':
                pkt['usUnits'] = weewx.METRIC
            else:
                pkt['usUnits'] = weewx.US
            pkt['hardware_id'] = m.group(1)
            pkt['channel'] = m.group(2)
            pkt['msg_type'] = m.group(3)
            pkt['temperature'] = float(m.group(4))
            pkt['humidity'] = float(m.group(6))
            pkt['strikes_total'] = float(m.group(7))
            pkt['distance'] = float(m.group(8))
        else:
            loginf("AcuriteLightningPacket: unrecognized data: %s" % lines[0])
        lines.pop(0)
        return Acurite.insert_ids(pkt, AcuriteLightningPacket.__name__)


class Acurite00275MPacket(Packet):
    IDENTIFIER = "00275rm"

    # {"time" : "2017-03-09 21:59:11", "model" : "00275rm", "probe" : 2, "id" : 3942, "battery" : "OK", "temperature_C" : 23.300, "humidity" : 34, "ptemperature_C" : 22.700, "crc" : "ok"}

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['hardware_id'] = "%04x" % obj.get('id', 0)
        pkt['probe'] = obj.get('probe')
        pkt['battery'] = 0 if obj.get('battery') == 'OK' else 1
        pkt['temperature_probe'] = Packet.get_float(obj, 'ptemperature_C')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        return Acurite.insert_ids(pkt, Acurite00275MPacket.__name__)


class AmbientF007THPacket(Packet):
    # 2017-01-21 18:17:16 : Ambient Weather F007TH Thermo-Hygrometer
    # House Code: 80
    # Channel: 1
    # Temperature: 61.8
    # Humidity: 13 %

    IDENTIFIER = "Ambient Weather F007TH Thermo-Hygrometer"
    PARSEINFO = {
        'House Code': ['house_code', None, lambda x: int(x)],
        'Channel': ['channel', None, lambda x: int(x)],
        'Temperature': [
            'temperature', re.compile('([\d.-]+) F'), lambda x: float(x)],
        'Humidity': ['humidity', re.compile('([\d.]+) %'), lambda x: float(x)]}

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, AmbientF007THPacket.PARSEINFO))
        house_code = pkt.pop('house_code', 0)
        channel = pkt.pop('channel', 0)
        sensor_id = "%s:%s" % (channel, house_code)
        pkt = Packet.add_identifiers(
            pkt, sensor_id, AmbientF007THPacket.__name__)
        return pkt

    # {"time" : "2017-01-21 13:01:30", "model" : "Ambient Weather F007TH Thermo-Hygrometer", "device" : 80, "channel" : 1, "temperature_F" : 61.800, "humidity" : 10}

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.US
        house_code = obj.get('device', 0)
        channel = obj.get('channel')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_F')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        sensor_id = "%s:%s" % (channel, house_code)
        pkt = Packet.add_identifiers(
            pkt, sensor_id, AmbientF007THPacket.__name__)
        return pkt


class CalibeurRF104Packet(Packet):
    # 2016-11-01 01:25:28 :Calibeur RF-104
    # ID: 1
    # Temperature: 1.8 C
    # Humidity: 71 %

    # 2016-11-04 05:16:39 :Calibeur RF-104
    # ID: 1
    # Temperature: -2.2 C
    # Humidity: 71 %

    IDENTIFIER = "Calibeur RF-104"
    PARSEINFO = {
        'ID': ['id', None, lambda x: int(x)],
        'Temperature': [
            'temperature', re.compile('([\d.-]+) C'), lambda x: float(x)],
        'Humidity': ['humidity', re.compile('([\d.]+) %'), lambda x: float(x)]}

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, CalibeurRF104Packet.PARSEINFO))
        pkt_id = pkt.pop('id', 0)
        sensor_id = "%s" % pkt_id
        pkt = Packet.add_identifiers(
            pkt, sensor_id, CalibeurRF104Packet.__name__)
        return pkt


class FOWH1080Packet(Packet):
    # 2016-09-02 22:26:05 :Fine Offset WH1080 weather station
    # Msg type: 0
    # StationID: 0026
    # Temperature: 19.9 C
    # Humidity: 78 %
    # Wind string: E
    # Wind degrees: 90
    # Wind avg speed: 0.00
    # Wind gust: 1.22
    # Total rainfall: 144.3
    # Battery: OK

    # {"time" : "2016-11-04 14:40:38", "model" : "Fine Offset WH1080 weather station", "msg_type" : 0, "id" : 38, "temperature_C" : 12.500, "humidity" : 68, "direction_str" : "E", "direction_deg" : "90", "speed" : 8.568, "gust" : 12.240, "rain" : 249.600, "battery" : "OK"}

    # FIXME: verify that wind speed is kph
    # FIXME: verify that rain total is cm

    IDENTIFIER = "Fine Offset WH1080 weather station"
    PARSEINFO = {
#        'Msg type': ['msg_type', None, None],
        'StationID': ['station_id', None, None],
        'Temperature': [
            'temperature', re.compile('([\d.-]+) C'), lambda x: float(x)],
        'Humidity': [
            'humidity', re.compile('([\d.]+) %'), lambda x: float(x)],
#        'Wind string': ['wind_dir_ord', None, None],
        'Wind degrees': ['wind_dir', None, lambda x: int(x)],
        'Wind avg speed': ['wind_speed', None, lambda x: float(x)],
        'Wind gust': ['wind_gust', None, lambda x: float(x)],
        'Total rainfall': ['rain_total', None, lambda x: float(x)],
        'Battery': ['battery', None, lambda x: 0 if x == 'OK' else 1]}

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, FOWH1080Packet.PARSEINFO))
        return FOWH1080Packet.insert_ids(pkt)

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['station_id'] = obj.get('id')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['wind_dir'] = Packet.get_float(obj, 'direction_deg')
        pkt['wind_speed'] = Packet.get_float(obj, 'speed')
        pkt['wind_gust'] = Packet.get_float(obj, 'gust')
        pkt['rain_total'] = Packet.get_float(obj, 'rain')
        pkt['battery'] = 0 if obj.get('battery') == 'OK' else 1
        return FOWH1080Packet.insert_ids(pkt)

    @staticmethod
    def insert_ids(pkt):
        station_id = pkt.pop('station_id', '0000')
        pkt = Packet.add_identifiers(pkt, station_id, FOWH1080Packet.__name__)
        return pkt


class Hideki(object):
    @staticmethod
    def insert_ids(pkt, pkt_type):
        channel = pkt.pop('channel', 0)
        code = pkt.pop('rolling_code', 0)
        sensor_id = "%s:%s" % (channel, code)
        pkt = Packet.add_identifiers(pkt, sensor_id, pkt_type)
        return pkt


class HidekiTS04Packet(Packet):
    # 2016-08-31 17:41:30 :   HIDEKI TS04 sensor
    # Rolling Code: 9
    # Channel: 1
    # Battery: OK
    # Temperature: 27.30 C
    # Humidity: 60 %

    # {"time" : "2016-11-04 14:44:37", "model" : "HIDEKI TS04 sensor", "rc" : 9, "channel" : 1, "battery" : "OK", "temperature_C" : 12.400, "humidity" : 61}

    IDENTIFIER = "HIDEKI TS04 sensor"
    PARSEINFO = {
        'Rolling Code': ['rolling_code', None, lambda x: int(x)],
        'Channel': ['channel', None, lambda x: int(x)],
        'Battery': ['battery', None, lambda x: 0 if x == 'OK' else 1],
        'Temperature': [
            'temperature', re.compile('([\d.-]+) C'), lambda x: float(x)],
        'Humidity': ['humidity', re.compile('([\d.]+) %'), lambda x: float(x)]}

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, HidekiTS04Packet.PARSEINFO))
        return Hideki.insert_ids(pkt, HidekiTS04Packet.__name__)

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['rolling_code'] = obj.get('rc')
        pkt['channel'] = obj.get('channel')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['battery'] = 0 if obj.get('battery') == 'OK' else 1
        return Hideki.insert_ids(pkt, HidekiTS04Packet.__name__)


class HidekiWindPacket(Packet):
    # 2017-01-16 05:39:42 : HIDEKI Wind sensor
    # Rolling Code: 0
    # Channel: 4
    # Battery: OK
    # Temperature: -5.0 C
    # Wind Strength: 2.57 km/h
    # Direction: 45.0 \xc2\xb0

    # {"time" : "2017-01-16 04:38:39", "model" : "HIDEKI Wind sensor", "rc" : 0, "channel" : 4, "battery" : "OK", "temperature_C" : -4.400, "windstrength" : 2.897, "winddirection" : 292.500}

    IDENTIFIER = "HIDEKI Wind sensor"
    PARSEINFO = {
        'Rolling Code': ['rolling_code', None, lambda x: int(x)],
        'Channel': ['channel', None, lambda x: int(x)],
        'Battery': ['battery', None, lambda x: 0 if x == 'OK' else 1],
        'Temperature': [
            'temperature', re.compile('([\d.-]+) C'), lambda x: float(x)],
        'Wind Strength': ['wind_speed', re.compile('([\d.]+) km/h'), lambda x: float(x)],
        'Direction': ['wind_dir', re.compile('([\d.]+) '), lambda x: float(x)]}

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, HidekiWindPacket.PARSEINFO))
        return Hideki.insert_ids(pkt, HidekiWindPacket.__name__)

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['rolling_code'] = obj.get('rc')
        pkt['channel'] = obj.get('channel')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['wind_speed'] = Packet.get_float(obj, 'windstrength')
        pkt['wind_dir'] = Packet.get_float(obj, 'winddirection')
        pkt['battery'] = 0 if obj.get('battery') == 'OK' else 1
        return Hideki.insert_ids(pkt, HidekiWindPacket.__name__)


class HidekiRainPacket(Packet):
    # 2017-01-16 05:39:42 : HIDEKI Rain sensor
    # Rolling Code: 0
    # Channel: 4
    # Battery: OK
    # Rain: 2622.900

    # {"time" : "2017-01-16 04:38:50", "model" : "HIDEKI Rain sensor", "rc" : 0, "channel" : 4, "battery" : "OK", "rain" : 2622.900}

    IDENTIFIER = "HIDEKI Rain sensor"
    PARSEINFO = {
        'Rolling Code': ['rolling_code', None, lambda x: int(x)],
        'Channel': ['channel', None, lambda x: int(x)],
        'Battery': ['battery', None, lambda x: 0 if x == 'OK' else 1],
        'Rain': ['rain_total', re.compile('([\d.]+) '), lambda x: float(x)]}

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, HidekiRainPacket.PARSEINFO))
        return Hideki.insert_ids(pkt, HidekiRainPacket.__name__)

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['rolling_code'] = obj.get('rc')
        pkt['channel'] = obj.get('channel')
        pkt['rain_total'] = Packet.get_float(obj, 'rain')
        pkt['battery'] = 0 if obj.get('battery') == 'OK' else 1
        return Hideki.insert_ids(pkt, HidekiRainPacket.__name__)


class LaCrossWSPacket(Packet):
    # 2016-09-08 00:43:52 :LaCrosse WS :9 :202
    # Temperature: 21.0 C
    # 2016-09-08 00:43:53 :LaCrosse WS :9 :202
    # Humidity: 92
    # 2016-09-08 00:43:53 :LaCrosse WS :9 :202
    # Wind speed: 0.0 m/s
    # Direction: 67.500
    # 2016-11-03 17:43:20 :LaCrosse WS :9 :202
    # Rainfall: 850.04 mm

    # {"time" : "2016-11-04 14:42:49", "model" : "LaCrosse WS", "ws_id" : 9, "id" : 202, "temperature_C" : 12.100}
    # {"time" : "2016-11-04 14:44:58", "model" : "LaCrosse WS", "ws_id" : 9, "id" : 202, "humidity" : 67}
    # {"time" : "2016-11-04 14:49:16", "model" : "LaCrosse WS", "ws_id" : 9, "id" : 202, "wind_speed_ms" : 0.800, "wind_direction" : 270.000}

    IDENTIFIER = "LaCrosse WS"
    PARSEINFO = {
        'Wind speed': [
            'wind_speed', re.compile('([\d.]+) m/s'), lambda x: float(x)],
        'Direction': ['wind_dir', None, lambda x: float(x)],
        'Temperature': [
            'temperature', re.compile('([\d.-]+) C'), lambda x: float(x)],
        'Humidity': ['humidity', None, lambda x: int(x)],
        'Rainfall': [
            'rain_total', re.compile('([\d.]+) mm'), lambda x: float(x)]}

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRICWX
        pkt.update(Packet.parse_lines(lines, LaCrossWSPacket.PARSEINFO))
        parts = payload.split(':')
        if len(parts) == 3:
            pkt['ws_id'] = parts[1].strip()
            pkt['hw_id'] = parts[2].strip()
        return LaCrossWSPacket.insert_ids(pkt)

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRICWX
        pkt['ws_id'] = obj.get('ws_id')
        pkt['hw_id'] = obj.get('id')
        if 'temperature_C' in obj:
            pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        if 'humidity' in obj:
            pkt['humidity'] = Packet.get_float(obj, 'humidity')
        if 'wind_speed_ms' in obj:
            pkt['wind_speed'] = Packet.get_float(obj, 'wind_speed_ms')
        if 'wind_direction' in obj:
            pkt['wind_dir'] = Packet.get_float(obj, 'wind_direction')
        if 'rain' in obj:
            pkt['rain_total'] = Packet.get_float(obj, 'rain')
        return LaCrossWSPacket.insert_ids(pkt)

    @staticmethod
    def insert_ids(pkt):
        ws_id = pkt.pop('ws_id', 0)
        hardware_id = pkt.pop('hw_id', 0)
        sensor_id = "%s:%s" % (ws_id, hardware_id)
        pkt = Packet.add_identifiers(pkt, sensor_id, LaCrossWSPacket.__name__)
        return pkt


class LaCrosseTX141THBv2Packet(Packet):

    # {"time" : "2017-01-16 15:24:43", "temperature" : 54.140, "humidity" : 34, "id" : 221, "model" : "LaCrosse TX141TH-Bv2 sensor", "battery" : "OK", "test" : "Yes"}

    IDENTIFIER = "LaCrosse TX141TH-Bv2 sensor"

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.US
        sensor_id = obj.get('id')
        pkt['temperature'] = Packet.get_float(obj, 'temperature')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['battery'] = 0 if obj.get('battery') == 'OK' else 1
        pkt = Packet.add_identifiers(pkt, sensor_id, LaCrosseTX141THBv2Packet.__name__)
        return pkt


class RubicsonTempPacket(Packet):
    # 2017-01-15 14:49:03 : Rubicson Temperature Sensor
    # House Code: 14
    # Channel: 1
    # Battery: OK
    # Temperature: 4.5 C
    # CRC: OK

    IDENTIFIER = "Rubicson Temperature Sensor"
    PARSEINFO = {
        'House Code': ['house_code', None, lambda x: int(x)],
        'Channel': ['channel', None, lambda x: int(x)],
        'Battery': ['battery', None, lambda x: 0 if x == 'OK' else 1],
        'Temperature': ['temperature', re.compile('([\d.-]+) C'), lambda x: float(x)]}

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, RubicsonTempPacket.PARSEINFO))
        channel = pkt.pop('channel', 0)
        code = pkt.pop('house_code', 0)
        sensor_id = "%s:%s" % (channel, code)
        return Packet.add_identifiers(pkt, sensor_id, RubicsonTempPacket.__name__)

    # {"time" : "2017-01-17 20:47:41", "model" : "Rubicson Temperature Sensor", "id" : 14, "channel" : 1, "battery" : "OK", "temperature_C" : -1.800, "crc" : "OK"}

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        channel = obj.get('channel', 0)
        code = obj.get('id', 0)
        sensor_id = "%s:%s" % (channel, code)
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['battery'] = 0 if obj.get('battery') == 'OK' else 1
        return Packet.add_identifiers(pkt, sensor_id, RubicsonTempPacket.__name__)


class OS(object):
    @staticmethod
    def insert_ids(pkt, pkt_type):
        channel = pkt.pop('channel', 0)
        code = pkt.pop('house_code', 0)
        sensor_id = "%s:%s" % (channel, code)
        return Packet.add_identifiers(pkt, sensor_id, pkt_type)


class OSPCR800Packet(Packet):
    # 2016-11-03 04:36:23 : OS : PCR800
    # House Code: 93
    # Channel: 0
    # Battery: OK
    # Rain Rate: 0.0 in/hr
    # Total Rain: 41.0 in

    IDENTIFIER = "PCR800"
    PARSEINFO = {
        'House Code': ['house_code', None, lambda x: int(x)],
        'Channel': ['channel', None, lambda x: int(x)],
        'Battery': ['battery', None, lambda x: 0 if x == 'OK' else 1],
        'Rain Rate':
            ['rain_rate', re.compile('([\d.]+) in'), lambda x: float(x)],
        'Total Rain':
            ['rain_total', re.compile('([\d.]+) in'), lambda x: float(x)]}

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.US
        pkt.update(Packet.parse_lines(lines, OSPCR800Packet.PARSEINFO))
        return OS.insert_ids(pkt, OSPCR800Packet.__name__)


class OSTHGR122NPacket(Packet):
    # 2016-09-12 21:44:55     :       OS :    THGR122N
    # House Code:      96
    # Channel:         3
    # Battery:         OK
    # Temperature:     27.30 C
    # Humidity:        36 %

    IDENTIFIER = "THGR122N"
    PARSEINFO = {
        'House Code': ['house_code', None, lambda x: int(x)],
        'Channel': ['channel', None, lambda x: int(x)],
        'Battery': ['battery', None, lambda x: 0 if x == 'OK' else 1],
        'Temperature': [
            'temperature', re.compile('([\d.-]+) C'), lambda x: float(x)],
        'Humidity': ['humidity', re.compile('([\d.]+) %'), lambda x: float(x)]}

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, OSTHGR122NPacket.PARSEINFO))
        return OS.insert_ids(pkt, OSTHGR122NPacket.__name__)

    # {"time" : "2017-01-18 14:56:03", "brand" : "OS", "model" :"THGR122N", "id" : 211, "channel" : 1, "battery" : "LOW", "temperature_C" : 7.900, "humidity" : 27}

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['house_code'] = obj.get('id')
        pkt['channel'] = obj.get('channel')
        pkt['battery'] = 0 if obj.get('battery') == 'OK' else 1
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        return OS.insert_ids(pkt, OSTHGR122NPacket.__name__)


class OSTHGR810Packet(Packet):
    # rtl_433 circa jul 2016 emits this
    # 2016-09-01 22:05:47 :Weather Sensor THGR810
    # House Code: 122
    # Channel: 1
    # Battery: OK
    # Celcius: 26.70 C
    # Fahrenheit: 80.06 F
    # Humidity: 58 %

    # rtl_433 circa nov 2016 emits this
    # 2016-11-04 02:21:37 :OS :THGR810
    # House Code: 122
    # Channel: 1
    # Battery: OK
    # Celcius: 22.20 C
    # Fahrenheit: 71.96 F
    # Humidity: 57 %

    IDENTIFIER = "THGR810"
    PARSEINFO = {
        'House Code': ['house_code', None, lambda x: int(x)],
        'Channel': ['channel', None, lambda x: int(x)],
        'Battery': ['battery', None, lambda x: 0 if x == 'OK' else 1],
        'Celcius': [
            'temperature', re.compile('([\d.-]+) C'), lambda x: float(x)],
        'Fahrenheit': [
            'temperature_F', re.compile('([\d.-]+) F'), lambda x: float(x)],
        'Humidity': ['humidity', re.compile('([\d.]+) %'), lambda x: float(x)]}

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, OSTHGR810Packet.PARSEINFO))
        return OS.insert_ids(pkt, OSTHGR810Packet.__name__)

    # {"time" : "2016-11-04 14:40:05", "brand" : "OS", "model" : "THGR810", "id" : 122, "channel" : 1, "battery" : "OK", "temperature_C" : 20.900, "temperature_F" : 69.620, "humidity" : 57}

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['house_code'] = obj.get('id')
        pkt['channel'] = obj.get('channel')
        pkt['battery'] = 0 if obj.get('battery') == 'OK' else 1
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        return OS.insert_ids(pkt, OSTHGR810Packet.__name__)


class OSTHR228NPacket(Packet):
    # 2016-09-09 11:59:10 :   Thermo Sensor THR228N
    # House Code:      111
    # Channel:         2
    # Battery:         OK
    # Temperature:     24.70 C

    IDENTIFIER = "Thermo Sensor THR228N"
    PARSEINFO = {
        'House Code': ['house_code', None, lambda x: int(x)],
        'Channel': ['channel', None, lambda x: int(x)],
        'Battery': ['battery', None, lambda x: 0 if x == 'OK' else 1],
        'Temperature':
            ['temperature', re.compile('([\d.-]+) C'), lambda x : float(x)]}

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, OSTHR228NPacket.PARSEINFO))
        return OS.insert_ids(pkt, OSTHR228NPacket.__name__)


class OSUV800Packet(Packet):
    # 2017-01-30 22:00:12 : OS : UV800
    # House Code: 207
    # Channel: 1
    # Battery: OK
    # UV Index: 0

    IDENTIFIER = "UV800"
    PARSEINFO = {
        'House Code': ['house_code', None, lambda x: int(x)],
        'Channel': ['channel', None, lambda x: int(x)],
        'Battery': ['battery', None, lambda x: 0 if x == 'OK' else 1],
        'UV Index':
            ['uv_index', re.compile('([\d.-]+) C'), lambda x : float(x)]}

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, OSUV800Packet.PARSEINFO))
        return OS.insert_ids(pkt, OSUV800Packet.__name__)

    # {"time" : "2017-01-30 22:19:40", "brand" : "OS", "model" : "UV800", "id" : 207, "channel" : 1, "battery" : "OK", "uv" : 0}

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['house_code'] = obj.get('id')
        pkt['channel'] = obj.get('channel')
        pkt['battery'] = 0 if obj.get('battery') == 'OK' else 1
        pkt['uv_index'] = Packet.get_float(obj, 'uv')
        return OS.insert_ids(pkt, OSUV800Packet.__name__)


class OSWGR800Packet(Packet):
    # 2016-11-03 04:36:34 : OS : WGR800
    # House Code: 85
    # Channel: 0
    # Battery: OK
    # Gust: 1.1 m/s
    # Average: 1.1 m/s
    # Direction: 22.5 degrees

    IDENTIFIER = "WGR800"
    PARSEINFO = {
        'House Code': ['house_code', None, lambda x: int(x)],
        'Channel': ['channel', None, lambda x: int(x)],
        'Battery': ['battery', None, lambda x: 0 if x == 'OK' else 1],
        'Gust': [
            'wind_gust', re.compile('([\d.]+) m'), lambda x: float(x)],
        'Average': [
            'wind_speed', re.compile('([\d.]+) m'), lambda x: float(x)],
        'Direction': [
            'wind_dir', re.compile('([\d.]+) degrees'), lambda x: float(x)]}

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRICWX
        pkt.update(Packet.parse_lines(lines, OSWGR800Packet.PARSEINFO))
        return OS.insert_ids(pkt, OSWGR800Packet.__name__)


class ProloguePacket(Packet):
	# 2017-03-19 : Prologue Temperature and Humidity Sensor
	# {"time" : "2017-03-15 20:14:19", "model" : "Prologue sensor", "id" : 5, "rid" : 166, "channel" : 1, "battery" : "OK", "button" : 0, "temperature_C" : -0.700, "humidity" : 49}

    IDENTIFIER = "Prologue sensor"

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        sensor_id = obj.get('rid')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['battery'] = 0 if obj.get('battery') == 'OK' else 1
        pkt['channel'] = obj.get('channel')
        pkt = Packet.add_identifiers(pkt, sensor_id, ProloguePacket.__name__)
        return pkt


class PacketFactory(object):

    # FIXME: do this with class introspection
    KNOWN_PACKETS = [
        AcuriteTowerPacket,
        Acurite5n1Packet,
        Acurite986Packet,
        AcuriteLightningPacket,
        Acurite00275MPacket,
        AmbientF007THPacket,
        CalibeurRF104Packet,
        FOWH1080Packet,
        HidekiTS04Packet,
        HidekiWindPacket,
        HidekiRainPacket,
        LaCrossWSPacket,
        LaCrosseTX141THBv2Packet,
        RubicsonTempPacket,
        OSPCR800Packet,
        OSTHGR122NPacket,
        OSTHGR810Packet,
        OSTHR228NPacket,
        OSUV800Packet,
        OSWGR800Packet,
        ProloguePacket]

    @staticmethod
    def create(lines):
        # return a list of packets from the specified lines
        logdbg("lines=%s" % lines)
        while lines:
            pkt = None
            if lines[0].startswith('{'):
                pkt = PacketFactory.parse_json(lines)
                if pkt is None:
                    logdbg("punt unrecognized line '%s'" % lines[0])
                lines.pop(0)
            else:
                pkt = PacketFactory.parse_text(lines)
            if pkt is not None:
                yield pkt

    @staticmethod
    def parse_json(lines):
        try:
            obj = json.loads(lines[0])
            if 'model' in obj:
                for parser in PacketFactory.KNOWN_PACKETS:
                    if obj['model'].find(parser.IDENTIFIER) >= 0:
                        return parser.parse_json(obj)
                logdbg("parse_json: unknown model %s" % obj['model'])
        except ValueError, e:
            logdbg("parse_json failed: %s" % e)
        return None

    @staticmethod
    def parse_text(lines):
        ts, payload = PacketFactory.parse_firstline(lines[0])
        if ts and payload:
            logdbg("parse_text: ts=%s payload=%s" % (ts, payload))
            for parser in PacketFactory.KNOWN_PACKETS:
                if payload.find(parser.IDENTIFIER) >= 0:
                    pkt = parser.parse_text(ts, payload, lines)
                    logdbg("pkt=%s" % pkt)
                    return pkt
            logdbg("parse_text: unknown format: ts=%s payload=%s" %
                   (ts, payload))
        logdbg("parse_text failed: ts=%s payload=%s line=%s" %
               (ts, payload, lines[0]))
        lines.pop(0)
        return None

    TS_PATTERN = re.compile('(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d)[\s]+:*(.*)')

    @staticmethod
    def parse_firstline(line):
        ts = payload = None
        try:
            m = PacketFactory.TS_PATTERN.search(line)
            if m:
                utc = time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                ts = timegm(utc)
                payload = m.group(2).strip()
        except Exception, e:
            logerr("parse timestamp failed for '%s': %s" % (line, e))
        return ts, payload


class SDRConfigurationEditor(weewx.drivers.AbstractConfEditor):
    @property
    def default_stanza(self):
        return """
[SDR]
    # This section is for the software-defined radio driver.

    # The driver to use
    driver = user.sdr

    # How to invoke the rtl_433 command
#    cmd = %s

    # The sensor map associates observations with database fields.  Each map
    # element consists of a tuple on the left and a database field name on the
    # right.  The tuple on the left consists of:
    #
    #   <observation_name>.<sensor_identifier>.<packet_type>
    #
    # The sensor_identifier is hardware-specific.  For example, Acurite sensors
    # have a 4 character hexadecimal identifier, whereas fine offset sensor
    # clusters have a 4 digit identifier.
    #
    # glob-style pattern matching is supported for the sensor_identifier.
    #
# map data from any fine offset sensor cluster to database field names
#    [[sensor_map]]
#        windGust = wind_gust.*.FOWH1080Packet
#        outBatteryStatus = battery.*.FOWH1080Packet
#        rain_total = rain_total.*.FOWH1080Packet
#        windSpeed = wind_speed.*.FOWH1080Packet
#        windDir = wind_dir.*.FOWH1080Packet
#        outHumidity = humidity.*.FOWH1080Packet
#        outTemp = temperature.*.FOWH1080Packet

""" % DEFAULT_CMD


class SDRDriver(weewx.drivers.AbstractDevice):

    # map the counter total to the counter delta.  for example, the pair
    #   rain:rain_total
    # will result in a delta called 'rain' from the cumulative 'rain_total'.
    # these are applied to mapped packets.
    DEFAULT_DELTAS = {
        'rain': 'rain_total',
        'strikes': 'strikes_total'}

    def __init__(self, **stn_dict):
        loginf('driver version is %s' % DRIVER_VERSION)
        self._log_unknown = tobool(stn_dict.get('log_unknown_sensors', False))
        self._log_unmapped = tobool(stn_dict.get('log_unmapped_sensors', False))
        self._sensor_map = stn_dict.get('sensor_map', {})
        loginf('sensor map is %s' % self._sensor_map)
        self._deltas = stn_dict.get('deltas', SDRDriver.DEFAULT_DELTAS)
        loginf('deltas is %s' % self._deltas)
        self._counter_values = dict()
        cmd = stn_dict.get('cmd', DEFAULT_CMD)
        path = stn_dict.get('path', None)
        ld_library_path = stn_dict.get('ld_library_path', None)
        self._last_pkt = None # avoid duplicate sequential packets
        self._mgr = ProcManager()
        self._mgr.startup(cmd, path, ld_library_path)

    def closePort(self):
        self._mgr.shutdown()

    def hardware_name(self):
        return 'SDR'

    def genLoopPackets(self):
        while self._mgr.running():
            for lines in self._mgr.get_stdout():
                for packet in PacketFactory.create(lines):
                    if packet:
                        packet = self.map_to_fields(packet, self._sensor_map)
                        if packet:
                            if packet != self._last_pkt:
                                logdbg("packet=%s" % packet)
                                self._last_pkt = packet
                                self._calculate_deltas(packet)
                                yield packet
                            else:
                                logdbg("ignoring duplicate packet %s" % packet)
                        elif self._log_unmapped:
                            loginf("unmapped: %s (%s)" % (lines, packet))
                    elif self._log_unknown:
                        loginf("unparsed: %s" % lines)
            self._mgr.get_stderr() # flush the stderr queue
        else:
            logerr("err: %s" % self._mgr.get_stderr())
            raise weewx.WeeWxIOError("rtl_433 process is not running")

    def _calculate_deltas(self, pkt):
        for k in self._deltas:
            label = self._deltas[k]
            if label in pkt:
                pkt[k] = self._calculate_delta(
                    label, pkt[label], self._counter_values.get(label))
                self._counter_values[label] = pkt[label]

    @staticmethod
    def _calculate_delta(label, newtotal, oldtotal):
        delta = None
        if newtotal is not None and oldtotal is not None:
            if newtotal >= oldtotal:
                delta = newtotal - oldtotal
            else:
                loginf("%s decrement ignored:"
                       " new: %s old: %s" % (label, newtotal, oldtotal))
        return delta

    @staticmethod
    def map_to_fields(pkt, sensor_map):
        # selectively get elements from the packet using the specified sensor
        # map.  if the identifier is found, then use its value.  if not, then
        # skip it completely (it is not given a None value).  include the
        # time stamp and unit system only if we actually got data.
        packet = dict()
        for n in sensor_map.keys():
            label = SDRDriver._find_match(sensor_map[n], pkt.keys())
            if label:
                packet[n] = pkt.get(label)
        if packet:
            for k in ['dateTime', 'usUnits']:
                packet[k] = pkt[k]
        return packet

    @staticmethod
    def _find_match(pattern, keylist):
        # find the first key in pkt that matches the specified pattern.
        # the general form of a pattern is:
        #   <observation_name>.<sensor_id>.<packet_type>
        # do glob-style matching.
        if pattern in keylist:
            return pattern
        match = None
        pparts = pattern.split('.')
        if len(pparts) == 3:
            for k in keylist:
                kparts = k.split('.')
                if (len(kparts) == 3 and
                    SDRDriver._part_match(pparts[0], kparts[0]) and
                    SDRDriver._part_match(pparts[1], kparts[1]) and
                    SDRDriver._part_match(pparts[2], kparts[2])):
                    match = k
                    break
                elif pparts[0] == k:
                    match = k
                    break
        return match

    @staticmethod
    def _part_match(pattern, value):
        # use glob matching for parts of the tuple
        matches = fnmatch.filter([value], pattern)
        return True if matches else False


if __name__ == '__main__':
    import optparse

    usage = """%prog [--debug] [--help] [--version]
        [--action=(show-packets | show-detected | list-supported)]
        [--cmd=RTL_CMD] [--path=PATH] [--ld_library_path=LD_LIBRARY_PATH]

Actions:
  show-packets: display each packet (default)
  show-detected: display a running count of the number of each packet type
  list-supported: show a list of the supported packet types

Hide:
  This is a comma-separate list of the types of data that should not be
  displayed.  Default is to show everything."""

    syslog.openlog('sdr', syslog.LOG_PID | syslog.LOG_CONS)
    syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_INFO))
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('--version', dest='version', action='store_true',
                      help='display driver version')
    parser.add_option('--debug', dest='debug', action='store_true',
                      help='display diagnostic information while running')
    parser.add_option('--cmd', dest='cmd', default=DEFAULT_CMD,
                      help='rtl_433 command with options')
    parser.add_option('--path', dest='path',
                      help='value for PATH')
    parser.add_option('--ld_library_path', dest='ld_library_path',
                      help='value for LD_LIBRARY_PATH')
    parser.add_option('--hide', dest='hidden', default='empty',
                      help='output to be hidden: out, parsed, unparsed, empty')
    parser.add_option('--action', dest='action', default='show-packets',
                      help='actions include show-packets, show-detected, list-supported')

    (options, args) = parser.parse_args()

    if options.version:
        print "sdr driver version %s" % DRIVER_VERSION
        exit(1)

    if options.debug:
        syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_DEBUG))

    if options.action == 'list-supported':
        for pt in PacketFactory.KNOWN_PACKETS:
            print pt.IDENTIFIER
    elif options.action == 'show-detected':
        # display identifiers for detected sensors
        mgr = ProcManager()
        mgr.startup(options.cmd, path=options.path,
                    ld_library_path=options.ld_library_path)
        detected = dict()
        for lines in mgr.get_stdout():
#            print "out:", lines
            for p in PacketFactory.create(lines):
                if p:
                    del p['usUnits']
                    del p['dateTime']
                    keys = p.keys()
                    label = re.sub(r'^[^\.]+', '', keys[0])
                    if label not in detected:
                        detected[label] = 0
                    detected[label] += 1
                print detected
    else:
        # display output and parsed/unparsed packets
        hidden = [x.strip() for x in options.hidden.split(',')]
        mgr = ProcManager()
        mgr.startup(options.cmd, path=options.path,
                    ld_library_path=options.ld_library_path)
        for lines in mgr.get_stdout():
            if 'out' not in hidden and (
                'empty' not in hidden or len(lines)):
                print "out:", lines
            for p in PacketFactory.create(lines):
                if p:
                    if 'parsed' not in hidden:
                        print 'parsed: %s' % p
                else:
                    if 'unparsed' not in hidden and (
                        'empty' not in hidden or len(lines)):
                        print "unparsed:", lines
        for lines in mgr.get_stderr():
            print "err:", lines
