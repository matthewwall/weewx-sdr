#!/usr/bin/env python
# Copyright 2016 Matthew Wall, all rights reserved
"""
Collect data from stl-sdr.  Run rtl_433 on a thread and push the output onto
a queue.
"""

from __future__ import with_statement
from calendar import timegm
import Queue
import re
import subprocess
import syslog
import threading
import time

import weewx.drivers

DRIVER_NAME = 'SDR'
DRIVER_VERSION = '0.1'

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

    def __init__(self):
        self._process = None
        self.stdout_queue = Queue.Queue()
        self.stdout_reader = None
        self.stderr_queue = Queue.Queue()
        self.stderr_reader = None

    def startup(self, cmd):
        loginf("startup process '%s'" % cmd)
        self._process = subprocess.Popen(cmd,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        self.stdout_reader = AsyncReader(
            self._process.stdout, self.stdout_queue, 'stdout-thread')
        self.stdout_reader.start()
        self.stderr_reader = AsyncReader(
            self._process.stderr, self.stderr_queue, 'stderr-thread')
        self.stderr_reader.start()

    def process(self):
        out = err = []
        while not self.stdout_reader.eof() or not self.stderr_reader.eof():
            while not self.stdout_queue.empty():
                out.append(self.stdout_queue.get())
            while not self.stderr_queue.empty():
                err.append(self.stderr_queue.get())
            yield out, err
            out = err = []

    def shutdown(self):
        loginf('shutdown process')
        self.stdout_reader.join(10.0)
        self.stderr_reader.join(10.0)
        self._process.stdout.close()
        self._process.stderr.close()
        self._process = None


class Parser:
    TS_PATTERN = re.compile('(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d) :*(.*)')

    @staticmethod
    def get_timestamp(lines):
        ts = key = None
        if lines and len(lines) > 0:
            try:
                m = Parser.TS_PATTERN.search(lines[0])
                if m:
                    utc = time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                    ts = timegm(utc)
                    key = m.group(2).strip()
            except Exception, e:
                logerr("parse time failed for '%s': %s" % (lines[0], e))
        return ts, key

    @staticmethod
    def parse_lines(lines, labels=None):
        packet = dict()
        for line in lines:
            try:
                (name, value) = [x.strip() for x in line.split(':')]
                if name in labels:
                    packet[labels[name]] = value
            except Exception, e:
                logerr("parse failed for line '%s': %s" % (line, e))
        return packet


class FineOffsetWH1080(Parser):
    IDENTIFIER = "Fine Offset WH1080 weather station"
    LABELS = {'Msg type': 'msg_type',
              'StationID': 'station_id',
              'Temperature': 'temperature',
              'Humidity': 'humidity',
              'Wind string': 'wind_dir_ord',
              'Wind degrees': 'wind_dir',
              'Wind avg speed': 'wind_speed',
              'Wind gust': 'wind_gust',
              'Total rainfall': 'total_rain',
              'Battery': 'battery'}
    @staticmethod
    def parse(lines):
        return Parser.parse_lines(lines[1:], FineOffsetWH1080.LABELS)


class AcuriteTower:
    # 2016-08-30 23:57:20 Acurite tower sensor 0x37FC Ch A: 26.7 C 80.1 F 16 % RH

    IDENTIFIER = "Acurite tower sensor"
    PATTERN = re.compile('0x([0-9a-fA-F]+) Ch ([A-C]): ([\d.]+) C ([\d.]+) F ([\d]+) % RH')
    @staticmethod
    def parse(lines):
        packet = dict()
        m = AcuriteTower.PATTERN.search(lines[0])
        if m:
            packet['sensor_id'] = m.group(1)
            packet['channel'] = m.group(2)
            packet['temperature'] = m.group(3)
            packet['temperature_F'] = m.group(4)
            packet['humidity'] = m.group(5)
        else:
            logdbg("unrecognized data: '%s'" % lines[0])
        return packet


class Acurite5n1:
    # 2016-08-31 16:41:39 Acurite 5n1 sensor 0x0BFA Ch C, Msg 31, Wind 15 kmph / 9.3 mph 270.0^ W (3), rain gauge 0.00 in
    # 2016-08-30 23:57:25 Acurite 5n1 sensor 0x0BFA Ch C, Msg 38, Wind 2 kmph / 1.2 mph, 21.3 C 70.3 F 70 % RH

    IDENTIFIER = "Acurite 5n1 sensor"
    PATTERN = re.compile('0x([0-9a-fA-F]+) Ch ([A-C]), (.*)')
    RAIN = re.compile('Total rain fall since last reset: ([\d.]+)')
    MSG = re.compile('Msg (\d+), (.*)')
    MSG31 = re.compile('Wind ([\d.]+) kmph / ([\d.]+) mph ([\d.]+)')
    MSG38 = re.compile('Wind ([\d.]+) kmph / ([\d.]+) mph, ([\d.]+) C ([\d.]+) F ([\d.]+) % RH')

    @staticmethod
    def parse(lines):
        packet = dict()
        m = Acurite5n1.PATTERN.search(lines[0])
        if m:
            packet['sensor_id'] = m.group(1)
            packet['channel'] = m.group(2)
            payload = m.group(3)
            m = Acurite5n1.MSG.search(payload)
            if m:
                packet['msg_type'] = m.group(1)
                payload = m.group(2)
                if packet['msg_type'] == '31':
                    m = Acurite5n1.MSG31.search(payload)
                    if m:
                        packet['wind_speed'] = m.group(1)
                        packet['wind_speed_mph'] = m.group(2)
                        packet['wind_dir'] = m.group(3)
                elif packet['msg_type'] == '38':
                    m = Acurite5n1.MSG38.search(payload)
                    if m:
                        packet['wind_speed'] = m.group(1)
                        packet['wind_speed_mph'] = m.group(2)
                        packet['temperature'] = m.group(3)
                        packet['temperature_F'] = m.group(4)
                        packet['humidity'] = m.group(5)
                else:
                    logerr("unknown message type %s in line '%s'" %
                           (packet['msg_type'], lines[0]))
            else:
                m = Acurite5n1.RAIN.search(payload)
                if m:
                    packet['rain_total'] = m.group(1)
                else:
                    logerr("unknown message format: '%s'" % lines[0])
        else:
            logdbg("unrecognized data: '%s'" % lines[0])
        return packet


class HidekiTS04:
    IDENTIFIER = "HIDEKI TS04 sensor"
    LABELS = {'Rolling Code': 'rolling_code',
              'Channel': 'channel',
              'Battery': 'battery',
              'Temperature': 'temperature',
              'Humidity': 'humidity'}
    @staticmethod
    def parse(lines):
        return Parser.parse_lines(lines[1:], HidekiTS04.LABELS)


class OSTHGR810:
    IDENTIFIER = "Weather Sensor THGR810"
    LABELS = {'House Code': 'house_code',
              'Channel': 'channel',
              'Battery': 'battery',
              'Celcius': 'temperature',
              'Fahrenheit': 'temperature_F',
              'Humidity': 'humidity'}
    @staticmethod
    def parse(lines):
        return Parser.parse_lines(lines[1:], OSTHGR810.LABELS)


class SDRConfigurationEditor(weewx.drivers.AbstractConfEditor):
    @property
    def default_stanza(self):
        return """
[SDR]
    # This section is for the software-defined radio driver.

    # The driver to use
    driver = user.sdr
"""


class SDRDriver(weewx.drivers.AbstractDevice):

    PARSERS = [FineOffsetWH1080,
               AcuriteTower,
               Acurite5n1,
               HidekiTS04,
               OSTHGR810]

    def __init__(self, **stn_dict):
        loginf('driver version is %s' % DRIVER_VERSION)
        self._obs_map = stn_dict.get('sensor_map', None)
        self._cmd = stn_dict.get('cmd', 'rtl_433')
        self._mgr = ProcManager()
        self._mgr.startup(self._cmd)

    def closePort(self):
        self._mgr.shutdown()

    def hardware_name(self):
        return 'SDR'

    def genLoopPackets(self):
        for out, err in self._mgr.process():
            logdbg('raw out: %s' % out)
            logdbg('raw err: %s' % err)
            packet = self.parse(out)
            logdbg('raw packet: %s' % packet)
            packet = self.map_to_fields(packet, self._obs_map)
            logdbg('mapped packet: %s' % packet)
            yield packet

    @staticmethod
    def parse(data):
        ts, key = Parser.get_timestamp(data)
        if key:
            for parser in SDRDriver.PARSERS:
                if key.startswith(parser.IDENTIFIER):
                    data = parser.parse(data)
                    if data:
                        data['dateTime'] = ts
                        data['sensor_type'] = parser.IDENTIFIER
                        return data
        return dict()

    @staticmethod
    def map_to_fields(pkt, obs_map=None):
        if obs_map is None:
            return pkt
        packet = dict()
        for k in obs_map:
            if k in pkt:
                packet[obs_map[k]] = pkt[k]
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

    mgr = ProcManager()
    mgr.startup('rtl_433')
    for out, err in mgr.process():
        raw_packet = SDRDriver.parse(out)
        if raw_packet:
            if options.debug:
                print 'raw packet: %s' % raw_packet
            map_packet = SDRDriver.map_to_fields(raw_packet)
            if map_packet:
                print 'mapped packet: %s' % map_packet
            elif out:
                for line in out:
                    print line.strip()
#        if err:
#            for line in err:
#                print "error: ", line.strip()
#        time.sleep(0.1)
