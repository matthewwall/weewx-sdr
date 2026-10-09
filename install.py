# installer for the weewx-sdr driver
# Copyright 2016-2024 Matthew Wall
# Distributed under the terms of the GNU Public License (GPLv3)

from weecfg.extension import ExtensionInstaller

VERSION = '0.96b2'

# Files to install, relative to the extension root.
# This has to be a static list because weewx
# uses this same installer to remove these files
# if a user uninstalls our extension
FILES = [
    'bin/user/brands/__init__.py',
    'bin/user/brands/acurite.py',
    'bin/user/brands/alecto.py',
    'bin/user/brands/ambient.py',
    'bin/user/brands/auriol.py',
    'bin/user/brands/bresser.py',
    'bin/user/brands/calibeur.py',
    'bin/user/brands/cotech.py',
    'bin/user/brands/ecowitt.py',
    'bin/user/brands/emax.py',
    'bin/user/brands/esperanza.py',
    'bin/user/brands/fine_offset.py',
    'bin/user/brands/hideki.py',
    'bin/user/brands/holman.py',
    'bin/user/brands/infactory.py',
    'bin/user/brands/kedsum.py',
    'bin/user/brands/lacrosse.py',
    'bin/user/brands/nexus.py',
    'bin/user/brands/oregon_scientific.py',
    'bin/user/brands/prologue.py',
    'bin/user/brands/rubicson.py',
    'bin/user/brands/springfield.py',
    'bin/user/brands/tfa.py',
    'bin/user/brands/tsft002.py',
    'bin/user/brands/vevor.py',
    'bin/user/brands/ws2032.py',
    'bin/user/brands/wt0124.py',
    'bin/user/core.py',
    'bin/user/log.py',
    'bin/user/packet.py',
    'bin/user/sdr.py',
    'bin/user/units.py',
]


def loader():
    return SDRInstaller()


class SDRInstaller(ExtensionInstaller):
    def __init__(self):
        super(SDRInstaller, self).__init__(
            version=VERSION,
            name='sdr',
            description='Capture data from rtl_433',
            author='Matthew Wall',
            author_email='mwall@users.sourceforge.net',
            files=[('bin/user', FILES)],
        )
