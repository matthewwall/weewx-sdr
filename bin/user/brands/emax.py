import weewx

from ..packet import Packet
from ..units import to_C


class EM3551HPacket(Packet):
    IDENTIFIER = 'Emax-EM3551H'
    # The EMAX-EM3551H sensor cluster, used in the raddy weather station
    EXAMPLES = (
        {
            'time': '2024-10-25 17:51:33',
            'model': 'Emax-EM3551H',
            'id': 1001,
            'channel': 4,
            'battery_ok': 1,
            'temperature_F': 55.700,
            'humidity': 95,
            'wind_avg_km_h': 0.000,
            'wind_max_km_h': 0.000,
            'wind_dir_deg': 169,
            'rain_mm': 0.000,
            'mic': 'CHECKSUM',
        },
    )

    @staticmethod
    def parse_json(obj):
        sensor_id = obj.get('id')  # changes when the outdoor sensor is reset
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['battery'] = Packet.get_battery(obj)
        pkt['temperature'] = to_C(Packet.get_float(obj, 'temperature_F'))
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['wind_gust'] = Packet.get_float(obj, 'wind_max_km_h')
        pkt['wind_speed'] = Packet.get_float(obj, 'wind_avg_km_h')
        pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
        pkt['rain_total'] = Packet.get_float(obj, 'rain_mm')
        pkt = Packet.add_identifiers(pkt, sensor_id, EM3551HPacket.__name__)
        return pkt
