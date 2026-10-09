import weewx

from ..packet import Packet


class EcoWittWH40Packet(Packet):
    IDENTIFIER = 'EcoWitt-WH40'
    # This is for a WH40 rain sensor
    EXAMPLES = (
        {
            'time': '2020-02-05 12:37:05',
            'model': 'EcoWitt-WH40',
            'id': 52591,
            'rain_mm': 0.800,
            'data': '0002ed0000',
            'mic': 'CRC',
        },
    )

    @staticmethod
    def parse_json(obj):
        sensor_id = obj.get('id')
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRICWX
        pkt['rain_total'] = Packet.get_float(obj, 'rain_mm')
        pkt['battery'] = Packet.get_battery(obj)
        pkt['supplyVoltage'] = Packet.get_float(obj, 'battery_V')
        pkt['freq1'] = Packet.get_float(obj, 'freq1')
        pkt['freq2'] = Packet.get_float(obj, 'freq2')
        pkt['rssi'] = Packet.get_float(obj, 'rssi')
        pkt['snr'] = Packet.get_float(obj, 'snr')
        pkt['noise'] = Packet.get_float(obj, 'noise')
        pkt = Packet.add_identifiers(pkt, sensor_id, EcoWittWH40Packet.__name__)
        return pkt


class EcoWittWS68Packet(Packet):
    IDENTIFIER = 'EcoWitt-WS68'
    # This is for a WS68 wind/solar sensor
    EXAMPLES = (
        {
            'time': '2022-09-26 00:47:41',
            'model': 'EcoWitt-WS68',
            'id': 388,
            'battery_raw': 90,
            'battery_ok': 1,
            'lux_raw': 0,
            'wind_avg_raw': 0,
            'wind_max_raw': 0,
            'wind_dir_deg': 157,
            'data': '00 210',
            'mic': 'CRC',
        },
    )

    @staticmethod
    def parse_json(obj):
        sensor_id = obj.get('id')
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRICWX
        pkt['battery'] = Packet.get_battery(obj)
        x = Packet.get_float(obj, 'battery_raw')
        if x is not None:
            pkt['supplyVoltage'] = 2 * x
        pkt['luminosity'] = Packet.get_float(obj, 'lux_raw')
        x = Packet.get_float(obj, 'wind_avg_raw')
        if x is not None:
            pkt['wind_speed'] = x / 10
        x = Packet.get_float(obj, 'wind_max_raw')
        if x is not None:
            pkt['wind_gust'] = x / 10
        pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
        pkt = Packet.add_identifiers(pkt, sensor_id, EcoWittWS68Packet.__name__)
        return pkt
