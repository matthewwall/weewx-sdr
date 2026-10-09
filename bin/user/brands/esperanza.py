import weewx

from ..packet import Packet


class EsperanzaEWSPacket(Packet):
    IDENTIFIER = 'Esperanza-EWS'
    # This is for a Esperanza-EWS temperature humidity sensor
    EXAMPLES = (
        {
            'time': '2022-06-30 08:29:25',
            'model': 'Esperanza-EWS',
            'id': 198,
            'channel': 2,
            'temperature_F': 69.200,
            'humidity': 0,
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
        pkt['channel'] = obj.get('channel')
        pkt = Packet.add_identifiers(pkt, sensor_id, EsperanzaEWSPacket.__name__)
        return pkt
