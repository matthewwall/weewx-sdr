import weewx

from ..packet import Packet


class WS2032Packet(Packet):
    IDENTIFIER = 'WS2032'

    EXAMPLES = (
        {
            'time': '2020-10-19 22:41:24',
            'model': 'WS2032',
            'id': 11768,
            'temperature_C': 3.800,
            'humidity': 48,
            'wind_dir_deg': 315.000,
            'wind_avg_km_h': 7.740,
            'wind_max_km_h': 15.480,
            'maybe_flags': 0,
            'maybe_rain': 256,
            'mic': 'CRC',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        sensor_id = obj.get('id')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['wind_gust'] = Packet.get_float(obj, 'wind_max_km_h')
        pkt['wind_speed'] = Packet.get_float(obj, 'wind_avg_km_h')
        pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
        pkt['rain_total'] = Packet.get_float(obj, 'maybe_rain')
        pkt = Packet.add_identifiers(pkt, sensor_id, WS2032Packet.__name__)
        return pkt
