import weewx

from ..packet import Packet


class InFactoryTHPacket(Packet):
    IDENTIFIER = 'nFactory-TH'

    EXAMPLES = (
        {
            'time': '2021-03-03 10:19:53',
            'model': 'inFactory-TH',
            'id': 195,
            'channel': 1,
            'battery_ok': 1,
            'temperature_F': 73.200,
            'humidity': 55,
            'mic': 'CRC',
        },
    )

    @staticmethod
    def parse_json(obj):
        sensor_id = obj.get('id')
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.US
        pkt['temperature'] = Packet.get_float(obj, 'temperature_F')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['battery'] = Packet.get_battery(obj)
        pkt['channel'] = obj.get('channel')
        pkt = Packet.add_identifiers(pkt, sensor_id, InFactoryTHPacket.__name__)
        return pkt
