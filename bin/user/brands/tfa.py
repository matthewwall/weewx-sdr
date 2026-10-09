import re

import weewx

from ..packet import Packet


class TFADropPacket(Packet):
    IDENTIFIER = 'TFA-Drop'
    EXAMPLES = (
        {
            'time': '2022-06-19 09:18:57',
            'model': 'TFA-Drop',
            'id': 549565,
            'battery_ok': 1,
            'rain_mm': 0.000,
            'mic': 'CHECKSUM',
        },
        {
            'time': '2024-08-24 13:51:38',
            'model': 'TFA-Drop',
            'id': 899964,
            'battery_ok': 1,
            'rain_mm': 17.780,
            'mic': 'CHECKSUM',
        },
    )

    @staticmethod
    def parse_json(obj):
        sensor_id = obj.get('id', '0000')
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRICWX
        pkt['rain_total'] = Packet.get_float(obj, 'rain_mm')
        pkt['battery'] = Packet.get_battery(obj)
        pkt = Packet.add_identifiers(pkt, sensor_id, TFADropPacket.__name__)
        return pkt


class TFATwinPlus303049Packet(Packet):
    IDENTIFIER = 'TFA-Twin-Plus-30.3049'

    EXAMPLES = (
        {
            'time': '2019-09-25 17:15:12',
            'model': 'TFA-Twin-Plus-30.3049',
            'id': 13,
            'channel': 1,
            'battery': 'OK',
            'temperature_C': 8.400,
            'humidity': 91,
            'mic': 'CHECK  SUM',
        },
    )
    TEXT_EXAMPLES = (
        (
            '2019-09-25 17:15:12 :   TFA-Twin-Plus-30.3049',
            'Channel: 1',
            'Battery: OK',
            'Temperature: 8.40 C',
            'Humidity: 91 %',
        ),
    )

    PARSEINFO = {
        'Channel': ['channel', None, lambda x: int(x)],
        'Battery': ['battery', None, lambda x: 0 if x == 'OK' else 1],
        'Temperature': ['temperature', re.compile(r'([\d.-]+) C'), lambda x: float(x)],
        'Humidity': ['humidity', re.compile(r'([\d.]+) %'), lambda x: float(x)],
    }

    @staticmethod
    def parse_text(ts, payload, lines):
        sensor_id = '0000'  # FIXME - no id in text output?
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, TFATwinPlus303049Packet.PARSEINFO))
        return Packet.add_identifiers(pkt, sensor_id, TFATwinPlus303049Packet.__name__)

    @staticmethod
    def parse_json(obj):
        sensor_id = obj.get('id', '0000')
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['channel'] = obj.get('channel')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['battery'] = Packet.get_battery(obj)
        return Packet.add_identifiers(pkt, sensor_id, TFATwinPlus303049Packet.__name__)
