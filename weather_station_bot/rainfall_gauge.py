#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# rainfall_gauge.py - A module that counts ticks from a two-wire rain gauge
#   (every tilt is one tick o the switch) connected to GPIO pin 6 (RasPi header
#   pin 31).  After 
# https://projects.raspberrypi.org/en/projects/build-your-own-weather-station/8

# By: The Doctor <drwho at virtadpt dot net>

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# - Make the GPIO pin the rain gauge is connected to configurable.
# - Use real logger code rather than a bunch of print()s.
# - Figure out when to reset the counter (i.e., it's no longer raining).

# Load modules.
import gpiozero
import sys
import time

import globals

# Constants.
# GPIO pin (not header pin) the rain gauge is connected to.
gpio_pin = 6

# Period of time in which tips of the rain gauge sampler are counted to
# calculate the amount of rainfall.
interval = 5

# Every time this amount of rain collects in the rain gauge, it means that
# 0.2794 mm of rain has fallen.  Used to calculate the amount of rain that has
# fallen.
rainfall_sample = 0.2794

# Global variables.
# Counts the number of times the switch in the anemometer has closed (ticks).
counter = 0

# Amount of rain fallen so far (in mm).
rainfall = 0.0

# Used to store a time_t timestamp for calculating the length of time of a
# rainfall sample.
start_time = 0.0

# Functions.
# rain_gauge_tip(): Callback function.  Every time the switch in the rain gauge
#   ticks the global counter increments.
def rain_gauge_tip():
    # i tip dis nao
    global counter
    counter = counter + 1

# reset_counter(): Helper function that resets the tip counter to 0.
def reset_counter():
    global counter
    counter = 0

# reset_rainfall(): Helper function that resets the rainfall gauge to 0.0.
def reset_rainfall():
    global rainfall
    rainfall = 0.0

# Core code...
# get_precip(): The function that does everything by calling everything
#   else.  Here so that it can be called from Weather Station Bot's central
#   module, as well as __main__ for testing.  Returns a hash table containing
#   the sample data.
def get_precip():
    global counter
    global rainfall

    # Holds the data gathered and computed from the anemometer.
    sample = {}

    # Set up the GPIO object.
    if not globals.raingauge:
        globals.raingauge = gpiozero.Button(gpio_pin)

    # Set a callback that increments the number of rotations counted every time
    # the GPIO pin is toggled.
    globals.raingauge.when_pressed = rain_gauge_tip

    # Do the thing.
    # Store the time at which the samples are taken.
    start_time = time.time()
    while (time.time() - start_time) <= interval:
        reset_counter()
        reset_rainfall()
        time.sleep(interval)

        # Calculate the amount of rainfall in mm.
        rainfall = counter * rainfall_sample
        sample["mm"] = round(rainfall, 2)

    return(sample)

# Exercise my code.
if __name__ == "__main__":
    print("Starting test run of 10 samples.")
    for i in range(1, 10):
        print("Running test cycle %s." % i)
        data = get_precip()

        # Print the test output.
        print("Rainfall in mm: %s" % round(data["mm"], 2))
        print()

    print("ticks: %s" % counter)
    print("rainfall: %s" % rainfall)

    print("End of test run.")
    sys.exit(0)

# Fin.
