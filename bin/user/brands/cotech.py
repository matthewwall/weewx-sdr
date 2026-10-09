import weewx

from ..packet import Packet
from ..units import to_C


class Cotech367959Packet(Packet):
    IDENTIFIER = 'Cotech-367959'
    # Cotech 36-7959 weather station
    # Also: SwitchDoc Labs Weather FT020T.
    # Also: Sainlogic Weather Station WS019T
    # Also: Sainlogic Weather Station FT0300
    # Also: Sainlogic Weather Station WS0310 (all current Sainlogic models ?)
    # Also: Ragova WiFi Weather Station FT-0310
    # Also: NicetyMeter Weather Station 0366 (without Lux or UV index)
    #
    # thanks to user gremlin205
    EXAMPLES = (
        {
            'time': '2022-03-01 14:11:42',
            'model': 'Cotech-367959',
            'id': 24,
            'battery_ok': 1,
            'temperature_F': 46.900,
            'humidity': 62,
            'rain_mm': 18.600,
            'wind_dir_deg': 16,
            'wind_avg_m_s': 0.600,
            'wind_max_m_s': 0.700,
            'mic': 'CRC',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRICWX
        sensor_id = obj.get('id')
        pkt['battery'] = Packet.get_battery(obj)
        if 'temperature_F' in obj:
            pkt['temperature'] = to_C(Packet.get_float(obj, 'temperature_F'))
        elif 'temperature_C' in obj:
            pkt['temperature'] = Packet.get_float(obj, 'temperature_F')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['wind_gust'] = Packet.get_float(obj, 'wind_max_m_s')
        pkt['wind_speed'] = Packet.get_float(obj, 'wind_avg_m_s')
        pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
        pkt['rain_total'] = Packet.get_float(obj, 'rain_mm')
        pkt['uv_index'] = Packet.get_float(obj, 'uv')
        pkt['luminosity'] = Packet.get_float(obj, 'light_lux')
        pkt = Packet.add_identifiers(pkt, sensor_id, Cotech367959Packet.__name__)
        return pkt
