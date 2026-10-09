import re
import time
from calendar import timegm

from .log import logdbg, logerr

try:
    import cjson as json

    setattr(json, 'dumps', json.encode)
    setattr(json, 'loads', json.decode)
except (ImportError, AttributeError):
    try:
        import simplejson as json
    except ImportError:
        import json


class Packet:
    def __init__(self):
        pass

    @staticmethod
    def parse_text(ts, payload, lines):
        return None

    @staticmethod
    def parse_json(obj):
        return None

    TS_PATTERN = re.compile(r'(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d)')

    @staticmethod
    def parse_time(line):
        ts = None
        try:
            m = Packet.TS_PATTERN.search(line)
            if m:
                utc = time.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')
                ts = timegm(utc)
        except Exception as e:
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
    def get_battery(obj):
        # deal with boolean battery status indicators.  older rtl_433 used a
        # field called 'battery' with string 'OK'.  later rtl_433 uses a field
        # called 'battery_ok' with value 1 to indicate battery is ok and 0 to
        # indicate battery is not ok.  at one point rtl_433 was emitting a
        # field called 'battery_low', so check for that too.
        #
        # for some sensors we see 'battery_ok' with a floating value.  not sure
        # what this means.
        #
        # map these to the WeeWX convention of boolean battery indicators of
        # 0=OK 1=notOK
        bs = None
        if 'battery_ok' in obj:
            level = Packet.get_float(obj, 'battery_ok')
            if level is not None:
                bs = 0 if level >= 1.0 else 1
        elif 'battery' in obj:
            bs = 0 if obj.get('battery') == 'OK' else 1
        elif 'battery_low' in obj:
            bs = Packet.get_int(obj, 'battery_low')
        return bs

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
                                logdbg("regex failed for %s:'%s'" % (name, value))
                        if parseinfo[name][2]:
                            value = parseinfo[name][2](value)
                        if parseinfo[name][0]:
                            name = parseinfo[name][0]
                        packet[name] = value
                    else:
                        logdbg('ignoring %s:%s' % (name, value))
                except Exception as e:
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
            packet['%s.%s.%s' % (n, sensor_id, packet_type)] = pkt[n]
        return packet


class PacketFactory(object):
    # known packets will be lazy-loaded by introspecting at first request
    KNOWN_PACKETS = []

    @staticmethod
    def known_packets():
        if not PacketFactory.KNOWN_PACKETS:
            import inspect

            from . import brands

            objs = inspect.getmembers(brands, inspect.isclass)
            for name, obj in objs:
                if hasattr(obj, 'IDENTIFIER'):
                    PacketFactory.KNOWN_PACKETS.append(obj)
        return PacketFactory.KNOWN_PACKETS

    @staticmethod
    def create(lines):
        # return a list of packets from the specified lines
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
                for parser in PacketFactory.known_packets():
                    if obj['model'].find(parser.IDENTIFIER) >= 0:
                        return parser.parse_json(obj)
                logdbg('parse_json: unknown model %s' % obj['model'])
        except ValueError as e:
            logdbg('parse_json failed: %s' % e)
        return None

    @staticmethod
    def parse_text(lines):
        ts, payload = PacketFactory.parse_firstline(lines[0])
        if ts and payload:
            logdbg('parse_text: ts=%s payload=%s' % (ts, payload))
            for parser in PacketFactory.known_packets():
                if payload.find(parser.IDENTIFIER) >= 0:
                    pkt = parser.parse_text(ts, payload, lines)
                    logdbg('pkt=%s' % pkt)
                    return pkt
            logdbg('parse_text: unknown format: ts=%s payload=%s' % (ts, payload))
        logdbg('parse_text failed: ts=%s payload=%s line=%s' % (ts, payload, lines[0]))
        lines.pop(0)
        return None

    TS_PATTERN = re.compile(r'(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d)[\s]+:*(.*)')

    @staticmethod
    def parse_firstline(line):
        ts = payload = None
        try:
            m = PacketFactory.TS_PATTERN.search(line)
            if m:
                utc = time.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')
                ts = timegm(utc)
                payload = m.group(2).strip()
        except Exception as e:
            logerr("parse timestamp failed for '%s': %s" % (line, e))
        return ts, payload
