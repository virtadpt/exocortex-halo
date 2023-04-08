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

# Load modules.
import gpiozero
import math
import sys
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

# Average wind speed.
# I know, this is supposed to be velocity because it's not calculated out of
# metric.
wind_speed = 0.0

# Used to store a time_t timestamp for calculating the length of time of a
# wind velocity sample.
start_time = 0.0

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

# reset_counter(): Helper function that resets the rotation counter to 0.
def reset_counter():
    global counter
    counter = 0

# Core code...
# get_wind_speed(): The function that does everything by calling everything
#   else.  Here so that it can be called from Weather Station Bot's central
#   module, as well as __main__ for testing.  Returns a hash table containing
#   the sample data.
def get_wind_speed():

    # Holds the data gathered and computed from the anemometer.
    sample = {}

    # Set up the GPIO object.
    sensor = gpiozero.Button(gpio_pin)

    # Set a callback that increments the number of rotations counted every time
    # the GPIO pin is toggled.
    sensor.when_pressed = spin

    # Do the thing.
    # Store the time at which the samples are taken.
    start_time = time.time()
    while (time.time() - start_time) <= interval:
        reset_counter()
        velocity = 0
        speed = 0
        time.sleep(interval)

        # Calculate the speed in cm/s.
        velocity = calculate_speed(interval)
        sample["velocity_cm_h"] = round(velocity, 2)

        # Convert to km/h.
        velocity = cm_to_km(velocity)
        sample["velocity_km_h"] = round(velocity, 2)

        # Convert km/h to mph.
        speed = km_to_mi(velocity)
        sample["speed"] = round(speed, 2)

        # Why do I have the more conventional measurements rounded out to four
        # decimal places?  If I use only two I keep getting answers of 0.0 when
        # I bench test.

        print("Value of counter: %s" % counter)

    return(sample)

# Exercise my code.
if __name__ == "__main__":
    print("Starting test run of 10 samples.")
    for i in range(1, 10):
        print("Running test cycle %s." % i)
        data = get_wind_speed()

        # Print the test output.
        print("Velocity: %s cm/h" % round(data["velocity_cm_h"], ndigits=2))
        print("Velocity: %s km/h" % round(data["velocity_km_h"], ndigits=2))
        print("Speed: %s mph" % round(data["speed"], ndigits=4))
        print()

    print("End of test run.")
    sys.exit(0)

# Fin.
