import weewx

from ..packet import Packet


class SpringfieldTMPacket(Packet):
    IDENTIFIER = 'Springfield Temperature & Moisture'
    EXAMPLES = (
        {
            'time': '2019-01-20 11:14:00',
            'model': 'Springfield Temperature & Moisture',
            'sid': 224,
            'channel': 3,
            'battery': 'OK',
            'transmit': 'MANUAL',
            'temperature_C': -204.800,
            'moisture': 0,
            'mic': 'CHECKSUM',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        sensor_id = obj.get('sid')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['moisture'] = Packet.get_float(obj, 'moisture')
        pkt['battery'] = Packet.get_battery(obj)
        pkt['channel'] = obj.get('channel')
        pkt['transmit'] = obj.get('transmit')
        pkt = Packet.add_identifiers(pkt, sensor_id, SpringfieldTMPacket.__name__)
        return pkt
