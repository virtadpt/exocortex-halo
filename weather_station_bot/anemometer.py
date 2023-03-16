#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# anemometer.py - A module that counts ticks from a two-wire anemometer
#   connected to GPIO pin 5 (RasPi header pin 29).  After 
# https://projects.raspberrypi.org/en/projects/build-your-own-weather-station/2

# By: The Doctor <drwho at virtadpt dot net>

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# - Make the GPIO pin the anemometer is connected to configurable.
# - Make all of the specifics of the anemometer configurable.
# - Use real logger code rather than a bunch of print()s.
# - Find a way to memoize the calculations that don't change (such as the
#   circumfrence of the anemometer).

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

# Global variables.
# Counts the number of times the switch in the anemometer has closed (ticks).
counter = 0

# Handle to the device on the GPIO bus.
sensor = None

# Calculated wind speed.
speed = 0.0

# Functions.
# spin() - Callback function.  Every time the anemometer rotates once, a reed
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

    # Calculate the circumfrence of the anemometer.
    circumfrence = 2 * math.pi * radius

    # Each time the anemometer rotates once, the switch ticks twice.  So we cut
    # the number of rotations in half to get a reasonable number.
    rotations = counter / 2.0

    # Calculate the distance travelled in centimeters.
    distance = circumfrence * rotations

    # Calculate the wind speed in centimeters per second.
    speed = distance / interval

    return(speed)

# cm_to_km(): Convert speed in centimeters per second to kilometers per hour.
# MOOF MOOF MOOF
def cm_to_km(cm):
    pass

# km_to_mi(): Convert kilometers per hour to miles per hour.
# MOOF MOOF MOOF
def km_to_mi(km):
    pass

# Core code...
# Set up the GPIO object.
sensor = gpiozero.Button(gpio_pin)
# MOOF MOOF MOOF - Redundant?
counter = 0
sensor.when_pressed = spin

# Let's try this.
while True:
    counter = 0
    time.sleep(interval)
    print(calculate_speed(interval), "cm/h")

# Do other stuff.
# Sample wind speed for <mumble> seconds.
# Calculate the wind speed.
# Report the wind speed.
# Go do other stuff.

# Fin.
