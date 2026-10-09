import weewx

from ..packet import Packet


class Bresser5in1Packet(Packet):
    IDENTIFIER = 'Bresser-5in1'

    EXAMPLES = (
        {
            'time': '2018-12-15 16:04:04',
            'model': 'Bresser-5in1',
            'id': 118,
            'temperature_C': 6.400,
            'humidity': 87,
            'wind_gust': 2.800,
            'wind_speed': 2.900,
            'wind_dir_deg': 315.000,
            'rain_mm': 10.800,
            'data': 'e7897fd71fd6ef9bff78f7feff18768028e02910640087080100',
            'mic': 'CHECKSUM',
        },
        {
            'time': '2020-04-20 20:58:46',
            'model': 'Bresser-5in1',
            'id': 182,
            'battery_ok': 1,
            'temperature_C': 17.000,
            'humidity': 92,
            'wind_max_m_s': 4.000,
            'wind_avg_m_s': 2.400,
            'wind_dir_deg': 67.500,
            'rain_mm': 0.800,
            'mic': 'CHECKSUM',
        },
    )

    @staticmethod
    def parse_json(obj):
        station_id = obj.get('id')
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRICWX
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
        pkt['uv'] = Packet.get_float(obj, 'uv')
        pkt['uv_index'] = Packet.get_float(obj, 'uvi')
        pkt['battery'] = Packet.get_battery(obj)
        # deal with different labels from rtl_433
        for dst, src in [
            ('wind_speed', 'wind_speed_ms'),
            ('wind_speed', 'wind_speed'),
            ('wind_speed', 'wind_avg_m_s'),
            ('gust_speed', 'gust_speed_ms'),
            ('gust_speed', 'gust_speed'),
            ('rain_total', 'rainfall_mm'),
            ('rain_total', 'rain_mm'),
            ('wind_gust', 'gust_speed_ms'),
            ('wind_gust', 'wind_gust'),
            ('wind_gust', 'gust_speed'),
            ('wind_gust', 'wind_max_m_s'),
        ]:
            if src in obj:
                pkt[dst] = Packet.get_float(obj, src)
        pkt = Packet.add_identifiers(pkt, station_id, Bresser5in1Packet.__name__)
        return pkt


class Bresser6in1Packet(Packet):
    IDENTIFIER = 'Bresser-6in1'
    EXAMPLES = (
        {
            'time': '2018-12-15 16:04:04',
            'model': 'Bresser-6in1',
            'id': 118,
            'temperature_C': 6.400,
            'humidity': 87,
            'wind_gust': 2.800,
            'wind_speed': 2.900,
            'wind_dir_deg': 315.000,
            'rain_mm': 10.800,
            'data': 'e7897fd71fd6ef9bff78f7feff18768028e02910640087080100',
            'mic': 'CHECKSUM',
        },
    )

    @staticmethod
    def parse_json(obj):
        station_id = obj.get('id')
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRICWX
        pkt['battery'] = Packet.get_battery(obj)
        if 'temperature_C' in obj:
            pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        if 'humidity' in obj:
            pkt['humidity'] = Packet.get_float(obj, 'humidity')
        if 'wind_dir_deg' in obj:
            pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
        if 'wind_max_m_s' in obj:
            pkt['wind_gust'] = Packet.get_float(obj, 'wind_max_m_s')
        if 'wind_avg_m_s' in obj:
            pkt['wind_speed'] = Packet.get_float(obj, 'wind_avg_m_s')
        if 'uv' in obj:
            pkt['uv'] = Packet.get_float(obj, 'uv')
        if 'uv_index' in obj:
            pkt['uv_index'] = Packet.get_float(obj, 'uvi')
        # deal with different labels from rtl_433
        for dst, src in [
            ('wind_speed', 'wind_speed_ms'),
            ('gust_speed', 'gust_speed_ms'),
            ('rain_total', 'rainfall_mm'),
            ('wind_speed', 'wind_speed'),
            ('gust_speed', 'gust_speed'),
            ('rain_total', 'rain_mm'),
        ]:
            if src in obj:
                pkt[dst] = Packet.get_float(obj, src)
        pkt = Packet.add_identifiers(pkt, station_id, Bresser6in1Packet.__name__)
        return pkt


class Bresser7in1Packet(Packet):
    IDENTIFIER = 'Bresser-7in1'

    EXAMPLES = (
        {
            'time': '2023-06-11 17:09:05',
            'model': 'Bresser-7in1',
            'id': 50437,
            'temperature_C': 23.500,
            'humidity': 67,
            'wind_max_m_s': 0.000,
            'wind_avg_m_s': 0.000,
            'wind_dir_deg': 102,
            'rain_mm': 3.500,
            'light_klx': 8.592,
            'light_lux': 8592.000,
            'uv': 1.000,
            'battery_ok': 1,
            'mic ': 'CRC',
        },
    )

    @staticmethod
    def parse_json(obj):
        station_id = obj.get('id')
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRICWX
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['wind_gust'] = Packet.get_float(obj, 'wind_max_m_s')
        pkt['wind_speed'] = Packet.get_float(obj, 'wind_avg_m_s')
        pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
        pkt['rain_total'] = Packet.get_float(obj, 'rain_mm')
        pkt['lux'] = Packet.get_int(obj, 'light_lux')
        pkt['uv'] = Packet.get_float(obj, 'uv')
        pkt['battery'] = Packet.get_battery(obj)
        pkt = Packet.add_identifiers(pkt, station_id, Bresser7in1Packet.__name__)
        return pkt


class BresserProRainGaugePacket(Packet):
    IDENTIFIER = 'Bresser-ProRainGauge'
    EXAMPLES = (
        {
            'time': '2021-03-14 15:30:28',
            'model': 'Bresser-ProRainGauge',
            'id': 17,
            'battery_ok': 1,
            'temperature_C': 9.800,
            'rain_mm': 122.000,
            'mic': 'CHECKSUM',
        },
    )

    @staticmethod
    def parse_json(obj):
        sensor_id = obj.get('id')
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRICWX
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['rain_total'] = Packet.get_float(obj, 'rain_mm')
        pkt['battery'] = Packet.get_battery(obj)
        pkt = Packet.add_identifiers(pkt, sensor_id, BresserProRainGaugePacket.__name__)
        return pkt
