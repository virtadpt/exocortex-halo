#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# globals.py - A Weather Bot module that implements a couple of global
#   variables.  Right now this doesn't get a whole lot of use, but if I add
#   other remote monitoring modules in the future this will help.
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# v1.0 - Initial release.

# TODO:
# -

# By: The Doctor <drwho at virtadpt dot net>
#     0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

import sys

# Variables
# Handle to an SMbus for the BME280.
bme280_sensor = None

# Handle to the GPIO interface to the anemometer.
anemometer = None

# Handle to the GPIO interface to the weathervane.
weathervane = None

# Handle to the GPIO interface to the rain gauge's switch.
raingauge = None

# Core code.
if __name__ == "__main__":
    print("No self tests yet.")
    sys.exit(0)

