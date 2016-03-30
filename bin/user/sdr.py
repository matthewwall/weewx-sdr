#!/usr/bin/env python
# Copyright 2016 Matthew Wall, all rights reserved
"""
Collect data from stl-sdr.  Run rtl_433 on a thread and push the output onto
a queue.
"""

from __future__ import with_statement
import Queue
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


class SDRDriver(weewx.drivers.AbstractDevice):

    def __init__(self, **stn_dict):
        loginf('driver version is %s' % DRIVER_VERSION)
        self._obs_map = stn_dict.get('map', None)
        self._queue = Queue.Queue()
        self._capture_thread = threading.Thread(target=self.capture)
        self._capture_thread.setDaemon(True)
        self._capture_thread.setName('capture-thread')
        self._capture_thread.start()

    def closePort(self):
        loginf('shutting down server thread')
        self._capture_thread.join(20.0)
        if self._capture_thread.isAlive():
            logerr('unable to shut down capture thread')

    def hardware_name(self):
        return 'SDR'

    def genLoopPackets(self):
        while True:
            try:
                data = self._queue.get(True, 10)
                logdbg('raw data: %s' % data)
                packet = self.parse(data)
                logdbg('raw packet: %s' % packet)
                packet = self.map_to_fields(packet, self._obs_map)
                logdbg('mapped packet: %s' % packet)
                yield packet
            except Queue.Empty:
                logdbg('empty queue')

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


class SDRConfigurationEditor(weewx.drivers.AbstractConfEditor):
    @property
    def default_stanza(self):
        return """
[SDR]
    # This section is for the software-defined radio driver.

    # The driver to use:
    driver = user.sdr
"""
