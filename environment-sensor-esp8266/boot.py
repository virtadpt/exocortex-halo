# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# boot.py: This file started life as the basic boot.py file that comes with
#   Micropython.  I turned it into a utility to initialize an ESP8266
#   microcontroller and get it onto a wireless network set in config.py.
#
# print() statements are for debugging while connected through a serial port.

#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v1.1 - Made the presence of a display optional.
# v1.0 - Initial release.

# TO-DO:
# -

# Bare minimum to bootstrap the uc.
import gc
import network
import machine
import time
import sys
import uos

# Pull in the I2C library.
from machine import I2C

# Pull in the configuration file.
import config

# Try to import the ssd1306 driver.
has_display = False
try:
    import ssd1306
    has_display = True
    print("ssd1306 driver module found.")
except:
    print("ssd1306 driver module not found.")

# Handle to an I2C bus object.
i2c = None

# Handle to the display.
display = None

# Handle to a wifi configurator.
wifi = None

# Network configuration information.
local_networks = []
ifconfig = None

# Initialize the I2C bus.
# The magick pin numbers 4 and 5 are here because they're the only two I2C
# related pins on the Feather Huzzah.  They're the GPIO pin numbers, not the
# actual pin numbers...
print("Initializing the I2C bus.")
i2c = I2C(sda=machine.Pin(4), scl=machine.Pin(5))
i2c.scan()
print("Done.")

# I2C addresses are assigned by manufacturers so they're static.  When scanning
# the I2C bus you get decimal values, but everyone else refers to them as hex
# values.  So...
# i2c.scan() value      hex value      device
# ----------------      ---------      ------
# I2C address 56        0x38           AHT20 temperature/humidity sensor
# I2C address 60        0x3c           SSD1306 monochrome OLED

# Initialize the display.  We're going to turn it all the way on, and then all
# the way off to show that it works.
try:
    print("Initializing the sensor's display.")
    display = ssd1306.SSD1306_I2C(128, 32, i2c)
    display.fill(0)
    display.show()
    print("Display initialized.")
except:
    has_display = False
    print("No ssd1306 display found.")

# Tell the user something helpful.
# We have to micromanage the display.
# ssd1306.SSD1306_I2C.show("text", horizontal position, vertical position)
if has_display:
    display.text("Sensor online.", 0, 0)
    display.text("Looking for", 0, 10)
    display.text("network...", 10, 20)
    display.show()
else:
    print("Sensor online.")

# Configure up the wireless interface as a client (it defaults to an access
# point) and associate with the configured network.
print("Searching for configured wireless network.")
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
if not wifi.active():
    if has_display:
        display.fill(0)
        display.text("No wifi.", 0, 0)
        display.text("Trying again.", 0, 10)
        display.show()
    print("Wifi not online.  Trying again.")
    time.sleep(config.delay)

# This should make sure the wifi nic is awake.
local_networks = wifi.scan()
i = 0
for ap in local_networks:
    local_networks[i] = ap[0]
    i = i + 1
print("Networks found: %s" % local_networks)

if bytes(config.network, "utf-8") not in local_networks:
    if has_display:
        display.fill(0)
        display.text("No network.", 0, 0)
        display.text("Trying again.", 0, 10)
        display.show()
    print("Configured wireless network %s not found.  Trying again." % config.network)
    time.sleep(config.delay)
    sys.exit(1)

# Connect to the wireless network.
print("Trying to connect to wireless network.")
wifi.connect(config.network, config.password)
time.sleep(config.delay)

# Print the network configuration information.
# This is actually supposed to go to the local display.
if wifi.isconnected():
    ifconfig = wifi.ifconfig()
    if has_display:
        display.fill(0)
        display.text("Wifi active!", 0, 0)
        display.text(config.network, 0, 10)
        display.text(ifconfig[0], 0, 20)
    print("Network: " + config.network)
    print("IP: " + ifconfig[0])
    if has_display:
        display.show()
    print("Successfully connected to wifi network %s!" % config.network)
    print("IP address is: %s" % ifconfig[0])
    time.sleep(config.delay)
else:
    if has_display:
        display.fill(0)
        display.text("Couldn't find", 0, 0)
        display.text(config.network, 5, 10)
        display.text("Rebooting...", 0, 20)
        display.show()
    print("Unable to connect to network.")
    time.sleep(config.delay)
    sys.exit(1)

# Clean up.
gc.collect()
