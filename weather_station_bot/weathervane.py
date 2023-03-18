#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# weathervane.py - A module that that gets readings from a standard multiple
#   switches-and-resisters weather vane (wind vane) connected to GPIO pin 6
#   (RasPi header pin 31).  After 
# https://projects.raspberrypi.org/en/projects/build-your-own-weather-station/7

# By: The Doctor <drwho at virtadpt dot net>

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# - Make the GPIO pin the weather vane is connected to configurable.
# - Make the channel of the ADC chip configurable.
# - Use real logger code rather than a bunch of print()s.
# - The table of values-to-directions should probably be configurable, but I'm
#   not sure yet how to do that.

# Load modules.
import gpiozero
import sys
import time

# Constants.
# GPIO pin (not header pin) the anemometer is connected to.
gpio_pin = 6

# Channel (pin) of the ADC the weather vane is connected to.
channel = 0

# Value of the reference voltage the ADC is receiving on pin 15.  The circuit
# I'm using (and hardwired) draws power from pin 1 on the RasPi (3.3 VDC).
reference_voltage = 3.3

# Global variables.
# Handle to the device on the GPIO bus.
sensor = None

# Mappings of compass directions to values from the ADC.
directions = {
    "N": {"low": 0.004836345872007541, "high": 0.03385442110405499},
    "NE": {"low": 0.011284807034684995, "high": 0.030630190522715893},
    "E": {"low": 0.004836345872007541, "high": 0.09833903273082586},
    "SE": {"low": 0.004836345872007541, "high": 0.03385442110405499},
    "S": {"low": 0.004836345872007541, "high": 0.040302882266731704},
    "SW": {"low": 0.004836345872007541, "high": 0.02418172936003917},
    "W": {"low": 0.011284807034684995, "high": 0.027405959941377532},
    "NW": {"low": 0.004836345872007541, "high": 0.040302882266731704}
    }

# Functions.


# Core code...
# get_direction(): The function that does everything by calling everything
#   else.  Here so that it can be called from Weather Station Bot's central
#   module, as well as __main__ for testing.  Returns a hash table containing
#   the sample data.
def get_direction():

    # Holds the data gathered and computed from the anemometer.
    sample = {}

    # Set up the GPIO object.
    sensor = gpiozero.MCP3008(channel=channel)

    print(round(sensor.value * reference_voltage, 3))

    return(sample)

# Exercise my code.
if __name__ == "__main__":
    print("Starting test run.")

    while True:
        get_direction()
        time.sleep(5)

    print("End of test run.")
    sys.exit(0)

# Fin.
