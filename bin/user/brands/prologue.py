import weewx

from ..packet import Packet


class ProloguePacket(Packet):
    IDENTIFIER = 'Prologue sensor'
    # 2017-03-19 : Prologue Temperature and Humidity Sensor
    EXAMPLES = (
        {
            'time': '2017-03-15 20:14:19',
            'model': 'Prologue sensor',
            'id': 5,
            'rid': 166,
            'channel': 1,
            'battery': 'OK',
            'button': 0,
            'temperature_C': -0.700,
            'humidity': 49,
        },
    )

    @staticmethod
    def parse_json(obj):
        sensor_id = obj.get('rid')
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['battery'] = Packet.get_battery(obj)
        pkt['channel'] = obj.get('channel')
        pkt = Packet.add_identifiers(pkt, sensor_id, ProloguePacket.__name__)
        return pkt


class PrologueTHPacket(Packet):
    IDENTIFIER = 'Prologue-TH'
    # 2021-09-03 : Prologue-TH Temperature and Humidity Sensor
    EXAMPLES = (
        {
            'time': '2021-09-02 23:47:40',
            'model': 'Prologue-TH',
            'subtype': 5,
            'id': 70,
            'channel': 1,
            'battery_ok': 1,
            'temperature_C': 24.8,
            'humidity': 49,
            'button': 0,
        },
    )

    @staticmethod
    def parse_json(obj):
        sensor_id = obj.get('id')
        pkt = dict()
        pkt['dateTime'] = Packet.parse_time(obj.get('time'))
        pkt['usUnits'] = weewx.METRIC
        pkt['model'] = obj.get('model')
        pkt['temperature'] = Packet.get_float(obj, 'temperature_C')
        pkt['humidity'] = Packet.get_float(obj, 'humidity')
        pkt['battery'] = Packet.get_battery(obj)
        pkt['channel'] = obj.get('channel')
        pkt = Packet.add_identifiers(pkt, sensor_id, PrologueTHPacket.__name__)
        return pkt
