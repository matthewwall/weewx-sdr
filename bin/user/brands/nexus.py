import re

import weewx

from ..packet import Packet
from .oregon_scientific import OS


class NexusTemperaturePacket(Packet):
    IDENTIFIER = 'Nexus Temperature'
    TEXT_EXAMPLES = (
        (
            '2018-06-30 01:12:12 :   Nexus Temperature',
            '        House Code:      55',
            '        Battery:         OK',
            '        Channel:         1',
            '        Temperature:     27.10 C',
        ),
        (
            '2018-08-01 22:03:11 :   Nexus Temperature/Humidity',
            '   House Code:      180',
            '   Battery:         OK',
            '   Channel:         1',
            '   Temperature:     20.10 C',
            '   Humidity:        42 %',
        ),
    )
    PARSEINFO = {
        'House Code': ['house_code', None, lambda x: int(x)],
        'Battery': ['battery', None, lambda x: 0 if x == 'OK' else 1],
        'Channel': ['channel', None, lambda x: int(x)],
        'Temperature': ['temperature', re.compile(r'([\d.-]+) C'), lambda x: float(x)],
        'Humidity': ['humidity', re.compile(r'([\d.-]+) %'), lambda x: float(x)],
    }

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, NexusTemperaturePacket.PARSEINFO))
        return OS.insert_ids(pkt, NexusTemperaturePacket.__name__)

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['house_code'] = obj.get('id')
        pkt['battery'] = Packet.get_battery(obj)
        pkt['channel'] = obj.get('channel')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        if 'humidity' in obj:
            pkt['humidity'] = Packet.get_float(obj, 'humidity')
        return OS.insert_ids(pkt, NexusTemperaturePacket.__name__)
