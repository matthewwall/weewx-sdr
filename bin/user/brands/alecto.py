import weewx

from ..packet import Packet


class AlectoV1TemperaturePacket(Packet):
    IDENTIFIER = 'AlectoV1-Temperature'

    EXAMPLES = (
        {
            'time': '2024-12-28 09:06:10',
            'model': 'AlectoV1-Temperature',
            'id': 33,
            'channel': 1,
            'battery_ok': 1,
            'temperature_C': -2.200,
            'humidity': 51,
            'mic': 'CHECKSUM',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRICWX
        station_id = obj.get('id')
        pkt['channel'] = obj.get('channel')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['battery'] = Packet.get_battery(obj)
        pkt = Packet.add_identifiers(pkt, station_id, AlectoV1TemperaturePacket.__name__)
        return pkt


class AlectoV1WindPacket(Packet):
    IDENTIFIER = 'AlectoV1-Wind'

    EXAMPLES = (
        {
            'time': '2024-12-28 09:06:41',
            'model': 'AlectoV1-Wind',
            'id': 33,
            'channel': 1,
            'battery_ok': 1,
            'wind_avg_m_s': 0.800,
            'wind_max_m_s': 1.000,
            'wind_dir_deg': 180,
            'mic': 'CHECKSUM',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRICWX
        station_id = obj.get('id')
        pkt['channel'] = obj.get('channel')
        pkt['wind_speed'] = Packet.get_float(obj, 'wind_avg_m_s')
        pkt['wind_gust'] = Packet.get_float(obj, 'wind_max_m_s')
        pkt['wind_dir'] = Packet.get_int(obj, 'wind_dir_deg')
        pkt['battery'] = Packet.get_battery(obj)
        pkt = Packet.add_identifiers(pkt, station_id, AlectoV1WindPacket.__name__)
        return pkt


class AlectoV1RainPacket(Packet):
    IDENTIFIER = 'AlectoV1-Rain'

    EXAMPLES = (
        {
            'time': '2024-12-28 09:06:31',
            'model': 'AlectoV1-Rain',
            'id': 202,
            'channel': 0,
            'battery_ok': 1,
            'rain_mm': 54.750,
            'mic': 'CHECKSUM',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRICWX
        station_id = obj.get('id')
        pkt['channel'] = obj.get('channel')
        pkt['rain_total'] = Packet.get_float(obj, 'rain_mm')
        pkt['battery'] = Packet.get_battery(obj)
        pkt = Packet.add_identifiers(pkt, station_id, AlectoV1RainPacket.__name__)
        return pkt
