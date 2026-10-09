import weewx

from ..packet import Packet


class HolmanWS5029Packet(Packet):
    IDENTIFIER = 'Holman Industries WS5029 weather station'

    EXAMPLES = (
        {
            'time': '2019-08-07 10:35:07',
            'model': 'Holman Industries WS5029 weather station',
            'id': 53761,
            'temperature_C': 9.100,
            'humidity': 102,
            'rain_mm': 39.500,
            'wind_avg_km_h': 0,
            'direction_deg': 338,
        },
    )

    @staticmethod
    def parse_json(obj):
        sensor_id = obj.get('id')
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRICWX
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['wind_dir'] = Packet.get_float(obj, 'direction_deg')
        pkt['wind_speed'] = Packet.get_float(obj, 'wind_avg_km_h')
        pkt['rain_total'] = Packet.get_float(obj, 'rain_mm')
        pkt = Packet.add_identifiers(pkt, sensor_id, HolmanWS5029Packet.__name__)
        return pkt
