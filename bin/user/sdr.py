#!/usr/bin/env python
# Copyright 2016 Matthew Wall, all rights reserved
"""
Collect data from stl-sdr.  Run rtl_433 on a thread and push the output onto
a queue.
"""

# FIXME: make packet parsers dynamically loadable

from __future__ import with_statement
from calendar import timegm
import Queue
import re
import subprocess
import syslog
import threading
import time

import weewx.drivers
from weeutil.weeutil import tobool

DRIVER_NAME = 'SDR'
DRIVER_VERSION = '0.3'

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
#        return not self.is_alive() and self._queue.empty()
        return not self.is_alive()


class ProcManager():
    TS = re.compile('^\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d[\s]+')

    def __init__(self):
        self._process = None
        self.stdout_queue = Queue.Queue()
        self.stdout_reader = None

    def startup(self, cmd):
        loginf("startup process '%s'" % cmd)
        self._process = subprocess.Popen(cmd,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        self.stdout_reader = AsyncReader(
            self._process.stdout, self.stdout_queue, 'stdout-thread')
        self.stdout_reader.start()

    def process(self):
        lines = []
        while not self.stdout_reader.eof():
            try:
                line = self.stdout_queue.get(True, 10)
                m = ProcManager.TS.search(line)
                if m and lines:
                    yield lines
                    lines = []
                lines.append(line)
            except Queue.Empty:
                yield lines
                lines = []

    def shutdown(self):
        loginf('shutdown process')
        self.stdout_reader.join(10.0)
        self._process.stdout.close()
        self._process = None


class Packet:
    TS_PATTERN = re.compile('(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d)[\s]+:*(.*)')

    KNOWN_PACKETS = []

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
        # tuble is label, pattern, lambda
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
            sensor_id = m.group(1)
            channel = m.group(2)
            pkt['temperature'] = float(m.group(3))
            pkt['temperature_F'] = float(m.group(4))
            pkt['humidity'] = float(m.group(5))
            pkt = Packet.add_identifiers(
                pkt, sensor_id, AcuriteTowerPacket.__name__)
        else:
            loginf("AcuriteTowerPacket: unrecognized data: '%s'" % lines[0])
        return pkt


class Acurite5n1Packet(Packet):
    # 2016-08-31 16:41:39 Acurite 5n1 sensor 0x0BFA Ch C, Msg 31, Wind 15 kmph / 9.3 mph 270.0^ W (3), rain gauge 0.00 in
    # 2016-08-30 23:57:25 Acurite 5n1 sensor 0x0BFA Ch C, Msg 38, Wind 2 kmph / 1.2 mph, 21.3 C 70.3 F 70 % RH

    IDENTIFIER = "Acurite 5n1 sensor"
    PATTERN = re.compile('0x([0-9a-fA-F]+) Ch ([A-C]), (.*)')
    RAIN = re.compile('Total rain fall since last reset: ([\d.]+)')
    MSG = re.compile('Msg (\d+), (.*)')
    MSG31 = re.compile('Wind ([\d.]+) kmph / ([\d.]+) mph ([\d.]+)')
    MSG38 = re.compile('Wind ([\d.]+) kmph / ([\d.]+) mph, ([\d.]+) C ([\d.]+) F ([\d.]+) % RH')

    @staticmethod
    def parse(ts, payload, lines):
        pkt = dict()
        m = Acurite5n1Packet.PATTERN.search(lines[0])
        if m:
            pkt['dateTime'] = ts
            pkt['usUnits'] = weewx.METRIC
            sensor_id = m.group(1)
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
                        pkt = Packet.add_identifiers(
                            pkt, sensor_id, Acurite5n1Packet.__name__)
                elif msg_type == '38':
                    m = Acurite5n1Packet.MSG38.search(payload)
                    if m:
                        pkt['wind_speed'] = float(m.group(1))
                        pkt['wind_speed_mph'] = float(m.group(2))
                        pkt['temperature'] = float(m.group(3))
                        pkt['temperature_F'] = float(m.group(4))
                        pkt['humidity'] = float(m.group(5))
                        pkt = Packet.add_identifiers(
                            pkt, sensor_id, Acurite5n1Packet.__name__)
                else:
                    loginf("Acurite5n1Packet: unknown message type %s"
                           " in line '%s'" % (msg_type, lines[0]))
            else:
                m = Acurite5n1Packet.RAIN.search(payload)
                if m:
                    pkt['rain_total'] = float(m.group(1))
                    pkt = Packet.add_identifiers(
                        pkt, sensor_id, Acurite5n1Packet.__name__)
                else:
                    loginf("Acurite5n1Packet: unknown message format: '%s'" %
                           lines[0])
        else:
            loginf("Acurite5n1Packet: unrecognized data: '%s'" % lines[0])
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


class OSTHGR810Packet(Packet):
    # 2016-09-01 22:05:47 :Weather Sensor THGR810
    # House Code: 122
    # Channel: 1
    # Battery: OK
    # Celcius: 26.70 C
    # Fahrenheit: 80.06 F
    # Humidity: 58 %

    IDENTIFIER = "Weather Sensor THGR810"
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


class LaCrossePacket(Packet):
    # 2016-09-08 00:43:52 :LaCrosse WS :9 :202
    # Temperature: 21.0 C
    # 2016-09-08 00:43:53 :LaCrosse WS :9 :202
    # Humidity: 92
    # 2016-09-08 00:43:53 :LaCrosse WS :9 :202
    # Wind speed: 0.0 m/s
    # Direction: 67.500

    IDENTIFIER = "LaCrosse WS"
    PARSEINFO = {
        'Wind speed':
            ['wind_speed', re.compile('([\d.]+) m/s'), lambda x : float(x)],
        'Direction': ['wind_dir', None, lambda x : float(x)],
        'Temperature':
            ['temperature', re.compile('([\d.]+) C'), lambda x : float(x)],
        'Humidity': ['humidity', None, lambda x : int(x)]
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


class SDRConfigurationEditor(weewx.drivers.AbstractConfEditor):
    @property
    def default_stanza(self):
        return """
[SDR]
    # This section is for the software-defined radio driver.

    # The driver to use
    driver = user.sdr

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
# map data from any fine offset sensor cluster to database field names
#    [[sensor_map]]
#        wind_gust.*.FOWH1080Packet = windGust
#        battery.*.FOWH1080Packet = outBatteryStatus
#        total_rain.*.FOWH1080Packet = rain
#        wind_speed.*.FOWH1080Packet = windSpeed
#        wind_dir.*.FOWH1080Packet = windDir
#        humidity.*.FOWH1080Packet = outHumidity
#        temperature.*.FOWH1080Packet = outTemp

"""


class SDRDriver(weewx.drivers.AbstractDevice):

    def __init__(self, **stn_dict):
        loginf('driver version is %s' % DRIVER_VERSION)
        self._log_unknown = tobool(stn_dict.get('log_unknown_sensors', False))
        self._log_unmapped = tobool(stn_dict.get('log_unmapped_sensors', False))
        self._obs_map = stn_dict.get('sensor_map', None)
        loginf('sensor map is %s' % self._obs_map)
        self._cmd = stn_dict.get('cmd', 'rtl_433')
        self._last_pkt = None # avoid duplicate sequential packets
        # FIXME: make this list dynamically loadable
        Packet.KNOWN_PACKETS = [
            FOWH1080Packet,
            AcuriteTowerPacket,
            Acurite5n1Packet,
            HidekiTS04Packet,
            OSTHGR810Packet,
            LaCrossePacket]
        self._mgr = ProcManager()
        self._mgr.startup(self._cmd)

    def closePort(self):
        self._mgr.shutdown()

    def hardware_name(self):
        return 'SDR'

    def genLoopPackets(self):
        for lines in self._mgr.process():
            packet = Packet.create(lines)
            if packet:
                packet = self.map_to_fields(packet, self._obs_map)
                if packet:
                    if packet != self._last_pkt:
                        logdbg("packet=%s" % packet)
                        self._last_pkt = packet
                        yield packet
                    else:
                        logdbg("ignoring duplicate packet %s" % packet)
                elif self._log_unmapped:
                    loginf("unmapped: %s" % lines)
            elif self._log_unknown:
                loginf("unparsed: %s" % lines)

    @staticmethod
    def map_to_fields(pkt, obs_map=None):
        if obs_map is None:
            return pkt
        packet = dict()
        keys_a = set(pkt.keys())
        keys_b = set(obs_map.keys())
        keys = keys_a & keys_b
        if keys:
            for k in keys:
                packet[obs_map[k]] = pkt[k]
            for k in ['dateTime', 'usUnits']:
                packet[k] = pkt[k]
        return packet


if __name__ == '__main__':
    import optparse

    usage = """%prog [options] [--debug] [--help]"""

    syslog.openlog('sdr', syslog.LOG_PID | syslog.LOG_CONS)
    syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_INFO))
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('--version', dest='version', action='store_true',
                      help='display driver version')
    parser.add_option('--debug', dest='debug', action='store_true',
                      help='display diagnostic information while running')

    (options, args) = parser.parse_args()

    if options.version:
        print "sdr driver version %s" % DRIVER_VERSION
        exit(1)

    if options.debug:
        syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_DEBUG))

    Packet.KNOWN_PACKETS = [FOWH1080Packet,
                            AcuriteTowerPacket,
                            Acurite5n1Packet,
                            HidekiTS04Packet,
                            OSTHGR810Packet,
                            LaCrossePacket]
    mgr = ProcManager()
    mgr.startup('rtl_433')
    for lines in mgr.process():
        if options.debug:
            print "out:", lines
        packet = Packet.create(lines)
        if packet:
            if options.debug:
                print 'parsed: %s' % packet
            packet = SDRDriver.map_to_fields(packet)
            print 'packet: %s' % packet
        else:
            print "unparsed:", lines
        time.sleep(0.1)
