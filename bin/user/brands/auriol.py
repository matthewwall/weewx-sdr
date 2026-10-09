import weewx

from ..packet import Packet


class AuriolHG02832Packet(Packet):
    IDENTIFIER = 'Auriol-HG02832'

    EXAMPLES = (
        {
            'time': '2017-09-14 20:24:43',
            'model': 'Auriol-HG02832',
            'id': 1,
            'channel': 2,
            'battery': 'OK',
            'temperature_C': 25.090,
            'humidity': 49,
        },
        {
            'time': '2017-09-14 20:24:44',
            'model': 'Auriol-HG02832',
            'id': 1,
            'channel': 2,
            'battery': 'OK',
            'temperature_C': 25.110,
            'humidity': 49,
        },
        {
            'time': '2017-09-14 20:24:44',
            'model': 'Auriol-HG02832',
            'id': 1,
            'channel': 2,
            'battery': 'OK',
            'temperature_C': 25.120,
            'humidity': 49,
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['sid'] = Packet.get_int(obj, 'id')
        pkt['channel'] = Packet.get_int(obj, 'channel')
        pkt['battery'] = Packet.get_battery(obj)
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        _id = '%s:%s' % (pkt['sid'], pkt['channel'])
        pkt = Packet.add_identifiers(pkt, _id, AuriolHG02832Packet.__name__)
        return pkt
