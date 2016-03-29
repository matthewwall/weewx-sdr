weewx-sdr

This is a driver for weewx that captures data from software-defined radio.


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
