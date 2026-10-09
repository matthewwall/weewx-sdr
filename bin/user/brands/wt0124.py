import weewx

from ..packet import Packet


class WT0124Packet(Packet):
    IDENTIFIER = 'WT0124 Pool Thermometer'
    # 2019-04-23: WT0124 Pool Thermometer
    EXAMPLES = (
        {
            'time': '2019-04-23 12:28:52',
            'model': 'WT0124 Pool Thermometer',
            'rid': 122,
            'channel': 1,
            'temperature_C': 22.800,
            'mic': 'CHECKSUM',
            'data': 172,
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        sensor_id = obj.get('rid')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt = Packet.add_identifiers(pkt, sensor_id, WT0124Packet.__name__)
        return pkt
