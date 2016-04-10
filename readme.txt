weewx-sdr

This is a driver for weewx that captures data from software-defined radio.
It works with open source rtl sdr software that in turn works with
inexpensive, broad spectrum radio receivers such as the Realtek RTL2838UHIDIR.
These devices cost about 20$US and are capable of receiving radio signals from
weather stations, energy monitors, doorbells, and many other devices that use
unlicensed spectrum such as 433MHz, 838MHz, and 900MHz frequencies.

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


Hardware

Tested with the Realtek RTL2838UHIDIR.  Should work with any software-defined
radio that is compatible with the rtl-sdr software.  Uses the modules in
rtl_433 to recognize packets.
