#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# conversions.py - A Weather Station Bot module that implements conversions
#   from one unit (degrees Centigrate) to another (degrees Fahrenheit).
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# v1.1 - Added hPa to inHg, because the BME280 outputs in hPa. Oops.
# v1.0 - Initial release.

# TODO:
# -

# By: The Doctor <drwho at virtadpt dot net>
#     0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

import sys

# c_to_f(): Converts centigrade to fahrenheit.
def c_to_f(centigrade):
    # Sure, I could one-line this but I can never remember how to do the
    # conversion and this makes it easy to refer back to.
    fahrenheit = centigrade * 9
    fahrenheit = fahrenheit / 5
    fahrenheit = fahrenheit + 32
    return(fahrenheit)

# km_to_mi(): Convert velocity in km/h to speed in miles per hour.
def km_to_mi(km):
    # You wouldn't believe how difficult this is to look up.  Some pages say
    # it's a multiplication, some say it's division.  I had to look at a bunch
    # of different websites, and I basically picked the conversion that
    # showed up more often (division) than the other.
    # We USians really can't do anything right, can we?
    return(km / 1.609)

# mm_to_in(): Converts mm into inches.
def mm_to_in(mm):
    # 25.4 mm per inch.
    return(mm / 25.4)

# cm_to_km(): Convert velocity in centimeters per second to kilometers per hour.
def cm_to_km(cm):
    # 100 cm / m
    # 1000 m / km
    return((cm / 100) / 1000)

# kpa_to_mmhg(): Convert pressure in kilopascals to mm of mercury.
def kpa_to_mmhg(kpa):
    return(kpa * 7.50062)

# hpa_to_inhg(): Convert pressure in hectopascals to inches of mercury.
def hpa_to_inhg(hpa):
    return(hpa * 0.02953)

if __name__ == "__main__":
    print("Utility functions in this module:")
    print(" * c_to_f(centigrade) - convert degrees Celsius to Fahrenheit")
    print(" * km_to_mi(km) - convert kilometers to miles")
    print(" * mm_to_in(mm) - convert millimeters to inches")
    print(" * cm_to_km(cm) - convert centimeters to kilometers")
    print(" * kpa_to_mmhg(kpa) - convert kilopascals to millimeters of mercury")
    print(" * hpa_to_inhg(hpa) - convert hectopascals to inches of mercury")
    sys.exit(0)

