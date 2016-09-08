weewx-sdr

This is a driver for weewx that captures data from software-defined radio.
It works with open source rtl sdr software that in turn works with
inexpensive, broad spectrum radio receivers such as the Realtek RTL2838UHIDIR.
These devices cost about 20$US and are capable of receiving radio signals from
weather stations, energy monitors, doorbells, and many other devices that use
unlicensed spectrum such as 433MHz, 838MHz, and 900MHz frequencies.


Hardware

Tested with the Realtek RTL2838UHIDIR.  Should work with any software-defined
radio that is compatible with the rtl-sdr software.  Uses the modules in
rtl_433 to recognize packets.

Output from the following sensors is recognized:

    Acurite tower sensor
    Acurite 5n1 sensor
    Fine Offset WH1080 weather station
    HIDEKI TS04 sensor
    Weather Sensor THGR810
    LaCrosse WS

Output from unrecognized sensors will be emitted to the log when parameter
log_unknown_sensors = 1


Installation

a) install weewx
    http://weewx.com/docs/usersguide.htm
b) install rtl-sdr
    http://sdr.osmocom.org/trac/wiki/rtl-sdr
c) install rtl_433
    https://github.com/merbanan/rtl_433

1) download the driver

wget -O weewx-sdr.zip https://github.com/matthewwall/weewx-sdr/archive/master.zip

2) install the driver

wee_extension --install weewx-sdr.zip

3) configure the driver

wee_config --reconfigure

4) start weewx

sudo /etc/init.d/weewx start


Configuration

The rtl_433 executable emits data for many different types of sensors, some of
which have similar output.  Use the sensor_map to distinguish between sensors
and map the output from rtl_433 to the database fields in weewx.  This is done
in the driver section of weewx.conf.

Here are some examples:

# collect data from Acurite 5n1 sensor 0BFA and t/h sensor 24A4
[SDR]
    driver = user.sdr
    [[sensor_map]]
        wind_dir.0BFA.Acurite5n1Packet = windDir
        wind_speed.0BFA.Acurite5n1Packet = windSpeed
        temperature.0BFA.Acurite5n1Packet = outTemp
        humidity.0BFA.Acurite5n1Packet = outHumidity
        temperature.24A4.AcuriteTowerPacket = inTemp
        humidity.24A4.AcuriteTowerPacket = inHumidity

# collect data from two Hideki TS04 sensors with channel=1 and channel=2
[SDR]
    driver = user.sdr
    [[sensor_map]]
        battery.1:9.HidekiTS04Packet = outBatteryStatus
        humidity.1:9.HidekiTS04Packet = outHumidity
        temperature.1:9.HidekiTS04Packet = outTemp
        battery.2:9.HidekiTS04Packet = inBatteryStatus
        humidity.2:9.HidekiTS04Packet = inHumidity
        temperature.2:9.HidekiTS04Packet = inTemp

# collect data from Fine Offset sensor cluster 0026
[SDR]
    driver = user.sdr
    [[sensor_map]]
        wind_gust.0026.FOWH1080Packet = windGust
        battery.0026.FOWH1080Packet = outBatteryStatus
        total_rain.0026.FOWH1080Packet = rain
        wind_speed.0026.FOWH1080Packet = windSpeed
        wind_dir.0026.FOWH1080Packet = windDir
        humidity.0026.FOWH1080Packet = outHumidity
        temperature.0026.FOWH1080Packet = outTemp


Environment

The driver invokes the rtl_433 executable, so the path to that executable and
any shared library linkage must be defined in the environment in which weewx
runs.

For example, with rtl-433 and rtl-sdr installed like this:

/opt/rtl-433/
/opt/rtl-sdr/

one would set the path like this:

export PATH=/opt/rtl-433/bin:${PATH}
export LD_LIBRARY_PATH=/opt/rtl-sdr/lib

Typically this would be done in the rc script that starts weewx.  If rtl-433
and rtl-sdr are install to /usr/local or /usr, then there should be no need
to set the PATH or LD_LIBRARY_PATH before invoking weewx.
