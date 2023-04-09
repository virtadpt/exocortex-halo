#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# bme280_sensor.py - A module that accesses the BME 280 sensor module from
#   Adafruit.  After
# https://projects.raspberrypi.org/en/projects/build-your-own-weather-station/2

# By: The Doctor <drwho at virtadpt dot net>

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# - Make the sensor's I2C address configurable.
# - Use real logger code rather than a bunch of print()s.

# Load modules.
import bme280
import logging
import smbus2
import sys

# Constants.
port = 1

# I2C address of the sensor.
address = 0x77

# Functions.
# get_reading() - Get a data sample from the sensor.  Data will not be
#   rounded, converted, or anything else.  That needs to happen elsewhere.
def get_reading():
    # Handle to an SMbus object.
    bus = None

    # Handle to a sensor sample.
    bme280_data = None

    # Hash table of data from the sensor sample.
    data = {}

    # Get a handle to the SMbus.
    try:
        logging.debug("Trying to get access to the sensor.")
        bus = smbus2.SMBus(port)
        bme280.load_calibration_params(bus, address)
    except:
        logging.error("Unable to get access to the SMbus.")
        return(None)

    # Structure of the data sample returned below:
    #   .id - A GUID.  String.
    #   .timestamp - ISO 8601 timestamp.  String.
    #   .temp - Temperature in degrees Centigrade.  Float.
    #   .pressure - Pressure in hPa/millibars.  Float.
    #       Standard pressure at sea level is 1013 hPa.
    #   .humidity - Relative humidity.  Float.
    # Get a sample from the sensor.
    bme280_data = bme280.sample(bus, address)

    # Populate the sample.
    data["timestamp"] = bme280_data.timestamp
    data["temp_c"] = round(bme280_data.temperature, 2)
    data["pressure"] = round(bme280_data.pressure, 2)
    data["humidity"] = round(bme280_data.humidity, 2)

    return(data)

# Core code...
# If we call this file by itself, exercise the do-stuff function.
if __name__ == "__main__":
    sample = get_reading()
    if not sample:
        print("Sensor did not return data.")
        sys.exit(1)

    print("Time: %s" % sample["timestamp"])
    print("Temperature: %s degrees C" % round(sample["temp_c"], ndigits=2))
    print("Pressure: %s kPa" % round(sample["pressure"], ndigits=2))
    print("Humidity: %s%%" % round(sample["humidity"], ndigits=2))

    sys.exit(0)

# Fin.
