# installer for the weewx-sdr driver
# Copyright 2016 Matthew Wall, all rights reserved

from setup import ExtensionInstaller

def loader():
    return SDRInstaller()

class SDRInstaller(ExtensionInstaller):
    def __init__(self):
        super(SDRInstaller, self).__init__(
            version="0.11",
            name='sdr',
            description='Capture data from rtl_433',
            author="Matthew Wall",
            author_email="mwall@users.sourceforge.net",
            files=[('bin/user', ['bin/user/sdr.py'])]
            )
