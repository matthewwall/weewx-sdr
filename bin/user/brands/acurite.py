import re

import weewx
import weewx.units

from ..log import loginf
from ..packet import Packet
from ..units import to_F, to_in, to_mph


class Acurite(object):
    @staticmethod
    def insert_ids(pkt, pkt_type):
        # there should be a sensor_id field in the packet to identify sensor.
        # ensure the sensor_id is upper-case - it should be 4 hex characters.
        sensor_id = str(pkt.pop('hardware_id', '0000')).upper()
        return Packet.add_identifiers(pkt, sensor_id, pkt_type)


class AcuriteAtlasPacket(Packet):
    IDENTIFIER = 'Acurite-Atlas'
    # for battery, 0 means OK (assuming that 1 for battery_ok means OK)
    # message types: 37, 38, 39
    #   37: wind_avg_mi_h, temperature_F, humidity
    #   38: wind_avg_mi_h, wind_dir_deg, rain_in
    #   39: wind_avg_mi_h, uv, lux
    EXAMPLES = (
        {
            'time': '2019-12-14 16:56:57',
            'model': 'Acurite-Atlas',
            'id': 896,
            'channel': 'A',
            'sequence_num': 0,
            'battery_ok': 1,
            'message_type': 37,
            'wind_avg_mi_h': 5.000,
            'temperature_F': 40.000,
            'humidity': 76,
            'byte8': 0,
            'byte9': 37,
            'byte89': 37,
        },
        {
            'time': '2019-12-14 16:57:58',
            'model': 'Acurite-Atlas',
            'id': 896,
            'channel': 'A',
            'sequence_num': 0,
            'battery_ok': 1,
            'message_type': 39,
            'wind_avg_mi_h': 6.000,
            'uv': 0,
            'lux': 22900,
            'byte8': 0,
            'byte9': 37,
            'byte89': 37,
        },
        {
            'time': '2019-12-14 16:57:07',
            'model': 'Acurite-Atlas',
            'id': 896,
            'channel': 'A',
            'sequence_num': 0,
            'battery_ok': 1,
            'message_type': 38,
            'wind_avg_mi_h': 6.000,
            'wind_dir_deg': 291.000,
            'rain_in': 0.290,
            'byte8': 0,
            'byte9': 37,
            'byte89': 37,
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['usUnits'] = weewx.US
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['model'] = obj.get('model')
        pkt['hardware_id'] = '%04x' % obj.get('id', 0)
        pkt['channel'] = obj.get('channel')
        pkt['sequence_num'] = Packet.get_int(obj, 'sequence_num')
        pkt['message_type'] = Packet.get_int(obj, 'message_type')
        if 'humidity' in obj:
            pkt['humidity'] = Packet.get_float(obj, 'humidity')
        if 'temperature_F' in obj:
            pkt['temperature'] = Packet.get_float(obj, 'temperature_F')
        elif 'temperature_C' in obj:
            pkt['temperature'] = to_F(Packet.get_float(obj, 'temperature_C'))
        if 'wind_avg_mi_h' in obj:
            pkt['wind_speed'] = Packet.get_float(obj, 'wind_avg_mi_h')
        elif 'wind_avg_km_h' in obj:
            pkt['wind_speed'] = to_mph(Packet.get_float(obj, 'wind_avg_km_h'))
        if 'wind_dir_deg' in obj:
            pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
        if 'rain_in' in obj:
            pkt['rain_total'] = Packet.get_float(obj, 'rain_in')
        elif 'rain_mm' in obj:
            pkt['rain_total'] = to_in(Packet.get_float(obj, 'rain_mm'))
        if 'uv' in obj:
            pkt['uv'] = Packet.get_int(obj, 'uv')
        if 'lux' in obj:
            pkt['lux'] = Packet.get_int(obj, 'lux')
        if 'strike_count' in obj:
            pkt['strike_count'] = Packet.get_int(obj, 'strike_count')
        if 'strike_distance' in obj:
            pkt['strike_distance'] = Packet.get_int(obj, 'strike_distance')
        if 'snr' in obj:
            pkt['snr'] = obj.get('snr')
        if 'rssi' in obj:
            pkt['rssi'] = obj.get('rssi')
        if 'noise' in obj:
            pkt['noise'] = obj.get('noise')
        pkt['battery'] = Packet.get_battery(obj)
        return Acurite.insert_ids(pkt, AcuriteAtlasPacket.__name__)


class Acurite3n1PacketV2(Packet):
    IDENTIFIER = 'Acurite-3n1'
    # sample json output from rtl_433
    EXAMPLES = (
        {
            'time': '2021-12-27 02:53:38',
            'model': 'Acurite-3n1',
            'subtype': 32,
            'id': 7220,
            'channel': 'B',
            'sequence_num': 1,
            'battery_ok': 1,
            'wind_avg_mi_h': 5.000,
            'temperature_F': 5.100,
            'humidity': 65,
            'mic': 'CHECKSUM',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['usUnits'] = weewx.US
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['model'] = obj.get('model')
        pkt['hardware_id'] = '%04x' % obj.get('id', 0)
        pkt['channel'] = obj.get('channel')
        pkt['sequence_num'] = Packet.get_int(obj, 'sequence_num')
        pkt['battery'] = Packet.get_battery(obj)
        if 'subtype' in obj:
            pkt['msg_type'] = Packet.get_int(obj, 'subtype')
        elif 'message_type' in obj:
            pkt['msg_type'] = Packet.get_int(obj, 'message_type')
        if 'humidity' in obj:
            pkt['humidity'] = Packet.get_float(obj, 'humidity')
        if 'temperature_F' in obj:
            pkt['temperature'] = Packet.get_float(obj, 'temperature_F')
        elif 'temperature_C' in obj:
            pkt['temperature'] = to_F(Packet.get_float(obj, 'temperature_C'))
        if 'wind_avg_mi_h' in obj:
            pkt['wind_speed'] = Packet.get_float(obj, 'wind_avg_mi_h')
        elif 'wind_avg_km_h' in obj:
            pkt['wind_speed'] = to_mph(Packet.get_float(obj, 'wind_avg_km_h'))
        return Acurite.insert_ids(pkt, Acurite3n1PacketV2.__name__)


class Acurite5n1Packet(Packet):
    #
    # the 'rain fall since last reset' seems to be emitted once when rtl_433
    # starts up, then never again.  the rain measure in the type 31 messages
    # is a cumulative value, but not the same as rain since last reset.
    #
    # rtl_433 keeps using different labels and calculations for the rain
    # counter, so try to deal with the variants we have seen.

    IDENTIFIER = 'Acurite 5n1 sensor'
    PATTERN = re.compile('0x([0-9a-fA-F]+) Ch ([A-C]), (.*)')
    RAIN = re.compile(r'Total rain fall since last reset: ([\d.]+)')
    MSG = re.compile(r'Msg (\d+), (.*)')
    MSG31 = re.compile(r'Wind ([\d.]+) kmph / ([\d.]+) mph ([\d.]+).*rain gauge ([\d.]+) in')
    MSG38 = re.compile(r'Wind ([\d.]+) kmph / ([\d.]+) mph, ([\d.-]+) C ([\d.-]+) F ([\d.]+) % RH')

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        m = Acurite5n1Packet.PATTERN.search(lines[0])
        if m:
            pkt['dateTime'] = ts
            pkt['usUnits'] = weewx.METRIC
            pkt['hardware_id'] = m.group(1)
            pkt['channel'] = m.group(2)
            payload = m.group(3)
            m = Acurite5n1Packet.MSG.search(payload)
            if m:
                msg_type = m.group(1)
                payload = m.group(2)
                if msg_type == '31':
                    m = Acurite5n1Packet.MSG31.search(payload)
                    if m:
                        pkt['wind_speed'] = float(m.group(1))
                        pkt['wind_speed_mph'] = float(m.group(2))
                        pkt['wind_dir'] = float(m.group(3))
                        pkt['rain_total'] = float(m.group(4))
                    else:
                        loginf("Acurite5n1Packet: no match for type 31: '%s'" % payload)
                elif msg_type == '38':
                    m = Acurite5n1Packet.MSG38.search(payload)
                    if m:
                        pkt['wind_speed'] = float(m.group(1))
                        pkt['wind_speed_mph'] = float(m.group(2))
                        pkt['temperature'] = float(m.group(3))
                        pkt['temperature_F'] = float(m.group(4))
                        pkt['humidity'] = float(m.group(5))
                    else:
                        loginf("Acurite5n1Packet: no match for type 38: '%s'" % payload)
                else:
                    loginf(
                        'Acurite5n1Packet: unknown message type %s'
                        " in line '%s'" % (msg_type, lines[0])
                    )
            else:
                m = Acurite5n1Packet.RAIN.search(payload)
                if m:
                    total = float(m.group(1))
                    pkt['rain_since_reset'] = total
                    loginf('Acurite5n1Packet: rain since reset: %s' % total)
                else:
                    loginf("Acurite5n1Packet: unknown message format: '%s'" % lines[0])
        else:
            loginf("Acurite5n1Packet: unrecognized data: '%s'" % lines[0])
        lines.pop(0)
        return Acurite.insert_ids(pkt, Acurite5n1Packet.__name__)

    # sample json output from rtl_433 as of jan2017
    # some changes to rtl_433 as of dec2017
    # more changes to rtl_433 as of dec2018
    EXAMPLES = (
        {
            'time': '2017-01-16 02:34:12',
            'model': 'Acurite 5n1 sensor',
            'sensor_id': 3066,
            'channel': 'C',
            'sequence_num': 1,
            'battery': 'OK',
            'message_type': 49,
            'wind_speed': 0.000,
            'wind_dir_deg': 67.500,
            'wind_dir': 'ENE',
            'rainfall_accumulation': 0.000,
            'raincounter_raw': 8978,
        },
        {
            'time': '2017-01-16 02:37:33',
            'model': 'Acurite 5n1 sensor',
            'sensor_id': 3066,
            'channel': 'C',
            'sequence_num': 1,
            'battery': 'OK',
            'message_type': 56,
            'wind_speed': 0.000,
            'temperature_F': 27.500,
            'humidity': 56,
        },
        {
            'time': '2017-12-24 02:07:00',
            'model': 'Acurite 5n1 sensor',
            'sensor_id': 2662,
            'channel': 'A',
            'sequence_num': 2,
            'battery': 'OK',
            'message_type': 56,
            'wind_speed_mph': 0.000,
            'temperature_F': 47.500,
            'humidity': 74,
        },
        {
            'time': '2017-12-24 02:07:18',
            'model': 'Acurite 5n1 sensor',
            'sensor_id': 2662,
            'channel': 'A',
            'sequence_num': 2,
            'battery': 'OK',
            'message_type': 49,
            'wind_speed_mph': 0.000,
            'wind_dir_deg': 157.500,
            'wind_dir': 'SSE',
            'rainfall_accumulation_inch': 0.000,
            'raincounter_raw': 421,
        },
        {
            'time': '2019-01-04 02:37:10',
            'model': 'Acurite 5n1 sensor',
            'sensor_id': 2662,
            'channel': 'A',
            'sequence_num': 1,
            'battery': 'OK',
            'message_type': 56,
            'wind_speed_kph': 0.000,
            'temperature_F': 42.400,
            'humidity': 83,
        },
        {
            'time': '2019-01-04 02:37:28',
            'model': 'Acurite 5n1 sensor',
            'sensor_id': 2662,
            'channel': 'A',
            'sequence_num': 0,
            'battery': 'LOW',
            'message_type': 49,
            'wind_speed_kph': 0.000,
            'wind_dir_deg': 180.000,
            'rain_inch': 28.970,
        },
    )
    TEXT_EXAMPLES = (
        (
            '2016-08-31 16:41:39 Acurite 5n1 sensor 0x0BFA Ch C, Msg 31, Wind 15 kmph / 9.3 mph '
            '270.0^ W (3), rain gauge 0.00 in',
        ),
        (
            '2016-08-30 23:57:25 Acurite 5n1 sensor 0x0BFA Ch C, Msg 38, Wind 2 kmph / 1.2 mph, '
            '21.3 C 70.3 F 70 % RH',
        ),
        (
            '2016-09-27 17:09:34 Acurite 5n1 sensor 0x062C Ch A, Total rain fall since last reset: '
            '2.00',
        ),
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.US
        pkt['hardware_id'] = '%04x' % obj.get('sensor_id', 0)
        pkt['channel'] = obj.get('channel')
        pkt['battery'] = Packet.get_battery(obj)
        pkt['status'] = obj.get('status')
        msg_type = obj.get('message_type')
        if msg_type == 49:  # 0x31
            pkt['wind_speed'] = Acurite5n1Packet.get_wind_speed(obj)
            pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
            pkt['rain_total'] = Acurite5n1Packet.get_rain_total(obj)
        elif msg_type == 56:  # 0x38
            pkt['wind_speed'] = Acurite5n1Packet.get_wind_speed(obj)
            pkt['temperature'] = Packet.get_float(obj, 'temperature_F')
            pkt['humidity'] = Packet.get_float(obj, 'humidity')
        return Acurite.insert_ids(pkt, Acurite5n1Packet.__name__)

    @staticmethod
    def get_wind_speed(obj):
        ws = None
        if 'wind_speed_mph' in obj:
            ws = Packet.get_float(obj, 'wind_speed_mph')
        if 'wind_speed_kph' in obj:
            ws = Packet.get_float(obj, 'wind_speed_kph')
            if ws is not None:
                ws = weewx.units.kph_to_mph(ws)
        return ws

    @staticmethod
    def get_rain_total(obj):
        rain_total = None
        if 'raincounter_raw' in obj:
            rain_counter = Packet.get_int(obj, 'raincounter_raw')
            # put some units on the rain total - each tip is 0.01 inch
            if rain_counter is not None:
                rain_total = rain_counter * 0.01  # inch
        elif 'rain_inch' in obj:
            rain_total = Packet.get_float(obj, 'rain_inch')
        return rain_total


class Acurite5n1PacketV2(Packet):
    # Based on Acurite5n1Packet class, but implemented for unsupported format
    IDENTIFIER = 'Acurite-5n1'
    # sample json output from rtl_433
    EXAMPLES = (
        {
            'time': '2019-07-29 07:46:22.482883',
            'protocol': 40,
            'model': 'Acurite-5n1',
            'id': 1234,
            'channel': 'B',
            'sequence_num': 1,
            'battery_ok': 1,
            'message_type': 56,
            'wind_avg_km_h': 0.000,
            'temperature_C': 20.500,
            'humidity': 93,
            'mod': 'ASK',
            'freq': 433.934,
            'rssi': -1.719,
            'snr': 24.404,
            'noise': -26.124,
        },
        {
            'time': '2020-02-05 02:20:54',
            'model': 'Acurite-5n1',
            'subtype': 56,
            'id': 956,
            'channel': 'A',
            'sequence_num': 2,
            'battery_ok': 1,
            'wind_avg_km_h': 3.483,
            'temperature_F': 31.300,
            'humidity': 66,
        },
        {
            'time': '2020-10-26 22:09:12',
            'model': 'Acurite-5n1',
            'message_type': 49,
            'id': 2662,
            'channel': 'A',
            'sequence_num': 0,
            'battery_ok': 1,
            'wind_avg_km_h': 15.900,
            'wind_dir_deg': 337.500,
            'rain_in': 7.290,
            'mic': 'CHECKSUM',
        },
        {
            'time': '2020-10-26 22:08:54',
            'model': 'Acurite-5n1',
            'message_type': 56,
            'id': 2662,
            'channel': 'A',
            'sequence_num': 2,
            'battery_ok': 1,
            'wind_avg_km_h': 9.278,
            'temperature_F': 76.100,
            'humidity': 15,
            'mic': 'CHECKSUM',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['usUnits'] = weewx.US
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['protocol'] = Packet.get_int(obj, 'protocol')
        pkt['model'] = obj.get('model')
        pkt['hardware_id'] = '%04x' % obj.get('id', 0)
        pkt['channel'] = obj.get('channel')
        pkt['sequence_num'] = Packet.get_int(obj, 'sequence_num')
        pkt['battery'] = Packet.get_battery(obj)
        # connection diagnostics depend on the version of rtl_433
        pkt['mod'] = obj.get('mod')  # apparently is ASK
        pkt['freq'] = Packet.get_float(obj, 'freq')
        pkt['rssi'] = Packet.get_float(obj, 'rssi')
        pkt['snr'] = Packet.get_float(obj, 'snr')
        pkt['noise'] = Packet.get_float(obj, 'noise')
        # the label for message type has changed in rtl_433
        if 'subtype' in obj:
            pkt['msg_type'] = Packet.get_int(obj, 'subtype')
        elif 'message_type' in obj:
            pkt['msg_type'] = Packet.get_int(obj, 'message_type')
        # each message type contains different information.  units vary
        # depending on the rtl_433 configuration, so be ready for anything.
        #   49 has wind_speed, wind_dir, and rain
        #   56 has wind_speed, temperature, humidity
        if 'wind_avg_km_h' in obj:
            pkt['wind_speed'] = to_mph(Packet.get_float(obj, 'wind_avg_km_h'))
        if 'wind_dir_deg' in obj:
            pkt['wind_dir'] = Packet.get_float(obj, 'wind_dir_deg')
        if 'rain_in' in obj:
            pkt['rain_total'] = Packet.get_float(obj, 'rain_in')
        elif 'rain_mm' in obj:
            pkt['rain_total'] = to_in(Packet.get_float(obj, 'rain_mm'))
        if 'temperature_F' in obj:
            pkt['temperature'] = Packet.get_float(obj, 'temperature_F')
        elif 'temperature_C' in obj:
            pkt['temperature'] = to_F(Packet.get_float(obj, 'temperature_C'))
        if 'humidity' in obj:
            pkt['humidity'] = Packet.get_float(obj, 'humidity')
        return Acurite.insert_ids(pkt, Acurite5n1PacketV2.__name__)


class AcuriteTowerPacket(Packet):
    # initial implementation was single-line
    #
    # multi-line was introduced nov2016 - only single line is supported here
    # 2017-01-12 02:55:10 : Acurite tower sensor : 12391 : B
    # Temperature: 18.0 C
    # Humidity: 68
    # Battery: 0
    # : 68

    IDENTIFIER = 'Acurite tower sensor'
    PATTERN = re.compile(r'0x([0-9a-fA-F]+) Ch ([A-C]): ([\d.-]+) C ([\d.-]+) F ([\d]+) % RH')

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        m = AcuriteTowerPacket.PATTERN.search(lines[0])
        if m:
            pkt['dateTime'] = ts
            pkt['usUnits'] = weewx.METRIC
            pkt['hardware_id'] = m.group(1)
            pkt['channel'] = m.group(2)
            pkt['temperature'] = float(m.group(3))
            pkt['temperature_F'] = float(m.group(4))
            pkt['humidity'] = float(m.group(5))
            pkt = Acurite.insert_ids(pkt, AcuriteTowerPacket.__name__)
        else:
            loginf("AcuriteTowerPacket: unrecognized data: '%s'" % lines[0])
        lines.pop(0)
        return pkt

    # JSON format as of mid-2018
    EXAMPLES = (
        {
            'time': '2018-07-21 01:53:56',
            'model': 'Acurite tower sensor',
            'id': 13009,
            'sensor_id': 13009,
            'channel': 'A',
            'temperature_C': 15.000,
            'humidity': 16,
            'battery_low': 1,
        },
        {
            'time': '2018-07-21 01:52:24',
            'model': 'Acurite tower sensor',
            'id': 13009,
            'sensor_id': 13009,
            'channel': 'A',
            'temperature_C': 15.600,
            'humidity': 16,
            'battery_low': 0,
        },
        # JSON format as of early 2017
        {
            'time': '2017-01-12 03:43:05',
            'model': 'Acurite tower sensor',
            'id': 521,
            'channel': 'A',
            'temperature_C': 0.800,
            'humidity': 68,
            'battery': 0,
            'status': 68,
        },
        {
            'time': '2017-01-12 03:43:11',
            'model': 'Acurite tower sensor',
            'id': 5585,
            'channel': 'C',
            'temperature_C': 21.100,
            'humidity': 32,
            'battery': 0,
            'status': 68,
        },
    )
    TEXT_EXAMPLES = (
        ('2016-08-30 23:57:20 Acurite tower sensor 0x37FC Ch A: 26.7 C 80.1 F 16 % RH',),
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.US
        pkt['hardware_id'] = '%04x' % obj.get('id', 0)
        pkt['channel'] = obj.get('channel')
        pkt['battery'] = Packet.get_battery(obj)
        pkt['status'] = obj.get('status')
        if 'temperature_F' in obj:
            pkt['temperature'] = Packet.get_float(obj, 'temperature_F')
        elif 'temperature_C' in obj:
            pkt['temperature'] = to_F(Packet.get_float(obj, 'temperature_C'))
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        return Acurite.insert_ids(pkt, AcuriteTowerPacket.__name__)


class AcuriteTowerPacketV2(Packet):
    # Based on AcuriteTowerPacket type, but implemented for unsupported format
    IDENTIFIER = 'Acurite-Tower'
    # Sample data:
    EXAMPLES = (
        {
            'time': '2019-07-29 07:44:23.005624',
            'protocol': 40,
            'model': 'Acurite-Tower',
            'id': 1234,
            'sensor_id': 1234,
            'channel': 'A',
            'temperature_C': 22.600,
            'humidity': 45,
            'battery_ok': 0,
            'mod': 'ASK',
            'freq': 433.938,
            'rssi': -0.134,
            'snr': 14.391,
            'noise': -14.525,
        },
        {
            'time': '2021-12-20 20:00:59',
            'model': 'Acurite-Tower',
            'id': 11041,
            'channel': 'B',
            'battery_ok': 1,
            'temperature_C': -3.500,
            'humidity': 71,
            'mic': 'CHECKSUM',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['usUnits'] = weewx.US
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['protocol'] = Packet.get_int(obj, 'protocol')  # 40
        pkt['model'] = obj.get('model')  # model = Acurite-Tower
        pkt['hardware_id'] = '%04x' % obj.get('id', 0)
        pkt['sensor_id'] = '%04x' % obj.get('sensor_id', 0)
        pkt['channel'] = obj.get('channel')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        if 'temperature_F' in obj:
            pkt['temperature'] = Packet.get_float(obj, 'temperature_F')
        elif 'temperature_C' in obj:
            pkt['temperature'] = to_F(Packet.get_float(obj, 'temperature_C'))
        pkt['battery'] = Packet.get_battery(obj)
        pkt['mod'] = obj.get('mod')  # apparently mod = ASK
        pkt['freq'] = Packet.get_float(obj, 'freq')
        pkt['rssi'] = Packet.get_float(obj, 'rssi')
        pkt['snr'] = Packet.get_float(obj, 'snr')
        pkt['noise'] = Packet.get_float(obj, 'noise')
        return Acurite.insert_ids(pkt, AcuriteTowerPacketV2.__name__)


class Acurite606TXPacket(Packet):
    IDENTIFIER = 'Acurite 606TX Sensor'
    # 2017-03-20: Acurite 606TX Temperature Sensor
    EXAMPLES = (
        {
            'time': '2017-03-04 16:18:12',
            'model': 'Acurite 606TX Sensor',
            'id': 48,
            'battery': 'OK',
            'temperature_C': -1.100,
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.US
        sensor_id = obj.get('id')
        if 'temperature_F' in obj:
            pkt['temperature'] = Packet.get_float(obj, 'temperature_F')
        elif 'temperature_C' in obj:
            pkt['temperature'] = to_F(Packet.get_float(obj, 'temperature_C'))
        pkt['battery'] = Packet.get_battery(obj)
        pkt = Packet.add_identifiers(pkt, sensor_id, Acurite606TXPacket.__name__)
        return pkt


class Acurite606TXPacketV2(Packet):
    IDENTIFIER = 'Acurite-606TX'
    # 2021-02-23: Acurite 606TX Temperature Sensor
    EXAMPLES = (
        {
            'time': '2021-02-23 16:24:07',
            'model': 'Acurite-606TX',
            'id': 153,
            'battery_ok': 1,
            'temperature_C': 18.800,
            'mic': 'CHECKSUM',
        },
        {
            'time': '2021-10-26 23:39:49',
            'model': 'Acurite-606TX',
            'id': 194,
            'battery_ok': 1,
            'temperature_C': 19.200,
            'mic': 'CHECKSUM',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.US
        sensor_id = obj.get('id')
        if 'temperature_F' in obj:
            pkt['temperature'] = Packet.get_float(obj, 'temperature_F')
        elif 'temperature_C' in obj:
            pkt['temperature'] = to_F(Packet.get_float(obj, 'temperature_C'))
        pkt['battery'] = Packet.get_battery(obj)
        pkt = Packet.add_identifiers(pkt, sensor_id, Acurite606TXPacketV2.__name__)
        return pkt


class AcuriteRain899Packet(Packet):
    IDENTIFIER = 'Acurite-Rain899'
    # Sample data:
    EXAMPLES = (
        {
            'time': '2019-12-05 16:32:20',
            'model': 'Acurite-Rain899',
            'id': 1699,
            'channel': 0,
            'battery_ok': 0,
            'rain_mm': 6.096,
        },
        {
            'time': '2019-12-05 16:32:20',
            'model': 'Acurite-Rain899',
            'id': 1699,
            'channel': 0,
            'battery_ok': 0,
            'rain_mm': 6.096,
        },
        {
            'time': '2019-12-05 16:32:20',
            'model': 'Acurite-Rain899',
            'id': 1699,
            'channel': 0,
            'battery_ok': 0,
            'rain_mm': 6.096,
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['usUnits'] = weewx.US
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['model'] = obj.get('model')
        pkt['hardware_id'] = '%04x' % obj.get('id', 0)
        pkt['channel'] = obj.get('channel')
        pkt['battery'] = Packet.get_battery(obj)
        if 'rain_mm' in obj:
            pkt['rain_total'] = to_in(Packet.get_float(obj, 'rain_mm'))
        return Acurite.insert_ids(pkt, AcuriteRain899Packet.__name__)


class Acurite986Packet(Packet):
    # The 986 hardware_id changes, so using the 2F and 1R as the hardware
    # identifer.  As long as you only have one set of sendors and your
    # close neighbors have none.

    # Older releases of rtl_433 used 'Acurite 986 sensor', while recent
    # versions use 'Acurite 986 Sensor'.  So we try to be compatible by
    # matching on the least that we can.

    # IDENTIFIER = "Acurite 986 sensor"
    # IDENTIFIER = "Acurite 986 Sensor"
    IDENTIFIER = 'Acurite-986'

    EXAMPLES = (
        {
            'time': '2018-04-22 18:01:03',
            'model': 'Acurite 986 Sensor',
            'id': 43248,
            'channel': '1R',
            'temperature_F': 69,
            'battery': 'OK',
            'status': 0,
        },
        {
            'time': '2020-10-19 07:00:32',
            'model': 'Acurite-986',
            'id': 9534,
            'channel': '2F',
            'battery_ok': 1,
            'temperature_F': -10.000,
            'status': 0,
            'mic': 'CRC',
        },
    )
    TEXT_EXAMPLES = (
        ('2016-10-31 15:24:29 Acurite 986 sensor 0x2c87 - 2F: 16.7 C 62 F',),
        ('2016-10-31 15:23:54 Acurite 986 sensor 0x85ed - 1R: 16.7 C 62 F',),
    )

    PATTERN = re.compile(r'0x([0-9a-fA-F]+) - (1R|2F): ([\d.-]+) C ([\d.-]+) F')

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        m = Acurite986Packet.PATTERN.search(lines[0])
        if m:
            pkt['dateTime'] = ts
            pkt['usUnits'] = weewx.METRIC
            pkt['hardware_id'] = m.group(1)
            pkt['channel'] = m.group(2)
            pkt['temperature'] = float(m.group(3))
            pkt['temperature_F'] = float(m.group(4))
        else:
            loginf("Acurite986Packet: unrecognized data: '%s'" % lines[0])
        lines.pop(0)
        return Acurite.insert_ids(pkt, Acurite986Packet.__name__)

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['hardware_id'] = obj.get('id', 0)
        pkt['channel'] = obj.get('channel')
        pkt['battery'] = Packet.get_battery(obj)
        if 'temperature_F' in obj:
            pkt['usUnits'] = weewx.US
            pkt['temperature'] = Packet.get_float(obj, 'temperature_F')
        else:
            pkt['usUnits'] = weewx.METRIC
            pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        return Acurite.insert_ids(pkt, Acurite986Packet.__name__)


class AcuriteLightningPacket(Packet):
    # with rtl_433 update of 19mar2017

    # pre-19mar2017

    # April 21, 2018 - JSON support

    #    IDENTIFIER = "Acurite lightning"
    #    IDENTIFIER = "Acurite Lightning 6045M"
    IDENTIFIER = 'Acurite-6045M'

    EXAMPLES = (
        {
            'time': '2018-04-21 19:12:53',
            'model': 'Acurite Lightning 6045M',
            'id': 151,
            'channel': 'C',
            'temperature_F': 66.900,
            'humidity': 33,
            'strike_count': 47,
            'storm_dist': 12,
            'active': 1,
            'rfi': 0,
            'ussb1': 1,
            'battery': 'LOW',
            'exception': 0,
            'raw_msg': '0097af2150f9afcc2b',
        },
        {
            'time': '2020-10-13 22:49:34',
            'model': 'Acurite-6045M',
            'id': 15431,
            'channel': 'A',
            'battery_ok': 0,
            'temperature_F': 91.800,
            'humidity': 21,
            'strike_count': 171,
            'storm_dist': 12,
            'active': 1,
            'rfi': 0,
            'exception': 0,
            'raw_msg': 'fc47af95d2de55cc58',
        },
    )
    TEXT_EXAMPLES = (
        (
            '2017-03-19 16:48:31 Acurite lightning 0x976F Ch A Msg Type 0x02: 66.2 F 25 % RH '
            'Strikes 1 Distance 0 L_status 0x02 - c0 97* 6f  99  50  72  81  c0  62*',
        ),
        (
            '2017-03-19 16:48:47 Acurite lightning 0x976F Ch A Msg Type 0x02: 66.2 F 25 % RH '
            'Strikes 1 Distance 0 L_status 0x02 - c0  97* 6f  99  50  72  81  c0  62*',
        ),
        (
            '2016-11-04 04:34:58 Acurite lightning 0x536F Ch A Msg Type 0x51: 15 C 58 % RH Strikes '
            '50 Distance 69 - c0  53  6f  3a  d1  0f  b2  c5  13*',
        ),
        (
            '2016-11-04 04:43:14 Acurite lightning 0x536F Ch A Msg Type 0x51: 15 C 58 % RH Strikes '
            '55 Distance 5 - c0  53  6f  3a  d1  0f  b7  05  58*',
        ),
        (
            '2016-11-04 04:43:22 Acurite lightning 0x536F Ch A Msg Type 0x51: 15 C 58 % RH Strikes '
            '55 Distance 69 - c0  53  6f  3a  d1  0f  b7  c5  18',
        ),
        (
            '2017-01-16 02:37:39 Acurite lightning 0x526F Ch A Msg Type 0x11: 67 C 38 % RH Strikes '
            '47 Distance 81 - dd  52* 6f  a6  11  c3  af  d1  98*',
        ),
    )

    PATTERN = re.compile(
        r'0x([0-9a-fA-F]+) Ch (.) Msg Type 0x([0-9a-fA-F]+): '
        r'([\d.-]+) ([CF]) ([\d.]+) % RH Strikes ([\d]+) Distance ([\d.]+)'
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.US
        pkt['channel'] = obj.get('channel')
        pkt['hardware_id'] = '%04x' % obj.get('id', 0)
        pkt['temperature'] = obj.get('temperature_F')
        pkt['battery'] = Packet.get_battery(obj)
        pkt['humidity'] = obj.get('humidity')
        pkt['active'] = obj.get('active')
        pkt['rfi'] = obj.get('rfi')
        pkt['exception'] = obj.get('exception')
        pkt['strikes_total'] = obj.get('strike_count')
        pkt['distance'] = obj.get('storm_dist')
        return Acurite.insert_ids(pkt, AcuriteLightningPacket.__name__)

    @staticmethod
    def parse_text(ts, payload, lines):
        pkt = dict()
        m = AcuriteLightningPacket.PATTERN.search(lines[0])
        if m:
            pkt['dateTime'] = ts
            units = m.group(5)
            if units == 'C':
                pkt['usUnits'] = weewx.METRIC
            else:
                pkt['usUnits'] = weewx.US
            pkt['hardware_id'] = m.group(1)
            pkt['channel'] = m.group(2)
            pkt['msg_type'] = m.group(3)
            pkt['temperature'] = float(m.group(4))
            pkt['humidity'] = float(m.group(6))
            pkt['strikes_total'] = float(m.group(7))
            pkt['distance'] = float(m.group(8))
        else:
            loginf('AcuriteLightningPacket: unrecognized data: %s' % lines[0])
        lines.pop(0)
        return Acurite.insert_ids(pkt, AcuriteLightningPacket.__name__)


class Acurite00275MPacket(Packet):
    IDENTIFIER = '00275rm'

    EXAMPLES = (
        {
            'time': '2017-03-09 21:59:11',
            'model': '00275rm',
            'probe': 2,
            'id': 3942,
            'battery': 'OK',
            'temperature_C': 23.300,
            'humidity': 34,
            'ptemperature_C': 22.700,
            'crc': 'ok',
        },
        {
            'time': '2017-03-09 21:59:11',
            'model': '00275rm',
            'probe': 2,
            'id': 3942,
            'battery': 'OK',
            'temperature_C': 23.300,
            'humidity': 34,
            'temperature_1_C': 22.700,
            'crc': 'ok',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['hardware_id'] = '%04x' % obj.get('id', 0)
        pkt['probe'] = obj.get('probe')
        pkt['battery'] = Packet.get_battery(obj)
        if 'temperature_1_C' in obj:
            pkt['temperature_probe'] = Packet.get_float(obj, 'temperature_1_C')
        else:
            pkt['temperature_probe'] = Packet.get_float(obj, 'ptemperature_C')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        return Acurite.insert_ids(pkt, Acurite00275MPacket.__name__)


class AcuriteWT450Packet(Packet):
    IDENTIFIER = 'WT450 sensor'

    EXAMPLES = (
        {
            'time': '2017-09-14 20:24:43',
            'model': 'WT450 sensor',
            'id': 1,
            'channel': 2,
            'battery': 'OK',
            'temperature_C': 25.090,
            'humidity': 49,
        },
        {
            'time': '2017-09-14 20:24:44',
            'model': 'WT450 sensor',
            'id': 1,
            'channel': 2,
            'battery': 'OK',
            'temperature_C': 25.110,
            'humidity': 49,
        },
        {
            'time': '2017-09-14 20:24:44',
            'model': 'WT450 sensor',
            'id': 1,
            'channel': 2,
            'battery': 'OK',
            'temperature_C': 25.120,
            'humidity': 49,
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['sid'] = Packet.get_int(obj, 'id')
        pkt['channel'] = Packet.get_int(obj, 'channel')
        pkt['battery'] = Packet.get_battery(obj)
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        _id = '%s:%s' % (pkt['sid'], pkt['channel'])
        return Packet.add_identifiers(pkt, _id, AcuriteWT450Packet.__name__)


class Acurite515Packet(Packet):
    IDENTIFIER = 'Acurite-515'
    # refrigerator (XR) and freezer (XF) sensors
    # X is one of A, B, or C
    EXAMPLES = (
        {
            'time': '2022-01-21 21:55:54',
            'model': 'Acurite-515',
            'id': 2375,
            'channel': 'BR',
            'battery_ok': 1,
            'temperature_F': 47.6,
            'mic': 'CHECKSUM',
        },
        {
            'time': '2022-01-21 21:55:44',
            'model': 'Acurite-515',
            'id': 78,
            'channel': 'BF',
            'battery_ok': 1,
            'temperature_F': 47.1,
            'mic': 'CHECKSUM',
        },
    )

    @staticmethod
    def parse_json(obj):
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.US
        pkt['hardware_id'] = '%04x' % obj.get('id', 0)
        pkt['channel'] = Packet.get_int(obj, 'channel')
        pkt['battery'] = Packet.get_battery(obj)
        if 'temperature_F' in obj:
            pkt['temperature'] = Packet.get_float(obj, 'temperature_F')
        elif 'temperature_C' in obj:
            pkt['temperature'] = to_F(Packet.get_float(obj, 'temperature_C'))
        return Acurite.insert_ids(pkt, Acurite515Packet.__name__)
