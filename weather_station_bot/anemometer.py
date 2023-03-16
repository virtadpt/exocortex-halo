#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# anemometer.py - A module that counts ticks from a two-wire anemometer
#   connected to GPIO pin 5 (RasPi header pin 29).  After 
# https://projects.raspberrypi.org/en/projects/build-your-own-weather-station/5

# By: The Doctor <drwho at virtadpt dot net>

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# - Make the GPIO pin the anemometer is connected to configurable.
# - Make all of the specifics of the anemometer configurable.
# - Use real logger code rather than a bunch of print()s.
# - Find a way to memoize the calculations that don't change (such as the
#   circumfrence of the anemometer).
# - Make the anemometer factor configurable but default to 1.18.
# - Turn this into an actual Python module.

# Load modules.
import gpiozero
import math
import time

# Constants.
# GPIO pin (not header pin) the anemometer is connected to.
gpio_pin = 5

# Radius of the anemometer (in centimeters).
radius = 9.0

# Period of time in which rotations are counted to calculate speed in seconds.
interval = 5

# Anemometer factor, per
# https://projects.raspberrypi.org/en/projects/build-your-own-weather-station/5
anemometer_factor = 1.18

# Global variables.
# Counts the number of times the switch in the anemometer has closed (ticks).
counter = 0

# Handle to the device on the GPIO bus.
sensor = None

# Calculated wind speed.
speed = 0.0

# Functions.
# spin(): Callback function.  Every time the anemometer rotates once, a reed
#   switch closes and re-opens.  This toggles a GPIO pin on a RasPi.  Every
#   time that pin is toggled, this function is called.
def spin():
    global counter
    counter = counter + 1

# calculate_speed(): Calculate the wind speed in centimeters per second.
def calculate_speed(time):
    global counter

    # Circumfrence of the anemometer.
    circumfrence = 0.0

    # Number of rotations in the sampling period.
    rotations = 0.0

    # Distance travelled by the anamometer's cups.
    distance = 0.0

    # Velocity of the wind, in cm/h.
    velocity = 0.0

    # Calculate the circumfrence of the anemometer.
    circumfrence = 2 * math.pi * radius

    # Each time the anemometer rotates once, the switch ticks twice.  So we cut
    # the number of rotations in half to get a reasonable number.
    rotations = counter / 2.0

    # Calculate the distance travelled in centimeters.
    distance = circumfrence * rotations

    # Calculate the wind velocity in centimeters per second.
    velocity = distance / interval

    # Per the original project, an anemometer factor must be included to get
    # a more reasonable value.
    velocity = velocity * anemometer_factor

    return(velocity)

# cm_to_km(): Convert velocity in centimeters per second to kilometers per hour.
def cm_to_km(cm):
    # 100 cm / m
    # 1000 m / km
    return((cm / 100) / 1000)

# km_to_mi(): Convert velocity in km/h to speed in miles per hour.
def km_to_mi(km):
    # You wouldn't believe how difficult this is to look up.  Some pages say
    # it's a multiplication, some say it's division.  I had to look at a bunch
    # of different websites, and I basically picked the conversion that
    # showed up more often (division) than the other.
    # We USians really can't do anything right, can we?
    return(km / 1.609)

# reset_counter(): Helper function that resets the rotation counter to 0.
def reset_counter():
    global counter
    counter = 0

# Core code...
# Set up the GPIO object.
sensor = gpiozero.Button(gpio_pin)

# Set a callback that increments the number of rotations counted every time the
# GPIO pin is toggled.
sensor.when_pressed = spin

# Do the thing.
while True:
    counter = 0
    velocity = 0
    speed = 0
    time.sleep(interval)

    # Calculate the speed in cm/s.
    velocity = calculate_speed(interval)
    print("Velocity: %s cm/h" % round(velocity, ndigits=2))

    # Convert to km/h.
    velocity = cm_to_km(velocity)
    print("Velocity: %s km/h" % round(velocity, ndigits=4))

    # Convert km/h to mph.
    speed = km_to_mi(velocity)
    print("Speed: %s mph" % round(speed, ndigits=4))

    # Why do I have the more conventional measurements rounded out to four
    # decimal places?  If I use only two I keep getting answers of 0.0 when
    # I bench test.
    print()

# Return calculated values in (what else) a hash table so that the user can
# choose the units they want in a config file without needing to do any
# conversion on their end of things.

# Do other stuff.
# Sample wind speed for <mumble> seconds.
# Calculate the wind speed.
# Report the wind speed.
# Go do other stuff.

# Fin.
