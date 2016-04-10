#!/usr/bin/env python
# Copyright 2016 Matthew Wall, all rights reserved
"""
Collect data from stl-sdr.  Run rtl_433 on a thread and push the output onto
a queue.
"""

from __future__ import with_statement
import Queue
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

    def parse(self, data):
        packet = dict()
        return packet

    def map_to_fields(self, pkt, obs_map):
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
        if out:
            for line in out:
                print line.strip()
        if err:
            for line in err:
                print "error: ", line.strip()
        time.sleep(0.1)
