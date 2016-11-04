#!/usr/bin/env python
# Copyright 2016 Matthew Wall, all rights reserved
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

import weewx.drivers
from weeutil.weeutil import tobool

DRIVER_NAME = 'SDR'
DRIVER_VERSION = '0.12'

# -q - suppress non-data messages
# -U - print timestamps in UTC
# -F json - emit data in json format (not all rtl_433 drivers support this)
DEFAULT_CMD = 'rtl_433 -q -U'


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
        self.setDaemon(True)
        self.setName(label)

    def run(self):
        for line in iter(self._fd.readline, ''):
            self._queue.put(line)

    def eof(self):
        return not self.is_alive() and self._queue.empty()


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
        self.stdout_reader.join(10.0)
        self.stdout_reader = None
        self.stderr_reader.join(10.0)
        self.stderr_reader = None
        self._process.stdout.close()
        self._process.stderr.close()
        self._process.terminate()
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
    TS_PATTERN = re.compile('(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d)[\s]+:*(.*)')

    @staticmethod
    def get_timestamp(line):
        ts = payload = None
        try:
            m = Packet.TS_PATTERN.search(line)
            if m:
                utc = time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                ts = timegm(utc)
                payload = m.group(2).strip()
        except Exception, e:
            logerr("parse timestamp failed for '%s': %s" % (line, e))
        return ts, payload

    @staticmethod
    def parse_lines(lines, parseinfo={}):
        # parse each line, splitting on colon for name:value
        # tuple in parseinfo is label, pattern, lambda
        # if there is a label, use it to transform the name
        # if there is a pattern, use it to match the value
        # if there is a lamba, use it to conver the value
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


class AcuriteTowerPacket(Packet):
    # 2016-08-30 23:57:20 Acurite tower sensor 0x37FC Ch A: 26.7 C 80.1 F 16 % RH

    IDENTIFIER = "Acurite tower sensor"
    PATTERN = re.compile('0x([0-9a-fA-F]+) Ch ([A-C]): ([\d.]+) C ([\d.]+) F ([\d]+) % RH')
    @staticmethod
    def parse(ts, payload, lines):
        pkt = dict()
        m = AcuriteTowerPacket.PATTERN.search(lines[0])
        if m:
            pkt['dateTime'] = ts
            pkt['usUnits'] = weewx.METRIC
            hardware_id = m.group(1)
            channel = m.group(2)
            pkt['temperature'] = float(m.group(3))
            pkt['temperature_F'] = float(m.group(4))
            pkt['humidity'] = float(m.group(5))
            pkt = Packet.add_identifiers(
                pkt, hardware_id, AcuriteTowerPacket.__name__)
        else:
            loginf("AcuriteTowerPacket: unrecognized data: '%s'" % lines[0])
        return pkt


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
    MSG38 = re.compile('Wind ([\d.]+) kmph / ([\d.]+) mph, ([\d.]+) C ([\d.]+) F ([\d.]+) % RH')

    @staticmethod
    def parse(ts, payload, lines):
        pkt = dict()
        m = Acurite5n1Packet.PATTERN.search(lines[0])
        if m:
            pkt['dateTime'] = ts
            pkt['usUnits'] = weewx.METRIC
            hardware_id = m.group(1)
            channel = m.group(2)
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
                        pkt = Packet.add_identifiers(
                            pkt, hardware_id, Acurite5n1Packet.__name__)
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
                        pkt = Packet.add_identifiers(
                            pkt, hardware_id, Acurite5n1Packet.__name__)
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
                    loginf("Acurite5n1Packet: rain since reset: %s" % total)
                    pkt['rain_since_reset'] = total
                    pkt = Packet.add_identifiers(
                        pkt, hardware_id, Acurite5n1Packet.__name__)
                else:
                    loginf("Acurite5n1Packet: unknown message format: '%s'" %
                           lines[0])
        else:
            loginf("Acurite5n1Packet: unrecognized data: '%s'" % lines[0])
        return pkt


class Acurite986Packet(Packet):
    # 2016-10-28 02:28:20 Acurite 986 sensor 0x2c87 - 2F: 20.0 C 68 F
    # 2016-10-31 15:24:29 Acurite 986 sensor 0x2c87 - 2F: 16.7 C 62 F
    # 2016-10-31 15:23:54 Acurite 986 sensor 0x85ed - 1R: 16.7 C 62 F

    IDENTIFIER = "Acurite 986 sensor"
    PATTERN = re.compile('0x([0-9a-fA-F]+) - 2F: ([\d.]+) C ([\d.]+) F')
    #PATTERN = re.compile('0x([0-9a-fA-F]+) - ([0-9a-fA-F]+): ([\d.]+) C ([\d.]+) F')

    @staticmethod
    def parse(ts, payload, lines):
        pkt = dict()
        m = Acurite986Packet.PATTERN.search(lines[0])
        if m:
            pkt['dateTime'] = ts
            pkt['usUnits'] = weewx.METRIC
            hardware_id = m.group(1)
            #channel = m.group(2)
            pkt['temperature'] = float(m.group(2))
            pkt['temperature_F'] = float(m.group(3))
            pkt = Packet.add_identifiers(
                pkt, hardware_id, Acurite986Packet.__name__)
        else:
            loginf("Acurite986Packet: unrecognized data: '%s'" % lines[0])
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

    # FIXME: verify that wind speed is kph
    # FIXME: verify that rain total is cm

    IDENTIFIER = "Fine Offset WH1080 weather station"
    PARSEINFO = {
#        'Msg type': ['msg_type', None, None],
        'StationID': ['station_id', None, None],
        'Temperature': [
            'temperature', re.compile('([\d.]+) C'), lambda x : float(x)],
        'Humidity': [
            'humidity', re.compile('([\d.]+) %'), lambda x : float(x)],
#        'Wind string': ['wind_dir_ord', None, None],
        'Wind degrees': ['wind_dir', None, lambda x : int(x)],
        'Wind avg speed': ['wind_speed', None, lambda x : float(x)],
        'Wind gust': ['wind_gust', None, lambda x : float(x)],
        'Total rainfall': ['rain_total', None, lambda x : float(x)],
        'Battery': ['battery', None, lambda x : 0 if x == 'OK' else 1]
        }
    @staticmethod
    def parse(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, FOWH1080Packet.PARSEINFO))
        station_id = pkt.pop('station_id', '0000')
        pkt = Packet.add_identifiers(pkt, station_id, FOWH1080Packet.__name__)
        return pkt


class HidekiTS04Packet(Packet):
    # 2016-08-31 17:41:30 :   HIDEKI TS04 sensor
    # Rolling Code: 9
    # Channel: 1
    # Battery: OK
    # Temperature: 27.30 C
    # Humidity: 60 %

    IDENTIFIER = "HIDEKI TS04 sensor"
    PARSEINFO = {
        'Rolling Code': ['rolling_code', None, lambda x : int(x)],
        'Channel': ['channel', None, lambda x : int(x)],
        'Battery': ['battery', None, lambda x : 0 if x == 'OK' else 1],
        'Temperature':
            ['temperature', re.compile('([\d.]+) C'), lambda x : float(x)],
        'Humidity': ['humidity', re.compile('([\d.]+) %'), lambda x : float(x)]
        }
    @staticmethod
    def parse(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, HidekiTS04Packet.PARSEINFO))
        channel = pkt.pop('channel', 0)
        code = pkt.pop('rolling_code', 0)
        sensor_id = "%s:%s" % (channel, code)
        pkt = Packet.add_identifiers(pkt, sensor_id, HidekiTS04Packet.__name__)
        return pkt


class OSTHGR122NPacket(Packet):
    # 2016-09-12 21:44:55     :       OS :    THGR122N
    # House Code:      96
    # Channel:         3
    # Battery:         OK
    # Temperature:     27.30 C
    # Humidity:        36 %

    IDENTIFIER = "THGR122N"
    PARSEINFO = {
        'House Code': ['house_code', None, lambda x : int(x) ],
        'Channel': ['channel', None, lambda x : int(x) ],
        'Battery': ['battery', None, lambda x : 0 if x == 'OK' else 1],
        'Temperature':
            ['temperature', re.compile('([\d.]+) C'), lambda x : float(x)],
        'Humidity': ['humidity', re.compile('([\d.]+) %'), lambda x : float(x)]
        }
    @staticmethod
    def parse(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, OSTHGR122NPacket.PARSEINFO))
        channel = pkt.pop('channel', 0)
        code = pkt.pop('house_code', 0)
        sensor_id = "%s:%s" % (channel, code)
        pkt = Packet.add_identifiers(pkt, sensor_id, OSTHGR122NPacket.__name__)
        return pkt


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
        'House Code': ['house_code', None, lambda x : int(x) ],
        'Channel': ['channel', None, lambda x : int(x) ],
        'Battery': ['battery', None, lambda x : 0 if x == 'OK' else 1],
        'Celcius':
            ['temperature', re.compile('([\d.]+) C'), lambda x : float(x)],
        'Fahrenheit':
            ['temperature_F', re.compile('([\d.]+) F'), lambda x : float(x)],
        'Humidity': ['humidity', re.compile('([\d.]+) %'), lambda x : float(x)]
        }
    @staticmethod
    def parse(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, OSTHGR810Packet.PARSEINFO))
        channel = pkt.pop('channel', 0)
        code = pkt.pop('house_code', 0)
        sensor_id = "%s:%s" % (channel, code)
        pkt = Packet.add_identifiers(pkt, sensor_id, OSTHGR810Packet.__name__)
        return pkt


class OSTHR228NPacket(Packet):
    # 2016-09-09 11:59:10 :   Thermo Sensor THR228N
    # House Code:      111
    # Channel:         2
    # Battery:         OK
    # Temperature:     24.70 C

    IDENTIFIER = "Thermo Sensor THR228N"
    PARSEINFO = {
        'House Code': ['house_code', None, lambda x : int(x) ],
        'Channel': ['channel', None, lambda x : int(x) ],
        'Battery': ['battery', None, lambda x : 0 if x == 'OK' else 1],
        'Temperature':
            ['temperature', re.compile('([\d.]+) C'), lambda x : float(x)]
        }
    @staticmethod
    def parse(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, OSTHR228NPacket.PARSEINFO))
        channel = pkt.pop('channel', 0)
        code = pkt.pop('house_code', 0)
        sensor_id = "%s:%s" % (channel, code)
        pkt = Packet.add_identifiers(pkt, sensor_id, OSTHR228NPacket.__name__)
        return pkt


class OSPCR800Packet(Packet):
    # 2016-11-03 04:36:23 : OS : PCR800
    # House Code: 93
    # Channel: 0
    # Battery: OK
    # Rain Rate: 0.0 in/hr
    # Total Rain: 41.0 in

    IDENTIFIER = "PCR800"
    PARSEINFO = {
        'House Code': ['house_code', None, lambda x : int(x) ],
        'Channel': ['channel', None, lambda x : int(x) ],
        'Battery': ['battery', None, lambda x : 0 if x == 'OK' else 1],
        'Rain Rate':
            ['rain_rate', re.compile('([\d.]+) in'), lambda x : float(x)],
        'Total Rain':
            ['rain_total', re.compile('([\d.]+) in'), lambda x : float(x)]
        }
    @staticmethod
    def parse(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.US
        pkt.update(Packet.parse_lines(lines, OSPCR800Packet.PARSEINFO))
        channel = pkt.pop('channel', 0)
        code = pkt.pop('house_code', 0)
        sensor_id = "%s:%s" % (channel, code)
        pkt = Packet.add_identifiers(pkt, sensor_id, OSPCR800Packet.__name__)
        return pkt


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
        'House Code': ['house_code', None, lambda x : int(x) ],
        'Channel': ['channel', None, lambda x : int(x) ],
        'Battery': ['battery', None, lambda x : 0 if x == 'OK' else 1],
        'Gust':
            ['wind_gust', re.compile('([\d.]+) m'), lambda x : float(x)],
        'Average':
            ['wind_speed', re.compile('([\d.]+) m'), lambda x : float(x)],
        'Direction':
            ['wind_dir', re.compile('([\d.]+) degrees'), lambda x : float(x)]
        }
    @staticmethod
    def parse(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRICWX
        pkt.update(Packet.parse_lines(lines, OSWGR800Packet.PARSEINFO))
        channel = pkt.pop('channel', 0)
        code = pkt.pop('house_code', 0)
        sensor_id = "%s:%s" % (channel, code)
        pkt = Packet.add_identifiers(pkt, sensor_id, OSWGR800Packet.__name__)
        return pkt


class LaCrossePacket(Packet):
    # 2016-09-08 00:43:52 :LaCrosse WS :9 :202
    # Temperature: 21.0 C
    # 2016-09-08 00:43:53 :LaCrosse WS :9 :202
    # Humidity: 92
    # 2016-09-08 00:43:53 :LaCrosse WS :9 :202
    # Wind speed: 0.0 m/s
    # Direction: 67.500
    # 2016-11-03 17:43:20 :LaCrosse WS :9 :202
    # Rainfall: 850.04 mm

    IDENTIFIER = "LaCrosse WS"
    PARSEINFO = {
        'Wind speed':
            ['wind_speed', re.compile('([\d.]+) m/s'), lambda x : float(x)],
        'Direction': ['wind_dir', None, lambda x : float(x)],
        'Temperature':
            ['temperature', re.compile('([\d.]+) C'), lambda x : float(x)],
        'Humidity': ['humidity', None, lambda x : int(x)],
        'Rainfall':
            ['rain_total', re.compile('([\d.]+) mm'), lambda x : float(x)]
        }
    @staticmethod
    def parse(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRICWX
        pkt.update(Packet.parse_lines(lines, LaCrossePacket.PARSEINFO))
        sensor_id = ''
        parts = payload.split(':')
        if len(parts) == 3:
            sensor_id = "%s:%s" % (parts[1].strip(), parts[2].strip())
        pkt = Packet.add_identifiers(pkt, sensor_id, LaCrossePacket.__name__)
        return pkt


class CalibeurRF104Packet(Packet):
    # 2016-11-01 01:25:28 :Calibeur RF-104
    # ID: 1
    # Temperature: 1.8 C
    # Humidity: 71 %

    IDENTIFIER = "Calibeur RF-104"
    PARSEINFO = {
        'ID': ['id', None, lambda x : int(x)],
        'Temperature':
            ['temperature', re.compile('([\d.]+) C'), lambda x : float(x)],
        'Humidity': ['humidity', re.compile('([\d.]+) %'), lambda x : float(x)]
        }
    @staticmethod
    def parse(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, CalibeurRF104Packet.PARSEINFO))
        pkt_id = pkt.pop('id', 0)
        sensor_id = "%s" % pkt_id
        pkt = Packet.add_identifiers(
            pkt, sensor_id, CalibeurRF104Packet.__name__)
        return pkt


class PacketFactory(object):

    Packet.KNOWN_PACKETS = [
        FOWH1080Packet,
        AcuriteTowerPacket,
        Acurite5n1Packet,
        Acurite986Packet,
        HidekiTS04Packet,
        OSTHGR122NPacket,
        OSTHGR810Packet,
        OSTHR228NPacket,
        OSPCR800Packet,
        OSWGR800Packet,
        LaCrossePacket,
        CalibeurRF104Packet]

    @staticmethod
    def create(lines):
        logdbg("lines=%s" % lines)
        if lines:
            ts, payload = Packet.get_timestamp(lines[0])
            logdbg("ts=%s payload=%s" % (ts, payload))
            if ts and payload:
                for parser in Packet.KNOWN_PACKETS:
                    if payload.find(parser.IDENTIFIER) >= 0:
                        pkt = parser.parse(ts, payload, lines)
                        logdbg("pkt=%s" % pkt)
                        return pkt
                logdbg("unhandled message format: ts=%s payload=%s" %
                       (ts, payload))
        return None


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
    DEFAULT_DELTAS = {'rain': 'rain_total'}

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
                packet = PacketFactory.create(lines)
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
                value = pkt[label]
                last_value = self._counter_values.get(label)
                if (value is not None and last_value is not None and
                    value < last_value):
                    loginf("%s decrement ignored:"
                           " new: %s old: %s" % (label, value, last_value))
                pkt[k] = self._calculate_delta(value, last_value)
                self._counter_values[label] = value

    @staticmethod
    def _calculate_delta(newtotal, oldtotal):
        delta = None
        if(newtotal is not None and oldtotal is not None and
           newtotal >= oldtotal):
            delta = newtotal - oldtotal
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

    usage = """%prog [--debug] [--help]
        [--version]
        [--action=(show-packets | show-detected | list-supported)]
        [--cmd=RTL_CMD] [--path=PATH] [--ld_library_path=LD_LIBRARY_PATH]"""

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
    parser.add_option('--filter', dest='filter', default='empty',
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
        for pt in Packet.KNOWN_PACKETS:
            print pt.IDENTIFIER
    elif options.action == 'show-detected':
        # display identifiers for detected sensors
        mgr = ProcManager()
        mgr.startup(options.cmd, path=options.path,
                    ld_library_path=options.ld_library_path)
        detected = dict()
        for lines in mgr.get_stdout():
#            print "out:", lines
            packet = PacketFactory.create(lines)
            if packet:
                del packet['usUnits']
                del packet['dateTime']
                keys = packet.keys()
                label = re.sub(r'^[^\.]+', '', keys[0])
                if label not in detected:
                    detected[label] = 0
                detected[label] += 1
            print detected
    else:
        # display output and parsed/unparsed packets
        hidden = [x.strip() for x in options.filter.split(',')]
        mgr = ProcManager()
        mgr.startup(options.cmd, path=options.path,
                    ld_library_path=options.ld_library_path)
        for lines in mgr.get_stdout():
            if 'out' not in hidden and (
                'empty' not in hidden or len(lines)):
                print "out:", lines
            packet = PacketFactory.create(lines)
            if packet:
                if 'parsed' not in hidden:
                    print 'parsed: %s' % packet
            else:
                if 'unparsed' not in hidden and (
                    'empty' not in hidden or len(lines)):
                    print "unparsed:", lines
        for lines in mgr.get_stderr():
            print "err:", lines
