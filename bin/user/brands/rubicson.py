import re

import weewx

from ..packet import Packet


class RubicsonTempPacket(Packet):
    IDENTIFIER = 'Rubicson Temperature Sensor'
    PARSEINFO = {
        'House Code': ['house_code', None, lambda x: int(x)],
        'Channel': ['channel', None, lambda x: int(x)],
        'Battery': ['battery', None, lambda x: 0 if x == 'OK' else 1],
        'Temperature': ['temperature', re.compile(r'([\d.-]+) C'), lambda x: float(x)],
    }

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, RubicsonTempPacket.PARSEINFO))
        channel = pkt.pop('channel', 0)
        code = pkt.pop('house_code', 0)
        sensor_id = '%s:%s' % (channel, code)
        return Packet.add_identifiers(pkt, sensor_id, RubicsonTempPacket.__name__)

    EXAMPLES = (
        {
            'time': '2017-01-17 20:47:41',
            'model': 'Rubicson Temperature Sensor',
            'id': 14,
            'channel': 1,
            'battery': 'OK',
            'temperature_C': -1.800,
            'crc': 'OK',
        },
    )
    TEXT_EXAMPLES = (
        (
            '2017-01-15 14:49:03 : Rubicson Temperature Sensor',
            'House Code: 14',
            'Channel: 1',
            'Battery: OK',
            'Temperature: 4.5 C',
            'CRC: OK',
        ),
    )

    @staticmethod
    def parse_json(obj):
        channel = obj.get('channel', 0)
        code = obj.get('id', 0)
        sensor_id = '%s:%s' % (channel, code)
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['battery'] = Packet.get_battery(obj)
        return Packet.add_identifiers(pkt, sensor_id, RubicsonTempPacket.__name__)


class RubicsonTempPacketV2(Packet):
    IDENTIFIER = 'Rubicson-Temperature'

    EXAMPLES = (
        {
            'time': '2023-04-04 19:57:28',
            'protocol': 2,
            'model': 'Rubicson-Temperature',
            'id': 183,
            'channel': 3,
            'battery_ok': 1,
            'temperature_C': 21.700,
            'mic': 'CRC',
        },
    )

    @staticmethod
    def parse_json(obj):
        channel = obj.get('channel', 0)
        code = obj.get('id', 0)
        sensor_id = '%s:%s' % (channel, code)
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['battery'] = Packet.get_battery(obj)
        return Packet.add_identifiers(pkt, sensor_id, RubicsonTempPacketV2.__name__)
