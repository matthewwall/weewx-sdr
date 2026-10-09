import weewx

from ..packet import Packet


class KedsumTHPacket(Packet):
    IDENTIFIER = 'Kedsum-TH'

    EXAMPLES = (
        {
            'time': '2022-06-17 00:23:59',
            'model': 'Kedsum-TH',
            'id': 235,
            'channel': 1,
            'battery_ok': 0,
            'flags': 8,
            'temperature_F': 59.000,
            'humidity': 74,
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
        pkt['flags'] = obj.get('flags')
        pkt = Packet.add_identifiers(pkt, sensor_id, KedsumTHPacket.__name__)
        return pkt
