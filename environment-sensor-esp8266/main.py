# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# main.py: This file initializes the environment sensor itself (here, an
#   AHT20 breakout board from Adafruit) and takes temperature and
#   relative humidity readings every couple of seconds.  It's not done
#   yet.
#
# Temperatures are read in degrees Centigrade from the sensor.  So, they
# will need to be converted to other scales depending upon what the user
# has configured.
#
# print() statements are for debugging while connected through a serial port.
#
# Location of the AHT20 datasheet:
# https://files.seeedstudio.com/wiki/Grove-AHT20_I2C_Industrial_Grade_Temperature_and_Humidity_Sensor/AHT20-datasheet-2020-4-16.pdf
#
# Mirror: https://drwho.virtadpt.net/files/AHT20.pdf

#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v1.2 - Added "send measurements to an arbitrary URL" functionality.
# v1.1 - Made the presence of a display optional.
# v1.0 - Initial release.

# TO-DO:
# -

# Modules for basic operation of the sensor.
import gc
import machine
import sys
import time
import urequests

from machine import I2C

# Pull in the config file.
import config

# Try to import the ssd1306 driver.
has_display = None
try:
    import ssd1306
    has_display = True
    print("ssd1306 driver module found.")
except:
    print("ssd1306 driver module not found.")

# Try to import the urequests (https://github.com/micropython/micropython-lib/tree/master/urequests) module.
has_requests = False
try:
    import urequests as requests
    has_requests = True
    print("urequests module found, imported as requests.")
except:
    print("Unable to import urequests module.")

# Variables.
# Generic response to hardware call variable.  We need to be careful with
# memory usage.
response = None

# Handle to a display object.
display = None

# Measurement from the sensor.
measurement = None

# Data split out of the sensor's measurement.
humidity = None
temperature = None

# Handle to a urequests object.
request = None

# HTTP headers.
headers = {}

# URL to contact (if configured).
url = None

# Handle to an HTTP request, for use if configured.
request = None

# Data to send to the URL.
measurement = {}

# Used to determine when to send measurements to the webhook (if enabled).
loop_counter = 0

# How often the sensor sends measurements to the webhook, if enabled.
# This is hardwired to 60 seconds untill I figure out how to do it right.
status_polling = 60

# Constants.
# Required delays (in seconds, because they're specified as ms in the docs).
state_delay = 0.04
measurement_delay = 0.075

# Repeating documentation from boot.py
# I2C addresses are assigned by manufacturers so they're static.  When scanning
# the I2C bus you get decimal values, but everyone else refers to them as hex
# values.  So...
# i2c.scan() value      hex value      device
# ----------------      ---------      ------
# I2C address 56        0x38           AHT20 temperature/humidity sensor
# I2C address 60        0x3c           SSD1306 monochrome OLED

# I2C devices' bus addresses are hardwired and standardized, so we don't
# necessarily have to worry about this changing.  Making it a constant makes
# the code more literate.
aht20_device_id = 0x38

# I2C commands, as constants to make them easier to work with (and document
# them.
initialize_command = b'\xbe\x08\x00'
calibrate_command = b'\xe1\x08\x00'
reset_command = b'\xba'
measure_command = b'\xac\x33\x00'
read_command = b'\x71'

# The sensor always returns six (6) bytes.  This eliminates magick numbers.
measurement_bytes = 6

# Bit manipulation constant.  Expressed as math so it matches the datasheet.
bit_manipulation_constant = 2**20

# Functions.
# Clears the display.
def blank_display(display):
    display.fill(0)
    display.show()
    print("Display cleared.")
    return()

# Core code.
# Build a display object.
try:
    display = ssd1306.SSD1306_I2C(128, 32, i2c)
    print("main.py got the display.")
except:
    has_display = False
    print("No display found.")

# Initialize the AHT20 device.
response = None
response = i2c.writeto(aht20_device_id, initialize_command)
time.sleep(state_delay)
if response:
    print("I2C device %s successfully initialized." % (aht20_device_id))
else:
    print("I2C device %s not successfully initialized." % (aht20_device_id))
    sys.exit(1)

# Calibrate the AHT20 sensor.
response = None
response = i2c.writeto(aht20_device_id, calibrate_command)
time.sleep(state_delay)
print("Value of response to calibration command: %s" % response)

# Check for the presence of a URL to send measurements to in the config
# file.
if config.webhook:
    print("Going to send measurements to URL %s." % config.webhook)
if config.auth:
     print("Got basic auth header %s." % config.auth)
     headers["Authorization"] = config.auth

# Blank the display.
if has_display:
    blank_display(display)

# Okay, let's do this.
while True:
    # Belt and suspenders.
    measurement = None
    humidity_data = None
    temperature_data = None

    # Tell the sensor to take a measurement.
    response = i2c.writeto(aht20_device_id, measure_command)
    print("Requested measurement.  Got %s from the i2c bus." % response)

    # Get the measurement from the sensor.
    response = i2c.writeto(aht20_device_id, read_command)
    print("Requested results.  Got %s from the i2c bus." % response)

    # Structure of measurement (in bytes)
    # [status]  [humidity data: 2] [humidity temperature] [temperature data: 2]
    measurement = i2c.readfrom(aht20_device_id, measurement_bytes)
    print("Bytes from sensor: %s" % measurement)

    # Dice up the measurement.
    # status = measurement[0]
    # Source: https://github.com/adafruit/Adafruit_CircuitPython_AHTx0/blob/master/adafruit_ahtx0.py
    humidity = (measurement[1] << 12 | measurement[2] << 4 | measurement[3] >> 4)
    temperature = (((measurement[3] & 0xf) << 16) | measurement[4] << 8 | measurement[5])
    print("humidity: %s" % humidity)
    print("temperature %s" % temperature)

    # Calculations are all taken from the AHT20 datasheet.
    # Calculate the humidity.
    humidity = (humidity * 100) / bit_manipulation_constant
    humidity = round(humidity, 2)
    print("Humidity: %s%% relative" % humidity)

    # Calculate the temperature (in Centigrade by default).
    temperature = ((temperature * 200.0) / bit_manipulation_constant) - 50.0
    print("Temperature %s degrees Centigrade." % temperature)

    # Fahrenheit?
    if config.temperature_scale == "f":
        temperature = ((temperature * 9) / 5) + 35.0
        print("Temperature %s degrees Fahrenheit." % temperature)

    # Kelvin?
    if config.temperature_scale == "k":
        temperature = temperature + 273.15
        print("Temperature %s degrees Kelvin." % temperature)

    # Round to 2 decimal places, just because.
    temperature = round(temperature, 2)

    # Convert figures to strings to make life easier.
    humidity = str(humidity)
    temperature = str(temperature)

    # Update the display.
    if has_display:
        display.text(humidity + "% rH", 0, 0)
        display.text(temperature + " deg " + config.temperature_scale.upper(), 0, 10)
        display.show()

    # Send the measurements to the configured webhook.
    if config.webhook:
        # If it's not time to send a measurement to the webhook, bounce out
        # of this conditional.
        if loop_counter < status_polling:
            print("Not going to send a measurement to the webhook.")
            print("Incrementing the loop counter.")
            loop_counter = loop_counter + config.delay
            print("Loop counter is now %s" % loop_counter)
            time.sleep(config.delay)
            if has_display:
                blank_display(display)
            continue

        print("Trying to send measurement to the webhook.")

        # Build a new measurement.
        measurement = {}
        measurement["stats"] = {}
        measurement["stats"]["temperature"] = temperature
        measurement["stats"]["humidity"] = humidity
        measurement["stats"]["scale"] = config.temperature_scale

        # Send the measurement to the webhook.
        print("Trying to contact the webhook.")
        try:
            request = urequests.post(config.webhook, json=measurement,
                headers=headers)
        except:
            print("Connection attempt failed.")
        print("HTTP return code: %s" % request.status_code)
        print("HTTP status: %s" % request.reason)

        # Nullify the request handle.
        request = None

        # Reset the loop counter.
        loop_counter = 0

        # Free up some memory because the urequests object is pretty hefty.
        gc.collect()

    # Sleep for a while.
    time.sleep(config.delay)
    if has_display:
        blank_display(display)

# Fin.
