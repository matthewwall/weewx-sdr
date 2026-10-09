import re

import weewx
import weewx.units

from ..packet import Packet


class Hideki(object):
    @staticmethod
    def insert_ids(pkt, pkt_type):
        channel = pkt.pop('channel', 0)
        code = pkt.pop('rolling_code', 0)
        sensor_id = '%s:%s' % (channel, code)
        pkt = Packet.add_identifiers(pkt, sensor_id, pkt_type)
        return pkt


class HidekiTS04Packet(Packet):
    IDENTIFIER = 'Hideki-TS04'

    EXAMPLES = (
        {
            'time': '2016-11-04 14:44:37',
            'model': 'HIDEKI TS04 sensor',
            'rc': 9,
            'channel': 1,
            'battery': 'OK',
            'temperature_C': 12.400,
            'humidity': 61,
        },
        {
            'time': '2020-10-15 07:13:33',
            'model': 'Hideki-TS04',
            'id': 14,
            'channel': 1,
            'battery_ok': 1,
            'temperature_C': 20.700,
            'humidity': 10,
            'mic': 'CRC',
        },
    )
    TEXT_EXAMPLES = (
        (
            '2016-08-31 17:41:30 :   HIDEKI TS04 sensor',
            'Rolling Code: 9',
            'Channel: 1',
            'Battery: OK',
            'Temperature: 27.30 C',
            'Humidity: 60 %',
        ),
    )

    PARSEINFO = {
        'Rolling Code': ['rolling_code', None, lambda x: int(x)],
        'Channel': ['channel', None, lambda x: int(x)],
        'Battery': ['battery', None, lambda x: 0 if x == 'OK' else 1],
        'Temperature': ['temperature', re.compile(r'([\d.-]+) C'), lambda x: float(x)],
        'Humidity': ['humidity', re.compile(r'([\d.]+) %'), lambda x: float(x)],
    }

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, HidekiTS04Packet.PARSEINFO))
        return Hideki.insert_ids(pkt, HidekiTS04Packet.__name__)

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['rolling_code'] = obj.get('id')
        pkt['channel'] = obj.get('channel')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['battery'] = Packet.get_battery(obj)
        return Hideki.insert_ids(pkt, HidekiTS04Packet.__name__)


class HidekiWindPacket(Packet):
    #    IDENTIFIER = "HIDEKI Wind sensor"
    IDENTIFIER = 'Hideki-Wind'

    EXAMPLES = (
        {
            'time': '2017-01-16 04:38:39',
            'model': 'HIDEKI Wind sensor',
            'rc': 0,
            'channel': 4,
            'battery': 'OK',
            'temperature_C': -4.400,
            'windstrength': 2.897,
            'winddirection': 292.500,
        },
        {
            'time': '2019-11-24 19:13:41',
            'model': 'HIDEKI Wind sensor',
            'rc': 3,
            'channel': 4,
            'battery': 'OK',
            'temperature_C': 11.000,
            'wind_speed_mph': 1.300,
            'gust_speed_mph': 0.100,
            'wind_approach': 1,
            'wind_direction': 270.000,
            'mic': 'CRC',
        },
        {
            'time': '2021-02-07 03:44:54',
            'model': 'Hideki-Wind',
            'id': 8,
            'channel': 4,
            'battery_ok': 1,
            'temperature_C': 15.200,
            'wind_avg_mi_h': 2.600,
            'wind_max_mi_h': 2.900,
            'wind_approach': 1,
            'wind_dir_deg': 337.500,
            'mic': 'CRC',
        },
    )
    TEXT_EXAMPLES = (
        (
            '2017-01-16 05:39:42 : HIDEKI Wind sensor',
            'Rolling Code: 0',
            'Channel: 4',
            'Battery: OK',
            'Temperature: -5.0 C',
            'Wind Strength: 2.57 km/h',
            'Direction: 45.0 \\xc2\\xb0',
        ),
    )

    PARSEINFO = {
        'Rolling Code': ['rolling_code', None, lambda x: int(x)],
        'Channel': ['channel', None, lambda x: int(x)],
        'Battery': ['battery', None, lambda x: 0 if x == 'OK' else 1],
        'Temperature': ['temperature', re.compile(r'([\d.-]+) C'), lambda x: float(x)],
        'Wind Strength': ['wind_speed', re.compile(r'([\d.]+) km/h'), lambda x: float(x)],
        'Direction': ['wind_dir', re.compile(r'([\d.]+) '), lambda x: float(x)],
    }

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, HidekiWindPacket.PARSEINFO))
        return Hideki.insert_ids(pkt, HidekiWindPacket.__name__)

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['rolling_code'] = obj.get('id')
        pkt['channel'] = obj.get('channel')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        if 'wind_avg_mi_h' in obj:
            v = Packet.get_float(obj, 'wind_avg_mi_h')
            if v is not None:
                v /= weewx.units.MILE_PER_KM
            pkt['wind_speed'] = v
        elif 'wind_speed_mph' in obj:
            v = Packet.get_float(obj, 'wind_speed_mph')
            if v is not None:
                v /= weewx.units.MILE_PER_KM
            pkt['wind_speed'] = v
        else:
            pkt['wind_speed'] = Packet.get_float(obj, 'windstrength')
        if 'wind_dir_deg' in obj:
            pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
        elif 'wind_direction' in obj:
            pkt['wind_dir'] = Packet.get_float(obj, 'wind_direction')
        else:
            pkt['wind_dir'] = Packet.get_float(obj, 'winddirection')
        if 'wind_max_mi_h' in obj:
            v = Packet.get_float(obj, 'wind_max_mi_h')
            if v is not None:
                v /= weewx.units.MILE_PER_KM
            pkt['wind_gust'] = v
        elif 'gust_speed_mph' in obj:
            v = Packet.get_float(obj, 'gust_speed_mph')
            if v is not None:
                v /= weewx.units.MILE_PER_KM
            pkt['wind_gust'] = v
        pkt['battery'] = Packet.get_battery(obj)
        return Hideki.insert_ids(pkt, HidekiWindPacket.__name__)


class HidekiRainPacket(Packet):
    #    IDENTIFIER = "HIDEKI Rain sensor"
    IDENTIFIER = 'Hideki-Rain'

    EXAMPLES = (
        {
            'time': '2017-01-16 04:38:50',
            'model': 'HIDEKI Rain sensor',
            'rc': 0,
            'channel': 4,
            'battery': 'OK',
            'rain': 2622.900,
        },
        {
            'time': '2019-11-24 19:13:52',
            'model': 'HIDEKI Rain sensor',
            'rc': 0,
            'channel': 4,
            'battery': 'OK',
            'rain_mm': 274.400,
            'mic': 'CRC',
        },
        {
            'time': '2021-02-07 03:45:10',
            'model': 'Hideki-Rain',
            'id': 0,
            'channel': 4,
            'battery_ok': 1,
            'rain_mm': 1382.500,
            'mic': 'CRC',
        },
        {
            'time': '2023-11-10 14:42:06',
            'model': 'Hideki-Rain',
            'id': 0,
            'channel': 4,
            'battery_ok': 1,
            'rain_mm': 2255.400,
            'mic': 'CRC',
        },
    )
    TEXT_EXAMPLES = (
        (
            '2017-01-16 05:39:42 : HIDEKI Rain sensor',
            'Rolling Code: 0',
            'Channel: 4',
            'Battery: OK',
            'Rain: 2622.900',
        ),
    )

    PARSEINFO = {
        'Rolling Code': ['rolling_code', None, lambda x: int(x)],
        'Channel': ['channel', None, lambda x: int(x)],
        'Battery': ['battery', None, lambda x: 0 if x == 'OK' else 1],
        'Rain': ['rain_total', re.compile(r'([\d.]+) '), lambda x: float(x)],
    }

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, HidekiRainPacket.PARSEINFO))
        return Hideki.insert_ids(pkt, HidekiRainPacket.__name__)

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['rolling_code'] = obj.get('id')
        pkt['channel'] = obj.get('channel')
        if 'rain_mm' in obj:
            pkt['rain_total'] = Packet.get_float(obj, 'rain_mm')
        else:
            pkt['rain_total'] = Packet.get_float(obj, 'rain')
        pkt['battery'] = Packet.get_battery(obj)
        return Hideki.insert_ids(pkt, HidekiRainPacket.__name__)
