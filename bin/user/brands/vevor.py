import weewx

from ..packet import Packet
from ..units import kmh_to_mps


class Vevor7in1Packet(Packet):
    IDENTIFIER = 'Vevor-7in1'
    # Vevor 7-in-1 weather station, thanks to ivan
    # https://sh.com.hr/weather-station/your-vevor-7-in-1-wi-fi-weather-station-yt60234-in-weewx/
    EXAMPLES = (
        {
            'time': '2024-11-13 13:27:59',
            'model': 'Vevor-7in1',
            'id': 52266,
            'channel': 0,
            'battery_ok': 1,
            'temperature_C': 5.400,
            'humidity': 76,
            'wind_avg_km_h': 0.700,
            'wind_max_km_h': 2.667,
            'wind_dir_deg': 87,
            'rain_mm': 12.116,
            'uv': 0,
            'light_lux': 7213,
            'mic': 'CHECKSUM',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRICWX
        station_id = Packet.get_int(obj, 'id')
        pkt['battery'] = Packet.get_battery(obj)
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['wind_gust'] = kmh_to_mps(Packet.get_float(obj, 'wind_max_km_h'))
        pkt['wind_speed'] = kmh_to_mps(Packet.get_float(obj, 'wind_avg_km_h'))
        pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
        pkt['rain_total'] = Packet.get_float(obj, 'rain_mm')
        pkt['light_lux'] = Packet.get_int(obj, 'light_lux')
        pkt['uv'] = Packet.get_float(obj, 'uv')
        pkt = Packet.add_identifiers(pkt, station_id, Vevor7in1Packet.__name__)
        return pkt
