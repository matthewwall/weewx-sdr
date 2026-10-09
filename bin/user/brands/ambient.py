import re

import weewx

from ..packet import Packet


class AmbientF007THPacket(Packet):
    #    IDENTIFIER = "Ambient Weather F007TH Thermo-Hygrometer"
    IDENTIFIER = 'Ambientweather-F007TH'
    PARSEINFO = {
        'House Code': ['house_code', None, lambda x: int(x)],
        'Channel': ['channel', None, lambda x: int(x)],
        'Temperature': ['temperature', re.compile(r'([\d.-]+) F'), lambda x: float(x)],
        'Humidity': ['humidity', re.compile(r'([\d.]+) %'), lambda x: float(x)],
    }

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        pkt['dateTime'] = ts
        pkt['usUnits'] = weewx.METRIC
        pkt.update(Packet.parse_lines(lines, AmbientF007THPacket.PARSEINFO))
        house_code = pkt.pop('house_code', 0)
        channel = pkt.pop('channel', 0)
        sensor_id = '%s:%s' % (channel, house_code)
        pkt = Packet.add_identifiers(pkt, sensor_id, AmbientF007THPacket.__name__)
        return pkt

    # as of 06feb2020:
    EXAMPLES = (
        {
            'time': '2017-01-21 13:01:30',
            'model': 'Ambient Weather F007TH Thermo-Hygrometer',
            'device': 80,
            'channel': 1,
            'temperature_F': 61.800,
            'humidity': 10,
        },
        {
            'time': '2020-02-05 19:33:11',
            'model': 'Ambientweather-F007TH',
            'id': 201,
            'channel': 5,
            'battery_ok': 1,
            'temperature_F': 39.400,
            'humidity': 60,
            'mic': 'CRC',
        },
    )
    TEXT_EXAMPLES = (
        (
            '2017-01-21 18:17:16 : Ambient Weather F007TH Thermo-Hygrometer',
            'House Code: 80',
            'Channel: 1',
            'Temperature: 61.8',
            'Humidity: 13 %',
        ),
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.US
        house_code = obj.get('id', 0)
        channel = obj.get('channel')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_F')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        sensor_id = '%s:%s' % (channel, house_code)
        pkt['battery'] = Packet.get_battery(obj)
        pkt['mod'] = obj.get('mod')
        pkt['freq'] = Packet.get_float(obj, 'freq')
        pkt['rssi'] = Packet.get_float(obj, 'rssi')
        pkt['snr'] = Packet.get_float(obj, 'snr')
        pkt['noise'] = Packet.get_float(obj, 'noise')
        pkt = Packet.add_identifiers(pkt, sensor_id, AmbientF007THPacket.__name__)
        return pkt


class AmbientTX8300Packet(Packet):
    IDENTIFIER = 'AmbientWeather-TX8300'

    EXAMPLES = (
        {
            'time': '2021-06-14 21:38:43',
            'model': 'AmbientWeather-TX8300',
            'id': 116,
            'channel': 1,
            'battery': 2,
            'temperature_C': 28.500,
            'mic': 'CHECKSUM',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        station_id = obj.get('id')
        pkt['channel'] = Packet.get_int(obj, 'channel')
        pkt['battery'] = Packet.get_battery(obj)
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt = Packet.add_identifiers(pkt, station_id, AmbientTX8300Packet.__name__)
        return pkt


class AmbientWH31EPacket(Packet):
    IDENTIFIER = 'AmbientWeather-WH31E'

    EXAMPLES = (
        {
            'time': '2019-02-14 17:24:41.259441',
            'protocol': 113,
            'model': 'AmbientWeather-WH31E',
            'id': 24,
            'channel': 1,
            'battery': 'OK',
            'temperature_C': 6.000,
            'humidity': 42,
            'data': '2f00000000',
            'mic': 'CRC',
            'mod': 'FSK',
            'freq1': 914.984,
            'freq2': 914.906,
            'rssi': -13.328,
            'snr': 13.197,
            'noise': -26.525,
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRICWX
        pkt['station_id'] = obj.get('id')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['battery'] = Packet.get_battery(obj)
        pkt['channel'] = Packet.get_int(obj, 'channel')
        pkt['rssi'] = Packet.get_int(obj, 'rssi')
        pkt['snr'] = Packet.get_float(obj, 'snr')
        pkt['noise'] = Packet.get_float(obj, 'noise')
        return AmbientWH31EPacket.insert_ids(pkt)

    @staticmethod
    def insert_ids(pkt):
        station_id = pkt.pop('station_id', '0000')
        pkt = Packet.add_identifiers(pkt, station_id, AmbientWH31EPacket.__name__)
        return pkt


class AmbientWH31BPacket(Packet):
    IDENTIFIER = 'AmbientWeather-WH31B'

    EXAMPLES = (
        {
            'time': '2024-03-04 17:36:20',
            'model': 'AmbientWeather-WH31B',
            'id': 196,
            'channel': 3,
            'battery_ok': 1,
            'temperature_C': 21.6,
            'humidity': 40,
            'data': 'ea00000000',
            'mic': 'CRC',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRICWX
        pkt['station_id'] = obj.get('id')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['battery'] = Packet.get_battery(obj)
        pkt['channel'] = Packet.get_int(obj, 'channel')
        pkt['rssi'] = Packet.get_int(obj, 'rssi')
        pkt['snr'] = Packet.get_float(obj, 'snr')
        pkt['noise'] = Packet.get_float(obj, 'noise')
        return AmbientWH31BPacket.insert_ids(pkt)

    @staticmethod
    def insert_ids(pkt):
        station_id = pkt.pop('station_id', '0000')
        pkt = Packet.add_identifiers(pkt, station_id, AmbientWH31BPacket.__name__)
        return pkt
