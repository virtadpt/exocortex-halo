#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# bme280_sensor.py - A module that accesses the BME 280 sensor module from
#   Adafruit.  After
# https://projects.raspberrypi.org/en/projects/build-your-own-weather-station/2

# By: The Doctor <drwho at virtadpt dot net>

# License: GPLv2

# v1.0 - Initial release.

# TO-DO:
# - Make the sensor's I2C address configurable.
# - Use real logger code rather than a bunch of print()s.
# - Turn this into a loadable module for the actual bot.
# - Make the sleep time optional.  Eventually this code will be called as a
#   module from the real bot.

# Load modules.
import bme280
import smbus2
import sys
import time

# Constants.
port = 1

# I2C address of the sensor.
address = 0x77

# Global variables.
# Handle to an smbus2 port.
bus = None

# Raw data from the sensor.
bme280_data = None

# If this is a class or module, say what it is and what it does.

# Classes.

# Functions.

# Core code...
# Get a handle to the SMbus.
try:
    bus = smbus2.SMBus(port)
    bme280.load_calibration_params(bus, address)
except:
    print("Unable to get access to the SMbus.")
    sys.exit(1)

# Research code: Pull data from the sensor every five seconds and print it to
# stdout.
while True:
    # Structure of the data sample returned below:
    #   .id - A GUID.  String.
    #   .timestamp - ISO 8601 timestamp.  String.
    #   .temp - Temperature in degrees Centigrade.  Float.
    #   .pressure - Pressure in hPa/millibars.  Float.
    #       Standard pressure at sea level is 1013 hPa.
    #   .humidity - Relative humidity.  Float.
    bme280_data = bme280.sample(bus, address)
    print("Time: %s" % bme280_data.timestamp)
    print("Temperature: %s degrees C" % round(bme280_data.temperature,
        ndigits=2))
    print("Pressure: %s kPa" % round(bme280_data.pressure, ndigits=2))
    print("Humidity: %s%%" % round(bme280_data.humidity, ndigits=2))

    print()
    time.sleep(5)

# Fin.
