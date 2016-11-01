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
    Thermo Sensor THR228N
    LaCrosse WS


Installation

0) install pre-requisites

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
        windDir = wind_dir.0BFA.Acurite5n1Packet
        windSpeed = wind_speed.0BFA.Acurite5n1Packet
        outTemp = temperature.0BFA.Acurite5n1Packet
        outHumidity = humidity.0BFA.Acurite5n1Packet
        inTemp = temperature.24A4.AcuriteTowerPacket
        inHumidity = humidity.24A4.AcuriteTowerPacket

# collect data from two Hideki TS04 sensors with channel=1 and channel=2
[SDR]
    driver = user.sdr
    [[sensor_map]]
        outBatteryStatus = battery.1:9.HidekiTS04Packet
        outHumidity = humidity.1:9.HidekiTS04Packet
        outTemp = temperature.1:9.HidekiTS04Packet
        inBatteryStatus = battery.2:9.HidekiTS04Packet
        inHumidity = humidity.2:9.HidekiTS04Packet
        inTemp = temperature.2:9.HidekiTS04Packet

# collect data from Fine Offset sensor cluster 0026
[SDR]
    driver = user.sdr
    [[sensor_map]]
        windGust = wind_gust.0026.FOWH1080Packet
        outBatteryStatus = battery.0026.FOWH1080Packet
        rain_total = rain_total.0026.FOWH1080Packet
        windSpeed = wind_speed.0026.FOWH1080Packet
        windDir = wind_dir.0026.FOWH1080Packet
        outHumidity = humidity.0026.FOWH1080Packet
        outTemp = temperature.0026.FOWH1080Packet

To figure out the sensor identifiers, run the driver directly, possibly with
the --debug option.  Another option is to run weewx with the logging options
for [SDR] enabled to display the sensors found by rtl, the sensor identifiers
used by weewx, and the sensors actually recognized by weewx.

[SDR]
    driver = user.sdr
    log_unknown_sensors = True
    log_unmapped_sensors = True

By default the logging options are False.


How to diagnose problems

First try running the rtl_433 application to be sure that it works properly:

sudo rtl_433

Once that is working, run the driver directly to be sure that it is collecting
data from the rtl_433 application:

cd /home/weewx
sudo PYTHONPATH=bin python bin/user/sdr.py

Make note of the sensor identifiers.  Each identifier is a three-part string
consisting of the observation, sensor id, and rf packet type, separated by
periods.  You need these in the sensor map to tell weewx the association
between sensors and database fields.

Once that is working and you have created the sensor map, run weewx directly
in one shell while you monitor the weewx log in a separate shell:

in shell 1:
cd /home/weewx
sudo ./bin/weewxd weewx.conf

in shell 2:
tail -f /var/log/syslog

At this point, verify that the mapping you made in the weewx configuration file
is working as you intend.  You should see data from your sensors in the weewx
LOOP and REC output.  If not, check the log file.  Use the logging options in
the [SDR] section of the weewx configuration file to help figure out which
sensors are captured, recognized, and parsed.

Once you are satisfied with the output when running weewx directly, run weewx
as a daemon and configure rc script or systemd to run weewx at system startup.

sudo /etc/init.d/weewx start


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

If you cannot control the environment in which weewx runs, then you can specify
the LD_LIBRARY_PATH and PATH in the weewx-sdr driver itself.  For example:

[SDR]
    driver = user.sdr
    path = /opt/rtl-433/bin
    ld_library_path = /opt/libusb-1.0.20/lib:/opt/rtl-sdr/lib
    [[sensor_map]]
        ...


libusb

I have had problems running rtl-sdr on systems with libusb 1.0.11.  The rtl_433
command craps out with a segmentation fault, and the rtl_test command sometimes
leaves the dongle in a weird state that can be cleared only by unplugging then
replugging the dongle.

Using a more recent version of libusb (e.g., 1.0.20) seems to clear things up.
