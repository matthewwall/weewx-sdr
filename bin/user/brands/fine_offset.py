import re

import weewx

from ..packet import Packet
from ..units import to_v


class FOWH1080Packet(Packet):
    # this assumes rain total is in mm
    # this assumes wind speed is kph

    IDENTIFIER = 'Fine Offset WH1080 weather station'

    EXAMPLES = (
        {
            'time': '2016-11-04 14:40:38',
            'model': 'Fine Offset WH1080 weather station',
            'msg_type': 0,
            'id': 38,
            'temperature_C': 12.500,
            'humidity': 68,
            'direction_str': 'E',
            'direction_deg': '90',
            'speed': 8.568,
            'gust': 12.240,
            'rain': 249.600,
            'battery': 'OK',
        },
    )
    TEXT_EXAMPLES = (
        (
            '2016-09-02 22:26:05 :Fine Offset WH1080 weather station',
            'Msg type: 0',
            'StationID: 0026',
            'Temperature: 19.9 C',
            'Humidity: 78 %',
            'Wind string: E',
            'Wind degrees: 90',
            'Wind avg speed: 0.00',
            'Wind gust: 1.22',
            'Total rainfall: 144.3',
            'Battery: OK',
        ),
    )

    PARSEINFO = {
        #        'Msg type': ['msg_type', None, None],
        'StationID': ['station_id', None, None],
        'Temperature': ['temperature', re.compile(r'([\d.-]+) C'), lambda x: float(x)],
        'Humidity': ['humidity', re.compile(r'([\d.]+) %'), lambda x: float(x)],
        #        'Wind string': ['wind_dir_ord', None, None],
        'Wind degrees': ['wind_dir', None, lambda x: int(x)],
        'Wind avg speed': ['wind_speed', None, lambda x: float(x)],
        'Wind gust': ['wind_gust', None, lambda x: float(x)],
        'Total rainfall': ['rain_total', None, lambda x: float(x)],
        'Battery': ['battery', None, lambda x: 0 if x == 'OK' else 1],
    }

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, FOWH1080Packet.PARSEINFO))
        return FOWH1080Packet.insert_ids(pkt)

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['station_id'] = obj.get('id')
        pkt['msg_type'] = Packet.get_int(obj, 'msg_type')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['wind_dir'] = Packet.get_float(obj, 'direction_deg')
        pkt['wind_speed'] = Packet.get_float(obj, 'speed')
        pkt['wind_gust'] = Packet.get_float(obj, 'gust')
        rain_total = Packet.get_float(obj, 'rain')
        if rain_total is not None:
            pkt['rain_total'] = rain_total / 10.0  # convert to cm
        pkt['battery'] = Packet.get_battery(obj)
        return FOWH1080Packet.insert_ids(pkt)

    @staticmethod
    def insert_ids(pkt):
        station_id = pkt.pop('station_id', '0000')
        return Packet.add_identifiers(pkt, station_id, FOWH1080Packet.__name__)


class FOWHx080Packet(Packet):
    # apparently there are different identifiers for the same packet, depending
    # on which version of rtl_433 is running.  one version has extra spaces,
    # while another version does not.  so for now, and until rtl_433
    # stabilizes, match on something unique to these packets that still matches
    # the strings from different rtl_433 versions.

    # this assumes rain total is in mm (as of dec 2019)
    # this assumes wind speed is kph (as of dec 2019)

    # todays rtl_433 output

    # IDENTIFIER = "Fine Offset Electronics WH1080 / WH3080 Weather Station"
    # IDENTIFIER = "Fine Offset Electronics WH1080/WH3080 Weather Station"
    # IDENTIFIER = "Fine Offset Electronics WH1080"
    IDENTIFIER = 'Fineoffset-WHx080'
    # 2017-05-15 11:58:31: Fine Offset Electronics WH1080 / WH3080 Weather Station
    # Msg type: 0
    # Station ID: 236
    # Temperature: 23.9 C
    # Humidity: 48%
    # Wind string: NE
    # Wind degrees: 45
    # Wind Avg Speed: 1.22
    # Wind gust: 2.45
    # Total rainfall: 525.3
    # Battery: OK

    # 2017-05-15 12:04:48: Fine Offset Electronics WH1080 / WH3080 Weather Station
    # Msg type: 1
    # Station ID: 173
    # Signal Type: WWVB / MSF
    # Hours: 21
    # Minutes: 71
    # Seconds: 11
    # Year: 2165
    # Month: 25
    # Day: 70
    EXAMPLES = (
        {
            'time': '2020-10-13 14:04:48',
            'model': 'Fine Offset Electronics WH1080/WH3080 Weather Station',
            'msg_type': 0,
            'id': 14,
            'battery': 'OK',
            'temperature_C': 24.400,
            'humidity': 35,
            'direction_deg': 225,
            'speed': 0.000,
            'gust': 0.000,
            'rain': 41.400,
            'mic': 'CRC',
        },
        {
            'time': '2020-10-13 14:04:48',
            'model': 'Fineoffset-WHx080',
            'subtype': 0,
            'id': 14,
            'battery_ok': 1,
            'temperature_C': 24.400,
            'humidity': 35,
            'wind_dir_deg': 225,
            'wind_avg_km_h': 0.000,
            'wind_max_km_h': 0.000,
            'rain_mm': 41.400,
            'mic': 'CRC',
        },
        {
            'time': '2022-08-17 15:58:42',
            'model': 'Fineoffset-WHx080',
            'subtype': 0,
            'id': 14,
            'battery_ok': 1,
            'temperature_C': 28.100,
            'humidity': 36,
            'wind_dir_deg': 338,
            'wind_avg_km_h': 0.000,
            'wind_max_km_h': 1.224,
            'rain_mm': 614.400,
            'mic': 'CRC',
        },
        {
            'time': '2022-08-14 17:22:30',
            'model': 'Fineoffset-WHx080',
            'subtype': 2,
            'uv_sensor_id': 225,
            'uv_status': 'OK',
            'uv_index': 1,
            'lux': 2223.200,
            'wm': 3.255,
            'mic': 'CRC',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        msg_type = obj.get('subtype')
        pkt['msg_type'] = msg_type

        if msg_type == 0:
            pkt['station_id'] = obj.get('id')
            pkt['battery'] = Packet.get_battery(obj)
            pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
            pkt['humidity'] = Packet.get_float(obj, 'humidity')
            pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
            pkt['wind_speed'] = Packet.get_float(obj, 'wind_avg_km_h')
            pkt['wind_gust'] = Packet.get_float(obj, 'wind_max_km_h')
            rain_total = Packet.get_float(obj, 'rain_mm')
            if rain_total is not None:
                pkt['rain_total'] = rain_total / 10.0  # convert to cm

        if msg_type == 2:
            pkt['station_id'] = obj.get('uv_sensor_id')
            pkt['uv_status'] = 0 if obj.get('uv_status') == 'OK' else 1
            pkt['uv_index'] = Packet.get_float(obj, 'uv_index')
            pkt['luminosity'] = Packet.get_float(obj, 'lux')
            pkt['radiation'] = Packet.get_float(obj, 'wm')

        return FOWHx080Packet.insert_ids(pkt)

    @staticmethod
    def insert_ids(pkt):
        station_id = pkt.pop('station_id', '0000')
        return Packet.add_identifiers(pkt, station_id, FOWHx080Packet.__name__)


class FOWH3080Packet(Packet):
    IDENTIFIER = 'Fine Offset Electronics WH3080 Weather Station'
    # 2017-05-15 11:58:08: Fine Offset Electronics WH3080 Weather Station
    # Msg type: 2
    # UV Sensor ID: 225
    # Sensor Status: OK
    # UV Index: 8
    # Lux: 120160.5
    # Watts / m: 175.93
    # Foot-candles: 11167.33
    EXAMPLES = (
        {
            'time': '2017-05-15 17:21:07',
            'model': 'Fine Offset Electronics WH3080 Weather Station',
            'msg_type': 2,
            'uv_sensor_id': 225,
            'uv_status': 'OK',
            'uv_index': 1,
            'lux': 7837.000,
            'wm': 11.474,
            'fc': 728.346,
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['station_id'] = obj.get('uv_sensor_id')
        pkt['msg_type'] = Packet.get_int(obj, 'msg_type')
        pkt['uv_index'] = Packet.get_float(obj, 'uv_index')
        pkt['luminosity'] = Packet.get_float(obj, 'lux')
        pkt['radiation'] = Packet.get_float(obj, 'wm')
        pkt['illumination'] = Packet.get_float(obj, 'fc')
        pkt['uv_status'] = 0 if obj.get('uv_status') == 'OK' else 1
        return FOWH3080Packet.insert_ids(pkt)

    @staticmethod
    def insert_ids(pkt):
        station_id = pkt.pop('station_id', '0000')
        return Packet.add_identifiers(pkt, station_id, FOWH3080Packet.__name__)


class FOWH2Packet(Packet):
    IDENTIFIER = 'Fine Offset Electronics, WH2'

    EXAMPLES = (
        {
            'time': '2018-08-29 17:08:33',
            'model': 'Fine Offset Electronics, WH2 Temperature/Humidity sensor',
            'id': 129,
            'temperature_C': 24.200,
            'mic': 'CRC',
        },
    )

    PARSEINFO = {
        'ID': ['station_id', None, lambda x: int(x)],
        'Temperature': ['temperature', re.compile(r'([\d.-]+) C'), lambda x: float(x)],
    }

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, FOWH2Packet.PARSEINFO))
        return FOWH2Packet.insert_ids(pkt)

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['station_id'] = obj.get('id')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        return FOWH2Packet.insert_ids(pkt)

    @staticmethod
    def insert_ids(pkt):
        station_id = pkt.pop('station_id', '0000')
        return Packet.add_identifiers(pkt, station_id, FOWH2Packet.__name__)


class FOWH5Packet(Packet):
    IDENTIFIER = 'Fine Offset WH5 sensor'

    EXAMPLES = (
        {
            'time': '2019-10-27 14:51:21',
            'model': 'Fine Offset WH5 sensor',
            'id': 48,
            'temperature_C': 11.700,
            'humidity': 62,
            'mic': 'CRC',
        },
    )

    PARSEINFO = {
        'ID': ['station_id', None, lambda x: int(x)],
        'Temperature': ['temperature', re.compile(r'([\d.-]+) C'), lambda x: float(x)],
    }

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, FOWH5Packet.PARSEINFO))
        return FOWH5Packet.insert_ids(pkt)

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['station_id'] = obj.get('id')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        return FOWH5Packet.insert_ids(pkt)

    @staticmethod
    def insert_ids(pkt):
        station_id = pkt.pop('station_id', '0000')
        return Packet.add_identifiers(pkt, station_id, FOWH5Packet.__name__)


class FOWH24Packet(Packet):
    IDENTIFIER = 'Fine Offset WH24'
    # This is for a WH24 which is the sensor array for several station models
    EXAMPLES = (
        {
            'time': '2019-02-11 03:44:32',
            'model': 'Fine Offset WH24',
            'id': 140,
            'temperature_C': 12.600,
            'humidity': 80,
            'wind_dir_deg': 111,
            'wind_speed_ms': 0.280,
            'gust_speed_ms': 1.120,
            'rainfall_mm': 1150.800,
            'uv': 1,
            'uvi': 0,
            'light_lux': 0.000,
            'battery': 'OK',
            'mic': 'CRC',
        },
        {
            'time': '2019-02-11 03:44:48',
            'model': 'Fine Offset WH24',
            'id': 140,
            'temperature_C': 12.600,
            'humidity': 80,
            'wind_dir_deg': 109,
            'wind_speed_ms': 0.980,
            'gust_speed_ms': 1.120,
            'rainfall_mm': 1150.800,
            'uv': 1,
            'uvi': 0,
            'light_lux': 0.000,
            'battery': 'OK',
            'mic': 'CRC',
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
        pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
        pkt['wind_speed'] = Packet.get_float(obj, 'wind_speed_ms')
        pkt['wind_gust'] = Packet.get_float(obj, 'gust_speed_ms')
        pkt['rain_total'] = Packet.get_float(obj, 'rainfall_mm')
        pkt['uv_index'] = Packet.get_float(obj, 'uvi')
        pkt['light'] = Packet.get_float(obj, 'light_lux')
        pkt['battery'] = Packet.get_battery(obj)
        pkt = Packet.add_identifiers(pkt, sensor_id, FOWH24Packet.__name__)
        return pkt


class FOWH24BPacket(Packet):
    # different mappings for the WH24 sensor

    IDENTIFIER = 'Fineoffset-WH24'

    EXAMPLES = (
        {
            'time': '2020-08-01 14:03:52',
            'model': 'Fineoffset-WH24',
            'id': 247,
            'battery_ok': 1,
            'temperature_C': 30.600,
            'humidity': 45,
            'wind_dir_deg': 149,
            'wind_avg_m_s': 0.000,
            'wind_max_m_s': 0.000,
            'rain_mm': 6.600,
            'uv': 783,
            'uvi': 1,
            'light_lux': 28025.000,
            'mic': 'CRC',
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
        pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
        pkt['wind_speed'] = Packet.get_float(obj, 'wind_avg_m_s')
        pkt['wind_gust'] = Packet.get_float(obj, 'wind_max_m_s')
        pkt['rain_total'] = Packet.get_float(obj, 'rain_mm')
        pkt['uv_index'] = Packet.get_float(obj, 'uvi')
        pkt['light'] = Packet.get_float(obj, 'light_lux')
        pkt['battery'] = Packet.get_battery(obj)
        pkt = Packet.add_identifiers(pkt, sensor_id, FOWH24BPacket.__name__)
        return pkt


class FOWH25Packet(Packet):
    #

    IDENTIFIER = 'Fineoffset-WH25'

    EXAMPLES = (
        {
            'time': '2017-03-25 05:33:57',
            'model': 'Fine Offset Electronics, WH25',
            'id': 239,
            'temperature_C': 30.200,
            'humidity': 68,
            'pressure': 1008.000,
        },
        {
            'time': '2018-10-10 13:37:11',
            'model': 'Fine Offset Electronics, WH25',
            'id': 21,
            'temperature_C': 21.600,
            'humidity': 66,
            'pressure_hPa': 972.800,
            'battery': 'OK',
            'mic': 'CHECKSUM',
        },
        {
            'time': '2020-10-13 23:29:35',
            'model': 'Fineoffset-WH25',
            'id': 170,
            'battery_ok': 0,
            'temperature_C': 26.200,
            'humidity': 36,
            'pressure_hPa': 1009.900,
            'mic': 'CRC',
        },
        {
            'time': '2021-04-08 18:11:01',
            'model': 'Fineoffset-WH25',
            'id': 121,
            'battery_ok': 1,
            'temperature_C': 20.000,
            'humidity': 48,
            'pressure_hPa': 979.100,
            'mic': 'CRC',
        },
        {
            'time': '2020-08-01 14:03:16',
            'model': 'Fineoffset-WH25',
            'id': 19,
            'battery_ok': 1,
            'temperature_C': 26.100,
            'humidity': 49,
            'pressure_hPa': 987.800,
            'mic': 'CRC',
        },
    )
    TEXT_EXAMPLES = (
        (
            '2016-09-02 22:26:05 :   Fine Offset Electronics, WH25',
            'ID:     239',
            'Temperature: 19.9 C',
            'Humidity: 78 %',
            'Pressure: 1007.9 hPa',
        ),
        (
            '2018-10-09 19:45:12 :   Fine Offset Electronics, WH25',
            'id : 21',
            'temperature_C : 20.900',
            'humidity : 65',
            'pressure_hPa : 980.400',
            'battery : OK',
            'mic : CHECKSUM',
        ),
    )

    PARSEINFO = {
        'ID': ['station_id', None, lambda x: int(x)],
        'Temperature': ['temperature', re.compile(r'([\d.-]+) C'), lambda x: float(x)],
        'Humidity': ['humidity', re.compile(r'([\d.]+) %'), lambda x: float(x)],
        'Pressure': ['pressure', re.compile(r'([\d.-]+) hPa'), lambda x: float(x)],
    }

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, FOWH25Packet.PARSEINFO))
        return FOWH25Packet.insert_ids(pkt)

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['station_id'] = obj.get('id')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['pressure'] = Packet.get_float(obj, 'pressure_hPa')
        pkt['battery'] = Packet.get_battery(obj)
        return FOWH25Packet.insert_ids(pkt)

    @staticmethod
    def insert_ids(pkt):
        station_id = pkt.pop('station_id', '0000')
        return Packet.add_identifiers(pkt, station_id, FOWH25Packet.__name__)


class FOWH32Packet(Packet):
    IDENTIFIER = 'Fineoffset-WH32'

    EXAMPLES = (
        {
            'time': '2024-03-04 17:41:55',
            'model': 'Fineoffset-WH32',
            'id': 35,
            'battery_ok': 1,
            'temperature_C': 3.2,
            'humidity': 91,
            'mic': 'CRC',
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
        pkt['battery'] = Packet.get_battery(obj)
        pkt['channel'] = Packet.get_int(obj, 'channel')
        pkt = Packet.add_identifiers(pkt, sensor_id, FOWH32Packet.__name__)
        return pkt


class FOWH32BPacket(Packet):
    IDENTIFIER = 'Fineoffset-WH32B'
    # This is for a WH32B which is the indoors sensor array for an Ambient
    # Weather WS-2902A. The same sensor array is used for several models.

    # time      : 2019-04-08 00:48:02
    # model     : Fineoffset-WH32B
    # ID        : 146
    # Temperature: 17.5 C
    # Humidity  : 60 %
    # Pressure  : 1001.2 hPa
    # Battery   : OK
    # Integrity : CHECKSUM
    EXAMPLES = (
        {
            'time': '2019-04-08 07:06:03',
            'model': 'Fineoffset-WH32B',
            'id': 146,
            'temperature_C': 16.900,
            'humidity': 59,
            'pressure_hPa': 1001.300,
            'battery': 'OK',
            'mic': 'CHECKSUM',
        },
        {
            'time': '2022-03-24 02:27:27',
            'model': 'Fineoffset-WH32B',
            'id': 114,
            'battery_ok': 1,
            'temperature_C': 20.700,
            'humidity': 49,
            'pressure_hPa': 960.300,
            'mic': 'CRC',
            'mod': 'FSK',
            'freq1': 914.964,
            'freq2': 915.026,
            'rssi': -0.118,
            'snr': 20.295,
            'noise': -20.412,
        },
    )

    @staticmethod
    def parse_json(obj):
        sensor_id = obj.get('id')
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['pressure'] = Packet.get_float(obj, 'pressure_hPa')
        pkt['battery'] = Packet.get_battery(obj)
        pkt['freq1'] = Packet.get_float(obj, 'freq1')
        pkt['freq2'] = Packet.get_float(obj, 'freq2')
        pkt['rssi'] = Packet.get_float(obj, 'rssi')
        pkt['snr'] = Packet.get_float(obj, 'snr')
        pkt['noise'] = Packet.get_float(obj, 'noise')
        pkt = Packet.add_identifiers(pkt, sensor_id, FOWH32BPacket.__name__)
        return pkt


class FOWH45Packet(Packet):
    IDENTIFIER = 'Fineoffset-WH45'
    # This is for a WH45 Air Quality Monitor
    EXAMPLES = (
        {
            'time': '2023-07-08 13:06:14',
            'model': 'Fineoffset-WH45',
            'id': 18034,
            'battery_ok': 1.000,
            'temperature_C': 20.400,
            'humidity': 84,
            'pm2_5_ug_m3': 1.800,
            'pm10_ug_m3': 1.800,
            'co2_ppm': 718,
            'ext_power': 1,
            'mic': 'CRC',
        },
    )

    @staticmethod
    def parse_json(obj):
        sensor_id = obj.get('id')
        pkt = dict()
        pkt['usUnits'] = weewx.METRIC
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['battery'] = Packet.get_battery(obj)
        pkt['co2_atm'] = Packet.get_float(obj, 'co2_ppm')
        pkt['pm2_5_atm'] = Packet.get_float(obj, 'pm2_5_ug_m3')
        pkt['pm10_0_atm'] = Packet.get_float(obj, 'pm10_ug_m3')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt = Packet.add_identifiers(pkt, sensor_id, FOWH45Packet.__name__)
        return pkt


class FOWH51Packet(Packet):
    IDENTIFIER = 'Fineoffset-WH51'
    # This is for a WH051 Soil Moisture Sensor (Fine Offset / Ecowitt WH51)
    EXAMPLES = (
        {
            'time': '2021-04-15 15:07:05',
            'model': 'Fineoffset-WH51',
            'id': '00df73',
            'battery_ok': 1.000,
            'battery_mV': 1600,
            'moisture': 0,
            'boost': 0,
            'ad_raw': 17,
            'mic': 'CRC',
            'mod': 'FSK',
            'freq1': 915.024,
            'freq2': 914.970,
            'rssi': -2.258,
            'snr': 35.115,
            'noise': -37.373,
        },
    )

    @staticmethod
    def parse_json(obj):
        sensor_id = obj.get('id')
        pkt = dict()
        pkt['usUnits'] = weewx.METRIC
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['soil_moisture_percent'] = Packet.get_float(obj, 'moisture')
        pkt['boost'] = Packet.get_float(obj, 'boost')
        pkt['soil_moisture_raw'] = Packet.get_float(obj, 'ad_raw')
        pkt['freq1'] = Packet.get_float(obj, 'freq1')
        pkt['freq2'] = Packet.get_float(obj, 'freq2')
        pkt['battery'] = Packet.get_battery(obj)
        pkt['battery_mV'] = Packet.get_float(obj, 'battery_mV')
        pkt['snr'] = Packet.get_float(obj, 'snr')
        pkt['rssi'] = Packet.get_float(obj, 'rssi')
        pkt['noise'] = Packet.get_float(obj, 'noise')
        pkt = Packet.add_identifiers(pkt, sensor_id, FOWH51Packet.__name__)
        return pkt


class FOWH65BPacket(Packet):
    IDENTIFIER = 'Fine Offset WH65B'
    # This is for a WH65B which is the sensor array for an Ambient Weather
    # WS-2902A. The same sensor array is used for several models.

    # 2018-10-10 13:37:02 :   Fine Offset WH65B
    # id : 89
    # temperature_C : 17.600
    # humidity : 93
    # wind_dir_deg : 224
    # wind_speed_ms : 1.540
    # gust_speed_ms : 2.240
    # rainfall_mm : 325.500
    # uv : 130
    # uvi : 0
    # light_lux : 13454.000
    # battery : OK
    # mic : CRC
    EXAMPLES = (
        {
            'time': '2018-10-10 13:37:02',
            'model': 'Fine Offset WH65B',
            'id': 89,
            'temperature_C': 17.600,
            'humidity': 93,
            'wind_dir_deg': 224,
            'wind_speed_ms': 1.540,
            'gust_speed_ms': 2.240,
            'rainfall_mm': 325.500,
            'uv': 130,
            'uvi': 0,
            'light_lux': 13454.000,
            'battery': 'OK',
            'mic': 'CRC',
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
        pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
        pkt['wind_speed'] = Packet.get_float(obj, 'wind_speed_ms')
        pkt['wind_gust'] = Packet.get_float(obj, 'gust_speed_ms')
        pkt['rain_total'] = Packet.get_float(obj, 'rainfall_mm')
        pkt['uv'] = Packet.get_float(obj, 'uv')
        pkt['uv_index'] = Packet.get_float(obj, 'uvi')
        pkt['light'] = Packet.get_float(obj, 'light_lux')
        pkt['battery'] = Packet.get_battery(obj)
        pkt = Packet.add_identifiers(pkt, sensor_id, FOWH65BPacket.__name__)
        return pkt


class FOWH65BAltPacket(Packet):
    IDENTIFIER = 'Fineoffset-WH65B'
    # This is for a WH65B sensor array that identifies itself as
    # Fineoffset-WH65B. Several mappings are also different from the other
    # WH65B. This configuration was tested on an Ambient Weather WS-2902A kit.

    # time : 2020-04-26 23:21:42
    # model : Fineoffset-WH65B
    # id : 16
    # temperature_C : 15.400
    # humidity : 51
    # wind_dir_deg : 323
    # wind_avg_m_s : 1.020
    # wind_max_m_s : 2.040
    # rain_mm : 76.453
    # uv : 701
    # uvi : 2
    # light_lux : 14616.000
    # battery_ok : OK
    # mic : CRC
    EXAMPLES = (
        {
            'time': '2020-04-26 19:41:10',
            'model': 'Fineoffset-WH65B',
            'id': 16,
            'battery_ok': 1,
            'temperature_C': 14.800,
            'humidity': 50,
            'wind_dir_deg': 336,
            'wind_avg_m_s': 1.658,
            'wind_max_m_s': 3.060,
            'rain_mm': 76.454,
            'uv': 1982,
            'uvi': 4,
            'light_lux': 69130.000,
            'mic': 'CRC',
        },
        {
            'time': '2020-07-22 04:47:47',
            'model': 'Fineoffset-WH65B',
            'id': 73,
            'battery_ok': 1,
            'temperature_C': 24.900,
            'humidity': 53,
            'wind_dir_deg': 21,
            'wind_avg_m_s': 0.000,
            'wind_max_m_s': 0.000,
            'rain_mm': 7.874,
            'uv': 1,
            'uvi': 0,
            'light_lux': 0.000,
            'mic': 'CRC',
        },
        {
            'time': '2022-03-24 02:27:26',
            'model': 'Fineoffset-WH65B',
            'id': 86,
            'battery_ok': 1,
            'temperature_C': 2.400,
            'humidity': 94,
            'wind_dir_deg': 268,
            'wind_avg_m_s': 0.701,
            'wind_max_m_s': 1.020,
            'rain_mm': 2411.222,
            'uv': 2,
            'uvi': 0,
            'light_lux': 0.000,
            'mic': 'CRC',
            'mod': 'FSK',
            'freq1': 914.965,
            'freq2': 915.019,
            'rssi': -0.120,
            'snr': 20.011,
            'noise': -20.130,
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
        pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
        pkt['wind_speed'] = Packet.get_float(obj, 'wind_avg_m_s')
        pkt['wind_gust'] = Packet.get_float(obj, 'wind_max_m_s')
        pkt['rain_total'] = Packet.get_float(obj, 'rain_mm')
        pkt['uv'] = Packet.get_float(obj, 'uv')  # superfluous?
        pkt['uv_index'] = Packet.get_float(obj, 'uvi')
        pkt['light'] = Packet.get_float(obj, 'light_lux')
        pkt['battery'] = Packet.get_battery(obj)
        pkt['rssi'] = Packet.get_float(obj, 'rssi')
        pkt['snr'] = Packet.get_float(obj, 'snr')
        pkt['noise'] = Packet.get_float(obj, 'noise')
        pkt = Packet.add_identifiers(pkt, sensor_id, FOWH65BAltPacket.__name__)
        return pkt


class FOWH0290Packet(Packet):
    IDENTIFIER = 'Fineoffset-WH0290'
    # This is for a WH0290 Air Quality Monitor (Ambient Weather PM25)
    EXAMPLES = (
        {
            'time': '@0.084044s',
            'model': 'Fine Offset Electronics, WH0290',
            'id': 204,
            'pm2_5_ug_m3': 9,
            'pm10_0_ug_m3': 10,
            'mic': 'CHECKSUM',
        },
        {
            'time': '2022-09-08 19:48:38',
            'model': 'Endoffset-WH0290',
            ' id ': 142,
            ' battery_ok ': 0.800,
            ' pm2_5_ug_m3 ': 2,
            ' estimated_pm10_0_ug_m3 ': 2,
            ' family ': 65,
            ' unknown1 ': 0,
            ' mic ': ' CRC ',
        },
    )

    @staticmethod
    def parse_json(obj):
        sensor_id = obj.get('id')
        pkt = dict()
        pkt['usUnits'] = weewx.METRIC
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['battery'] = Packet.get_battery(obj)
        pkt['pm2_5_atm'] = Packet.get_float(obj, 'pm2_5_ug_m3')
        pkt['pm10_0_atm'] = Packet.get_float(obj, 'estimated_pm10_0_ug_m3')
        pkt = Packet.add_identifiers(pkt, sensor_id, FOWH0290Packet.__name__)
        return pkt


class FOWH31LPacket(Packet):
    IDENTIFIER = 'FineOffset-WH31L'
    # This is for a WH31L lightning detector
    EXAMPLES = (
        {
            'time': '2021-06-30 20:37:11',
            'model': 'FineOffset-WH31L',
            'id': 67016,
            'battery_ok': 0,
            'state': 8,
            'flags': 56,
            'storm_dist_km': 10,
            'strike_count': 2,
            'mic': 'CRC',
        },
    )

    @staticmethod
    def parse_json(obj):
        sensor_id = obj.get('id')
        pkt = dict()
        pkt['usUnits'] = weewx.METRIC
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['battery'] = Packet.get_battery(obj)
        pkt['strikes_total'] = obj.get('strike_count')
        pkt['distance'] = obj.get('storm_dist_km')
        pkt['flags'] = obj.get('flags')
        pkt['state'] = obj.get('state')
        pkt = Packet.add_identifiers(pkt, sensor_id, FOWH31LPacket.__name__)
        return pkt


class FOWS80Packet(Packet):
    IDENTIFIER = 'Fineoffset-WS80'
    # This is for a Fine Offset Electronics WS80 weather station
    EXAMPLES = (
        {
            'time': '2022-07-06 21:06:18',
            'model': 'Fineoffset-WS80',
            'id': 589862,
            'battery_ok': 1.170,
            'battery_mV': 3280,
            'temperature_C': 17.700,
            'humidity': 67,
            'wind_dir_deg': 268,
            'wind_avg_m_s': 1.300,
            'wind_max_m_s': 1.800,
            'uvi': 0.000,
            'light_lux': 0.000,
            'flags': 170,
            'mic': 'CRC',
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
        pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
        pkt['wind_speed'] = Packet.get_float(obj, 'wind_avg_m_s')
        pkt['wind_gust'] = Packet.get_float(obj, 'wind_max_m_s')
        pkt['rain_total'] = Packet.get_float(obj, 'rainfall_mm')
        pkt['uv_index'] = Packet.get_float(obj, 'uvi')
        pkt['light'] = Packet.get_float(obj, 'light_lux')
        # pkt['battery'] = 0 if obj.get('battery_ok') == 1 else 1
        pkt['voltage'] = to_v(Packet.get_float(obj, 'battery_mV'))
        pkt = Packet.add_identifiers(pkt, sensor_id, FOWS80Packet.__name__)
        return pkt


class FOWS90Packet(Packet):
    IDENTIFIER = 'Fineoffset-WS90'
    # time : 2020-04-26 23:21:42
    # model : Fineoffset-WS90
    # id : 16
    # temperature_C : 15.400
    # humidity : 51
    # wind_dir_deg : 323
    # wind_avg_m_s : 1.020
    # wind_max_m_s : 2.040
    # rain_mm : 76.453
    # uvi : 2
    # light_lux : 14616.000
    # supercap_V: 3.200
    # battery_ok: OK
    # battery_mV: 3280
    # mic : CRC
    EXAMPLES = (
        {
            'time': '2023-03-08 22:00:38',
            'model': 'Fineoffset-WS90',
            'id': 13355,
            'battery_ok': 1.0,
            'battery_mV': 3280,
            'temperature_C': 5.700,
            'humidity': 75,
            'wind_dir_deg': 87,
            'wind_avg_m_s': 1.300,
            'wind_max_m_s': 1.600,
            'uvi': 0.000,
            'light_lux': 55300.000,
            'flags': 129,
            'rain_mm': 12.800,
            'supercap_V': 3.200,
            'data': '01c00000192000fe7ff0ff0082',
            'mic': 'CRC',
            'mod': 'FSK',
            'freq1': 914.945,
            'freq2': 915.039,
            'rssi': -0.123,
            'snr': 32.990,
            'noise': -33.113,
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
        pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
        pkt['wind_speed'] = Packet.get_float(obj, 'wind_avg_m_s')
        pkt['wind_gust'] = Packet.get_float(obj, 'wind_max_m_s')
        pkt['rain_total'] = Packet.get_float(obj, 'rain_mm')
        pkt['uv_index'] = Packet.get_float(obj, 'uvi')
        pkt['light'] = Packet.get_float(obj, 'light_lux')  # superfluous?
        pkt['battery'] = Packet.get_battery(obj)
        v = Packet.get_float(obj, 'battery_mV')
        if v is not None:
            v = round(v * 0.001, 2)
            pkt['supplyVoltage'] = v
        pkt['referenceVoltage'] = Packet.get_float(obj, 'supercap_V')
        pkt['freq1'] = Packet.get_float(obj, 'freq1')
        pkt['freq2'] = Packet.get_float(obj, 'freq2')
        pkt['rssi'] = Packet.get_float(obj, 'rssi')
        pkt['snr'] = Packet.get_float(obj, 'snr')
        pkt['noise'] = Packet.get_float(obj, 'noise')
        pkt = Packet.add_identifiers(pkt, sensor_id, FOWS90Packet.__name__)
        return pkt
