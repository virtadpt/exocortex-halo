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
# - Make the channel of the ADC chip configurable.
# - Use real logger code rather than a bunch of print()s.
# - The table of values-to-directions should probably be configurable, but I'm
#   not sure yet how to do that.
# - Add a utility that helps a user calculate their own table of direction/
#   values?

# Load modules.
import gpiozero
import sys
import time

# Constants.
# Channel (pin) of the ADC the weather vane is connected to.
channel = 0

# Value of the reference voltage the ADC is receiving on pin 15.  The circuit
# I'm using (and hardwired) draws power from pin 1 on the RasPi (3.3 VDC).
reference_voltage = 3.3

# Global variables.
# Handle to the device on the GPIO bus.
sensor = None

# Technically this falls under global constants, but I derived these values
# experimentally so they might change from station to station.
directions = {
    "2.1": "north",
    "1.8": "northeast",
    "3.0": "east",
    "2.7": "southeast",
    "2.4": "south",
    "1.3": "southwest",
    "0.2": "west",
    "1.0": "northwest"
    }

# Here is the research code I used to generate those values:
#
# import gpiozero
# import time
# adc = gpiozero.MCP3008(channel=0)
# values = []
# while True:
#   wind = round(adc.value * 3.3, 1)
#   if not wind in values:
#       values.append(wind)
#       print("Got new value: %s" % wind)
#       print()
#   time.sleep(5)
#

# Core code...
# get_direction(): The function that does everything by calling everything
#   else.  Here so that it can be called from Weather Station Bot's central
#   module, as well as __main__ for testing.  Returns a hash table containing
#   the sample data.
def get_direction():

    # Voltage from the weather vane.
    value = 0.0

    # Set up the GPIO object.
    sensor = gpiozero.MCP3008(channel=channel)

    # Get a sample from the weather vane.
    value = round(sensor.value * reference_voltage, 1)
    print("Value: %s" % value)

    # Look up the value from the sensor in the direction table.  If it's in
    # there return the direction, else return None.
    try:
        return(directions[value])
    except:
        return None

# Exercise my code.
if __name__ == "__main__":
    print("Starting test run.")

    sensor = gpiozero.MCP3008(channel=channel)
    for i in range(10):
        temp = None
        temp = get_direction()
        if temp:
            print("The weather vane is pointing %s." % temp)
        else:
            print("The weather vane returned a spurious value.")
        time.sleep(5)

    print("End of test run.")
    sys.exit(0)

# Fin.
