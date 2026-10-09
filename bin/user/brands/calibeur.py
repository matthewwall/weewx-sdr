import re

import weewx

from ..packet import Packet


class CalibeurRF104Packet(Packet):
    IDENTIFIER = 'Calibeur RF-104'
    TEXT_EXAMPLES = (
        (
            '2016-11-01 01:25:28 :Calibeur RF-104',
            'ID: 1',
            'Temperature: 1.8 C',
            'Humidity: 71 %',
        ),
        (
            '2016-11-04 05:16:39 :Calibeur RF-104',
            'ID: 1',
            'Temperature: -2.2 C',
            'Humidity: 71 %',
        ),
    )
    PARSEINFO = {
        'ID': ['id', None, lambda x: int(x)],
        'Temperature': ['temperature', re.compile(r'([\d.-]+) C'), lambda x: float(x)],
        'Humidity': ['humidity', re.compile(r'([\d.]+) %'), lambda x: float(x)],
    }

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, CalibeurRF104Packet.PARSEINFO))
        pkt_id = pkt.pop('id', 0)
        sensor_id = '%s' % pkt_id
        pkt = Packet.add_identifiers(pkt, sensor_id, CalibeurRF104Packet.__name__)
        return pkt
