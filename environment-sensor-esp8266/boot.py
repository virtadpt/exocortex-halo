# print() statements are for debugging while connected through a serial port.

# Bare minimum to bootstrap the uc.
import gc
import network
import machine
import time
import ssd1306
import sys
import uos

# Pull in the I2C library.
from machine import I2C

# Pull in the configuration file.
import config

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
print("Initializing the sensor's display.")
display = ssd1306.SSD1306_I2C(128, 32, i2c)
display.fill(0)
display.show()
print("Display initialized.")

# Tell the user something helpful.
# We have to micromanage the display.
# ssd1306.SSD1306_I2C.show("text", horizontal position, vertical position)
display.text("Sensor online.", 0, 0)
display.text("Looking for", 0, 10)
display.text("network...", 10, 20)
display.show()

# Configure up the wireless interface as a client (it defaults to an access
# point) and associate with the configured network.
print("Searching for configured wireless network.")
wifi = network.WLAN(network.STA_IF)
if not wifi.active():
    display.fill(0)
    display.text("No wifi.", 0, 0)
    display.text("Trying again.", 0, 10)
    display.show()
    print("Wifi not online.  Trying again.")
    time.sleep(config.delay)
    sys.exit(1)

# This should make sure the wifi nic is awake.
local_networks = wifi.scan()
i = 0
for ap in local_networks:
    local_networks[i] = ap[0]
    i = i + 1
print("Networks found: %s" % local_networks)

if bytes(config.network, "utf-8") not in local_networks:
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
    display.fill(0)
    display.text("Wifi active!", 0, 0)
    display.text(config.network, 0, 10)
    display.text(ifconfig[0], 0, 20)
    print("Network: " + config.network)
    print("IP: " + ifconfig[0])
    display.show()
    print("Successfully connected to wifi network %s!" % config.network)
    print("IP address is: %s" % ifconfig[0])
    time.sleep(config.delay)
else:
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
