import weewx

from ..packet import Packet


class TSFT002Packet(Packet):
    IDENTIFIER = 'TS-FT002'
    # time : 2019-12-22 16:57:58
    # model : TS-FT002 Id : 127
    # Depth : 186 Temperature: 20.9 C Transmit Interval: 180 Battery Flag?: 8 MIC : CHECKSUM
    EXAMPLES = (
        {
            'time': '2019-12-22 22:54:58',
            'model': 'TS-FT002',
            'id': 127,
            'depth_cm': 186,
            'temperature_C': 20.700,
            'transmit_s': 180,
            'flags': 8,
            'mic': 'CHECKSUM',
        },
    )

    @staticmethod
    def parse_json(obj):
        sensor_id = obj.get('id', '0000')
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['depth'] = Packet.get_float(obj, 'depth_cm')
        pkt['transmit'] = Packet.get_float(obj, 'transmit_s')
        pkt['flags'] = Packet.get_int(obj, 'flags')
        pkt = Packet.add_identifiers(pkt, sensor_id, TSFT002Packet.__name__)
        return pkt
