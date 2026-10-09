import re

import weewx

from ..packet import Packet


class LaCrosseBreezeProPacket(Packet):
    IDENTIFIER = 'LaCrosse-BreezePro'
    # sample json output from rtl_433
    EXAMPLES = (
        {
            'time': '2020-12-14 22:22:21',
            'model': 'LaCrosse-BreezePro',
            'id': 561556,
            'seq': 2,
            'flags': 0,
            'temperature_C': 19.800,
            'humidity': 50,
            'wind_avg_km_h': 0.000,
            'wind_dir_deg': 262,
            'mic': 'CRC',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['usUnits'] = weewx.METRIC
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['model'] = obj.get('model')
        pkt['hardware_id'] = '%d' % obj.get('id', 0)
        pkt['sequence_num'] = Packet.get_int(obj, 'seq')
        pkt['wind_speed'] = Packet.get_float(obj, 'wind_avg_km_h')
        pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        sensor_id = str(pkt.pop('hardware_id', '0000')).upper()
        return Packet.add_identifiers(pkt, sensor_id, LaCrosseBreezeProPacket.__name__)


class LaCrosseWSPacket(Packet):
    IDENTIFIER = 'LaCrosse WS'

    EXAMPLES = (
        {
            'time': '2016-11-04 14:42:49',
            'model': 'LaCrosse WS',
            'ws_id': 9,
            'id': 202,
            'temperature_C': 12.100,
        },
        {
            'time': '2016-11-04 14:44:58',
            'model': 'LaCrosse WS',
            'ws_id': 9,
            'id': 202,
            'humidity': 67,
        },
        {
            'time': '2016-11-04 14:49:16',
            'model': 'LaCrosse WS',
            'ws_id': 9,
            'id': 202,
            'wind_speed_ms': 0.800,
            'wind_direction': 270.000,
        },
    )
    TEXT_EXAMPLES = (
        (
            '2016-09-08 00:43:52 :LaCrosse WS :9 :202',
            'Temperature: 21.0 C',
        ),
        (
            '2016-09-08 00:43:53 :LaCrosse WS :9 :202',
            'Humidity: 92',
        ),
        (
            '2016-09-08 00:43:53 :LaCrosse WS :9 :202',
            'Wind speed: 0.0 m/s',
            'Direction: 67.500',
        ),
        (
            '2016-11-03 17:43:20 :LaCrosse WS :9 :202',
            'Rainfall: 850.04 mm',
        ),
    )

    PARSEINFO = {
        'Wind speed': ['wind_speed', re.compile(r'([\d.]+) m/s'), lambda x: float(x)],
        'Direction': ['wind_dir', None, lambda x: float(x)],
        'Temperature': ['temperature', re.compile(r'([\d.-]+) C'), lambda x: float(x)],
        'Humidity': ['humidity', None, lambda x: int(x)],
        'Rainfall': ['rain_total', re.compile(r'([\d.]+) mm'), lambda x: float(x)],
    }

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRICWX
        pkt.update(Packet.parse_lines(lines, LaCrosseWSPacket.PARSEINFO))
        parts = payload.split(':')
        if len(parts) == 3:
            pkt['ws_id'] = parts[1].strip()
            pkt['hw_id'] = parts[2].strip()
        return LaCrosseWSPacket.insert_ids(pkt)

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRICWX
        pkt['ws_id'] = obj.get('ws_id')
        pkt['hw_id'] = obj.get('id')
        if 'temperature_C' in obj:
            pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        if 'humidity' in obj:
            pkt['humidity'] = Packet.get_float(obj, 'humidity')
        if 'wind_speed_ms' in obj:
            pkt['wind_speed'] = Packet.get_float(obj, 'wind_speed_ms')
        if 'wind_direction' in obj:
            pkt['wind_dir'] = Packet.get_float(obj, 'wind_direction')
        if 'rain' in obj:
            pkt['rain_total'] = Packet.get_float(obj, 'rain')
        return LaCrosseWSPacket.insert_ids(pkt)

    @staticmethod
    def insert_ids(pkt):
        ws_id = pkt.pop('ws_id', 0)
        hardware_id = pkt.pop('hw_id', 0)
        sensor_id = '%s:%s' % (ws_id, hardware_id)
        pkt = Packet.add_identifiers(pkt, sensor_id, LaCrosseWSPacket.__name__)
        return pkt


class LaCrosseTX141Bv3Packet(Packet):
    IDENTIFIER = 'LaCrosse-TX141Bv3'

    EXAMPLES = (
        {
            'time': '2023-03-29 20:55:22',
            'model': 'LaCrosse-TX141Bv3',
            'id': 172,
            'channel': 1,
            'battery_ok': 1,
            'temperature_C': 3.700,
            'test': 'No',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        sensor_id = obj.get('id')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['battery'] = Packet.get_battery(obj)
        pkt = Packet.add_identifiers(pkt, sensor_id, LaCrosseTX141Bv3Packet.__name__)
        return pkt


class LaCrosseTX141THBv2Packet(Packet):
    IDENTIFIER = 'LaCrosse-TX141THBv2'

    EXAMPLES = (
        {
            'time': '2017-01-16 15:24:43',
            'temperature': 54.140,
            'humidity': 34,
            'id': 221,
            'model': 'LaCrosse TX141TH-Bv2 sensor',
            'battery': 'OK',
            'test': 'Yes',
        },
        {
            'time': '2020-10-28 00:22:25',
            'model': 'LaCrosse-TX141THBv2',
            'id': 50,
            'channel': 0,
            'battery_ok': 1,
            'temperature_C': -0.600,
            'humidity': 60,
            'test': 'No',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRICWX
        sensor_id = obj.get('id')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['battery'] = Packet.get_battery(obj)
        pkt = Packet.add_identifiers(pkt, sensor_id, LaCrosseTX141THBv2Packet.__name__)
        return pkt


class LaCrosseTXPacket(Packet):
    IDENTIFIER = 'LaCrosse TX Sensor'

    EXAMPLES = (
        {
            'time': '2017-07-30 21:11:19',
            'model': 'LaCrosse TX Sensor',
            'id': 127,
            'humidity': 34.000,
        },
        {
            'time': '2017-07-30 21:11:19',
            'model': 'LaCrosse TX Sensor',
            'id': 127,
            'temperature_C': 27.100,
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
        pkt = Packet.add_identifiers(pkt, sensor_id, LaCrosseTXPacket.__name__)
        return pkt


class LaCrosseTX18Packet(Packet):
    IDENTIFIER = 'LaCrosse-WS3600'

    EXAMPLES = (
        {
            'time': '2020-04-21 05:21:19',
            'model': 'LaCrosse-WS3600',
            'id': 184,
            'temperature_C': 9.400,
        },
        {'time': '2020-04-21 05:21:19', 'model': 'LaCrosse-WS3600', 'id': 184, 'humidity': 52},
        {'time': '2020-04-21 05:21:20', 'model': 'LaCrosse-WS3600', 'id': 184, 'rain_mm': 0.000},
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        sensor_id = obj.get('id')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt = Packet.add_identifiers(pkt, sensor_id, LaCrosseTX18Packet.__name__)
        return pkt


class LaCrosseLTVR3Packet(Packet):
    IDENTIFIER = 'LaCrosse-R3'
    EXAMPLES = (
        {
            'time': '2022-01-16 04:43:25',
            'model': 'LaCrosse-R3',
            'id': 7417878,
            'battery_ok': 1,
            'seq': 1,
            'rain_mm': 10921.75,
            'rain2_mm': 10921.75,
            'mic': 'CRC',
        },
    )

    @staticmethod
    def parse_json(obj):
        sensor_id = obj.get('id')
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['rain_total'] = Packet.get_float(obj, 'rain_mm')
        pkt['rain2_total'] = Packet.get_float(obj, 'rain2_mm')
        pkt['battery'] = Packet.get_battery(obj)
        pkt = Packet.add_identifiers(pkt, sensor_id, LaCrosseLTVR3Packet.__name__)
        return pkt
