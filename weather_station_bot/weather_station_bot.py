#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# weather_station_bot.py - A modular bot designed to poll physical weather
#   sensors attached to the computer it's running on.  By default it will only
#   send alerts to the XMPP bridge if there is a major change (it starts
#   raining, it stops raining, gusts of wind).
#
#   This bot is modular because not every weather station someone builds will
#   have the same set of sensors, or even the same kind of sensors (e.g.,
#   the BME* series of multisensors).  Additionally, not everyone will be
#   sending the data to the same places: Dashboards, dedicated applications,
#   citizen science projects, and so forth.  So, to facilitate this those can
#   be added as new modules as well.

# By: The Doctor <drwho at virtadpt dot net>

# License: GPLv3

# v1.2 - Added some newlines to the online help to make the online text look
#        a little nicer.
#      - Changed kPa to hPa everywhere.
#      - Added at-need conversions of hPa to inHg where necessary.
#      - Added imperial/metric conditionals to the air pressure parts, like I
#        had for temperature and speed.
#      - Added wind direction to the output file writer.
#      - Fixed a bug where km was not being converted to mi in USian mode.
#      - Added a downward trend analysis to wind speed/velocity.
#      - Added some measuring units-specific preprocessing code to the file
#        writer routine.  This includes some rounding to a reasonable number
#        of decimal places.
# v1.1 - I should have been updating this but I was too busy debugging the
#        bot and getting used to a new job to remember.  My bad.
#      - Added the file writer plugin.
#      - Deleted some debugging output that was commented out anyway.
#      - Started using the schedule module to run methods periodically.
#      - Reworked the temperature, pressure, and humidity alerts to tell the
#        user what they bounced to.
#      - Added periodic alerting of the wind direction so that it's actually
#        doing something useful.
#      - At long last, figured out how to add a crash handler.
# v1.0 - Initial release.

# TO-DO:
# - Develop a template module that makes it easy for a user to develop new
#   modules.  Also develop documentation that describes all of the changes
#   that will have to be made to integrate them.
# - Add support for configuring the sensors from the config file.
# - Add more comments that tell where to add code for new modules.
# - Wind kicks up by 1 sigma + rain == there's a storm?  Add code to do this.
# - Refactor the bme280 code because it's getting pretty out of control.

# Load modules.
import argparse
import configparser
import json
import logging
import os
import requests
import schedule
import statistics
import sys
import time

from linear_regression.lr import lr

import conversions
import file_writer
import parser

# Global variables.
# Handle to an argument parser object.
argparser = None

# Handle to the parsed arguments.
args = None

# Path to a configuration file.
config_file = ""

# Handle to a configuration file parser.
config = None

# Name of the bot.
bot_name = ""

# URL of the message queue to pull orders from.
message_queue = ""

# Loglevel to emit messages at.
config_log = ""

# Number of seconds in between pings to the message queue.
polling_time = 0

# Time (in seconds) between polling the various status markers.  This should be
# a fraction of the message queue poll time, perhaps 20-25%, with a hardwired
# value if it's too small (it would be four seconds or less, so default to five
# seconds?)
status_polling = 0

# Number of standard deviations to consider noteworthy as changes of weather
# conditions.
standard_deviations = 0

# Minimum and maximum lengths of the weather condition queues.  Default to 10
# unless it's set in the config file.
minimum_length = 10
maximum_length = 10

# Configuration for the logger.
loglevel = None

# Path to a text file and the number of seconds to write values to it.
write_file = ""
write_file_seconds = 0

# Multiple of polling_time that must pass between sending alerts.  Defaults to
# 3600 seconds (one hour).
time_between_alerts = 3600

# Scratch variables that hold a linear regression object and the slope of a
# calculated linear regression.
analysis = None
slope = 0.0

# Possible sensors comprising the weather station.
anemometer = False
bme280 = False
raingauge = False
weathervane = False

# Data from the sensors.
anemometer_data = {}
bme280_data = {}
raingauge_data = {}
weathervane_data = {}

# Reference array that represents the time axis of a graph.  For statistical
# analysis elsewhere in the bot core.
reference_array = []

# Lists of data samples from the sensors.
anemometer_samples = []
bme280_temperature_samples = []
bme280_pressure_samples = []
bme280_humidity_samples = []
raingauge_samples = []

# Average readings from the sensors.
average_wind_velocity = 0.0
average_temperature = 0.0
average_air_pressure = 0.0
average_humidity = 0.0

# Imperial or metric? (imperial/metric)
units = "metric"

# Counters used to keep track of when notices are sent to the bot's owner.
anemometer_counter = 0
bme280_counter = 0
raingauge_counter = 0
weathervane_counter = 0

# Functions.
# set_loglevel(): Turn a string into a numerical value which Python's logging
#   module can use because.
def set_loglevel(loglevel):
    if loglevel == "critical":
        return 50
    if loglevel == "error":
        return 40
    if loglevel == "warning":
        return 30
    if loglevel == "info":
        return 20
    if loglevel == "debug":
        return 10
    if loglevel == "notset":
        return 0

# send_message_to_user(): Function that does the work of sending messages back
# to the user by way of the XMPP bridge.  Takes one argument, the message to
#   send to the user.  Returns a True or False which delineates whether or not
#   it worked.
def send_message_to_user(message):
    # Headers the XMPP bridge looks for for the message to be valid.
    headers = {"Content-type": "application/json"}

    # Set up a hash table of stuff that is used to build the HTTP request to
    # the XMPP bridge.
    reply = {}
    reply["name"] = bot_name
    reply["reply"] = message

    # Send an HTTP request to the XMPP bridge containing the message for the
    # user.
    request = requests.put(server + "replies", headers=headers,
        data=json.dumps(reply))
    return

# online_help(): Function that returns text - online help - to the user.  Takes
#   no arguments, returns a complex string.
def online_help():
    logger.debug("Entered the function online_help().")
    message = "My name is " + bot_name + " and I am an instance of " + sys.argv[0] + ".\n\n"

    message = message + "I continually monitor inputs from multiple weather sensors connected to the system I am running on.  I can return specific data points upon request or I can send alerts when weather conditions change significantly.  The interactive commands I currently support are:\n\n"
    message = message + "    help - Display this online help\n"

    if anemometer:
        message = message + "    wind speed\n"
    if bme280:
        message = message + "    temperature/temp\n"
        message = message + "    air pressure/atmospheric pressure/barometric pressure/pressure\n"
        message = message + "    relative humidity/air humidity/humidity\n"
    if raingauge:
        message = message + "    rain gauge/raining/is it raining\n"
    if weathervane:
        message = message + "    wind direction/direction\n"
    if write_file:
        message = message + "\n"
        message = message + "The file writer plugin is enabled, and writes data points to " + write_file + " every " + str(write_file_seconds) + " seconds."
    return message

# poll_anemometer(): Breakout function for sampling data from the anemometer.
def poll_anemometer():
    logging.debug("Entered poll_anemometer().")

    std_dev = 0
    global anemometer_samples
    global anemometer_counter

    anemometer_data = anemometer.get_wind_speed()
    logging.debug(str(anemometer_data))

    # Save the running tally of wind velocities.
    anemometer_samples.append(anemometer_data["velocity_km_h"])
    if len(anemometer_samples) > maximum_length:
        anemometer_samples.pop(0)

    # Calculate average wind velocity if we have enough samples.
    if len(anemometer_samples) >= minimum_length:
        average_wind_velocity = statistics.mean(anemometer_samples)
        average_wind_velocity = round(average_wind_velocity, 2)
        logging.debug("The average wind velocity is %s kph." %
            average_wind_velocity)

    # Calculate the standard deviation of the data from the anemometer if
    # we have enough samples.
    if len(anemometer_samples) >= minimum_length:
        std_dev = statistics.stdev(anemometer_samples)
        logging.debug("Calculated standard deviation of wind velocity: %s" %
            std_dev)

        if std_dev >= standard_deviations:
            msg = "poll_anemometer() -> standard deviation of wind velocity"

            # Round it to make it look nice.
            std_dev = round(std_dev, 1)

            if units == "metric":
                msg = "The wind velocity has jumped by " + str(std_dev) +  " standard deviations to " + str(anemometer_samples[-1]) + " kph.  The weather might be getting bad."
            if units == "imperial":
                msg = "The wind speed has jumped by " + str(std_dev) +  " standard deviations to " + str(conversions.km_to_mi(anemometer_samples[-1])) + " mph.  The weather might be getting bad."

            # If time_between_alerts is 0, alerting is disabled.
            if time_between_alerts:
                if anemometer_counter >= time_between_alerts:
                    send_message_to_user(msg)

    # Do a trend analysis of wind speed to determine if it's increasing.
    if len(anemometer_samples) >= maximum_length:
        logging.debug("Calculating linear regression of wind speed.")
        analysis = lr(anemometer_samples, reference_array)
        msg = ""

        # This is the slope of a line that intercepts the origin (0, 0)
        # instead of wherever the line would naturally be graphed.  Because
        # the data points are always rolling forward one array entry per
        # cycle, and we always start looking from array[0], this gives
        # us the result we want.
        slope = analysis.slope00

        # This might not be the right way to do it, but I think for the
        # moment I can repurpose the number of standard deviations from
        # the config file to detect a noteworthy upward trend.
        if slope >= float(standard_deviations):
            msg = "The wind appears to be blowing noticeably harder.  "
            msg = msg + "It is now blowing at " + str(anemometer_samples[-1])
            if units == "metric":
                msg = msg + " kilometers per hour."
            if units == "imperial":
                msg = msg + " miles per hour."

        if slope < float(standard_deviations):
            msg = "The wind appears to be blowing not quite as hard.  "
            msg = msg + "It is now blowing at " + str(anemometer_samples[-1])
            if units == "metric":
                msg = msg + " kilometers per hour."
            if units == "imperial":
                msg = msg + " miles per hour."

        # If time_between_alerts is 0, alerting is disabled.
        if time_between_alerts:
            if anemometer_counter >= time_between_alerts:
                if msg:
                    send_message_to_user(msg)

    # Housekeeping: Update the "don't spam the user" counters.
    if anemometer_counter >= time_between_alerts:
        anemometer_counter = 0
    else:
        anemometer_counter = anemometer_counter + status_polling
    return

# poll_bme280(): Breakout function for sampling data from the BME280 multi-
#   sensor.
def poll_bme280():
    logging.debug("Entered poll_bme280().")

    std_dev = 0
    global bme280_temperature_samples
    global bme280_pressure_samples
    global bme280_humidity_samples
    global bme280_counter

    bme280_data = bme280.get_reading()
    logging.debug(str(bme280_data))

    # Save running tallies of data points.
    bme280_temperature_samples.append(bme280_data["temp_c"])
    if len(bme280_temperature_samples) > maximum_length:
        bme280_temperature_samples.pop(0)

    bme280_pressure_samples.append(bme280_data["pressure"])
    if len(bme280_pressure_samples) > maximum_length:
        bme280_pressure_samples.pop(0)

    bme280_humidity_samples.append(bme280_data["humidity"])
    if len(bme280_humidity_samples) > maximum_length:
        bme280_humidity_samples.pop(0)

    # Calculate averages if we have enough samples.
    if len(bme280_temperature_samples) >= minimum_length:
        average_temperature = statistics.mean(bme280_temperature_samples)
        average_temperature = round(average_temperature, 2)
        logging.debug("The average temperature is %s degrees C." %
            average_temperature)

    if len(bme280_pressure_samples) >= minimum_length:
        average_pressure = statistics.mean(bme280_pressure_samples)
        average_pressure = round(average_pressure, 2)
        logging.debug("The average barometric pressure is %s hPa." %
            average_pressure)

    if len(bme280_humidity_samples) >= minimum_length:
        average_humidity = statistics.mean(bme280_humidity_samples)
        average_humidity = round(average_humidity, 2)
        logging.debug("The average humidity is %s percent." %
            average_humidity)

    # Calculate standard deviations to see if anything weird is going on.
    if len(bme280_temperature_samples) >= minimum_length:
        msg = ""

        std_dev = statistics.stdev(bme280_temperature_samples)
        std_dev = round(std_dev, 1)
        logging.debug("Calculated standard deviation of temperature: %s" %
            std_dev)
        if std_dev >= standard_deviations:
            msg = "The temperature has jumped by " + str(std_dev) + " standard deviations, to "
            temp = bme280_temperature_samples[-1]
            if units == "imperial":
                msg = msg + str(conversions.c_to_f(temp))
                msg = msg + " degrees Fahrenheit."
            if units == "metric":
                msg = msg + str(temp)
                msg = msg + " degrees Centigrade."

            if time_between_alerts:
                if bme280_counter >= time_between_alerts:
                    send_message_to_user(msg)

    if len(bme280_pressure_samples) >= minimum_length:
        msg = ""

        std_dev = statistics.stdev(bme280_pressure_samples)
        std_dev = round(std_dev, 1)
        logging.debug("Calculated standard deviation of barometric pressure: %s" % std_dev)
        if std_dev >= standard_deviations:
            msg = "The air pressure has jumped by " + str(std_dev) + " standard deviations, to "

            if units == "metric":
                msg = msg + str(bme280_pressure_samples[-1])
                msg = msg + " hPa."
            if units == "imperial":
                msg = msg + str(conversions.hpa_to_inhg(bme280_pressure_samples[-1]))
                msg = msg + " inHg."

            if time_between_alerts:
                if bme280_counter >= time_between_alerts:
                    send_message_to_user(msg)

    if len(bme280_humidity_samples) >= minimum_length:
        msg = ""

        std_dev = statistics.stdev(bme280_humidity_samples)
        std_dev = round(std_dev, 1)
        logging.debug("Calculated standard deviation of relative humidity: %s"
            % std_dev)
        if std_dev >= standard_deviations:
            msg = "The humidity has jumped by " + str(std_dev) + " standard deviations, to " + str(bme280_humidity_samples[-1]) + "% relative."
            if time_between_alerts:
                if bme280_counter >= time_between_alerts:
                    send_message_to_user(msg)

    # Do a trend analysis of air pressure to make educated guesses about
    # where the weather might be going.
    if len(bme280_pressure_samples) >= maximum_length:
        logging.debug("Calculating linear regression of barometric pressure.")
        msg = ""
        analysis = lr(bme280_pressure_samples, reference_array)
        slope = analysis.slope00

        # Barometric pressure trending up (positive slope).
        if slope >= 1.0:
            msg = "The barometric pressure is trending upward.  That usually means that the weather's going to be pretty nice."

        # Air pressure trending down (negative slope).
        if slope < 0.0:
            msg = "The barometric pressure is trending downward.  That usually means that the weather's going to get kind of lousy."

        # If time_between_alerts is 0, alerting is disabled.
        # Send the message.
        if time_between_alerts:
            if bme280_counter >= time_between_alerts:
                if msg:
                    send_message_to_user(msg)

    # Housekeeping: Update the "don't spam the user" counters.
    if bme280_counter >= time_between_alerts:
        bme280_counter = 0
    else:
        bme280_counter = bme280_counter + status_polling
    return

# poll_raingauge(): Breakout function for sampling data from the raingauge.
def poll_raingauge():
    logging.debug("Entered poll_raingauge().")

    stddev = 0
    global raingauge_samples
    global raingauge_counter

    raingauge_data = raingauge.get_precip()
    logging.debug(str(raingauge_data))

    # Save the running tally of precipitation measurements.
    raingauge_samples.append(raingauge_data["mm"])
    if len(raingauge_samples) > maximum_length:
        raingauge_samples.pop(0)

    # Do a trend analysis to detect when it starts and stops raining
    if len(raingauge_samples) >= maximum_length:
        logging.debug("Calculating linear regression of rain gauge samples.")
        msg = ""
        analysis = lr(raingauge_samples, reference_array)
        slope = analysis.slope00

        # Precipitation samples trending up.
        if slope >= 1.0:
            msg = "The amount of precipitation the raingauge is detecting is trending up.  Is it raining?"

        # Precipitation samples trending down.
        if slope < 0.0:
            msg = "The amount of precipitation the raingauge is detecting is trending downward.  I think the rain's slowing down."

        # If time_between_alerts is 0, alerting is disabled.
        # Send the message.
        if time_between_alerts:
            if raingauge_counter >= time_between_alerts:
                if msg:
                    send_message_to_user(msg)

    # Housekeeping: Update the "don't spam the user" counters.
    if raingauge_counter >= time_between_alerts:
        raingauge_counter = 0
    else:
        raingauge_counter = raingauge_counter + status_polling
    return()

# poll_weathervane(): Wrapper function that polls a weather vane attached to
#   the system.
def poll_weathervane():
    logging.debug("Entered poll_weathervane().")

    global weathervane_counter

    logging.debug("Polling weather vane.")
    weathervane_data = weathervane.get_direction()
    logging.debug("Data from weather vane: %s" % weathervane_data)

    # If time_between_alerts is 0, alerting is disabled.
    # Send the message.
    if time_between_alerts:
        msg = ""
        if weathervane_counter >= time_between_alerts:

            # Catch the odd value of None for weathervane_data.
            if weathervane_data:
                msg = "The wind is blowing " + str(weathervane_data) + "ward."
            if msg:
                send_message_to_user(msg)

    # Housekeeping: Update the "don't spam the user" counters.
    if weathervane_counter >= time_between_alerts:
        weathervane_counter = 0
    else:
        weathervane_counter = weathervane_counter + status_polling
    return()

# contact_message_queue(): Function that pings the bot's message queue on the
#   XMPP bridge, looks for interactive commands, parses them, and handles
#   them.
def contact_message_queue():
    command = ""
    request = None

    try:
        logger.debug("Contacting message queue: " + message_queue)
        request = requests.get(message_queue)
        logger.debug("Response from server: " + request.text)
    except:
        logger.warn("Connection attempt to message queue timed out or failed.  Going back to sleep to try again later.")
        return()

    # Test the HTTP response code.
    # Success.
    if request.status_code == 200:
        logger.debug("Message queue " + bot_name + " found.")

        # Extract the command.
        command = json.loads(request.text)
        logger.debug("Command from user: " + str(command))
        command = command["command"]
        if not command:
            logger.debug("Empty command.")
            return()

        # Parse the command.
        command = parser.parse_command(command)
        logger.debug("Parsed command: " + str(command))

        # If the user is requesting online help...
        if command == "help":
            send_message_to_user(online_help())
            return()

        # If the user is requesting wind speed...
        if command == "speed":
            wind_speed = anemometer.get_wind_speed()
            msg = "main() do-stuff loop -> get anemometer wind speed"
            if units == "imperial":
                msg = "The current wind speed is "
                msg = msg + str(round(conversions.km_to_mi(wind_speed["velocity_km_h"]), 2))
                msg = msg + " miles per hour."
            if units == "metric":
                msg = "The current wind velocity is " + str(round(wind_speed["velocity_km_h"], 2)) + " kilometers per hour."
            send_message_to_user(msg)
            return()

        # If the user is requesting wind direction...
        if command == "direction":
            wind_direction = weathervane.get_direction()
            if wind_direction:
                send_message_to_user("The wind is blowing %sward." % wind_direction)
            else:
                send_message_to_user("The wind doesn't seem to be blowing.")
            return()

        # If the user is requesting the current temperature...
        if command == "temp":
            temp = bme280.get_reading()
            temp = temp["temp_c"]
            msg = "The current temperature is "
            if units == "imperial":
                msg = msg + str(round(conversions.c_to_f(temp), 1))
                msg = msg + " degrees Fahrenheit."
            if units == "metric":
                msg = msg + str(round(temp, 1))
                msg = msg + " degrees Centigrade."
            send_message_to_user(msg)
            return()

        # If the user is requesting the barometric pressure...
        if command == "pressure":
            pressure = bme280.get_reading()
            msg = "The current barometric pressure is "
            if units == "imperial":
                msg = msg + str(round(conversions.hpa_to_inhg(pressure["pressure"]), 1))
                msg = msg + " inHg."
            if units == "metric":
                msg = msg + str(round(pressure["pressure"], 1))
                msg = msg + " hPa."
            send_message_to_user(msg)
            return()

        # If the user is requesting the humidity...
        if command == "humidity":
            humidity = bme280.get_reading()
            msg = "The current humidity is "
            msg = msg + str(humidity["humidity"])
            msg = msg + " %."
            send_message_to_user(msg)
            return()

        # If the user is requesting the state of the rain gauge...
        if command == "rain":
            rain = raingauge.get_precip()
            msg = "main() do-stuff loop -> get precipitation"

            # If it's not raining, or if there is so little precipitation
            # that rounding the sensor sample is 0.0, account for that.
            if not rain["mm"]:
                msg = "If it's raining, it's so light that the sensor isn't picking it up."
            else:
                msg = "The measurement the rain gauge took during the last sample period was "
                if units == "imperial":
                    msg = msg + str(conversions.mm_to_in(rain["mm"])) + " inches "
                if units == "metric":
                    msg = msg + str(rain["mm"]) + " millimeters "
                msg = msg + "of rain."
            send_message_to_user(msg)
            return()

        # Fall-through.
        if command == "unknown":
            msg = "I didn't recognize that command."
            send_message_to_user(msg)
            return()

# write_file_handler(): This is a wrapper function that calls file_writer to
#   store readings in a text file.  Because some external software has specific
#   requirements (such as USian units only), this is done in two stages.
#   First, set local variables to appropriate values and units.  Then send them
#   on to the file writer module.  I could probably do it in a more Pythonic
#   manner, but this way is more self-documenting and easier to maintain later.
def write_file_handler():
    logging.debug("Entered write_file_handler().")

    # Local variables are explicitly declared here because otherwise their
    # scopes are limited to the conditionals in which they appear.
    anemometer = 0.0
    temperature = 0.0
    pressure = 0.0
    rain = 0.0

    # Wind speed.
    if units == "imperial":
        anemometer = conversions.km_to_mi(anemometer_samples[-1])
    if units == "metric":
        anemometer = anemometer_samples[-1]
    anemometer = round(anemometer, 2)
    logging.debug("Value of anemometer: %s" % anemometer)

    # Temperature.
    if units == "imperial":
        temperature = conversions.c_to_f(bme280_temperature_samples[-1])
    if units == "metric":
        temperature = bme280_temperature_samples[-1]
    temperature = round(temperature, 2)
    logging.debug("Value of temperature: %s" % temperature)

    # Pressure.
    if units == "imperial":
        pressure = conversions.hpa_to_inhg(bme280_pressure_samples[-1])
    if units == "metric":
        pressure = bme280_pressure_samples[-1]
    pressure = round(pressure, 2)
    logging.debug("Value of pressure: %s" % pressure)

    # Humidity is a percentage, that's sorted.
    logging.debug("Value of humidity: %s" % bme280_humidity_samples[-1])

    # Rain.
    if units == "imperial":
        rain = conversions.mm_to_in(raingauge_samples[-1])
    if units == "metric":
        rain = raingauge_samples[-1]
    rain = round(rain, 2)
    logging.debug("Value of pressure: %s" % pressure)

    # Wind direction is a string, that's sorted.

    file_writer.write_values_to_file(write_file,
        anemometer=anemometer,
        temperature=temperature,
        pressure=pressure,
        humidity=bme280_humidity_samples[-1],
        rain=rain,
        wind_direction=weathervane.get_direction())
    return()

# scream_and_die(): A function that is registered with the sys.excepthook()
#   handler, and fires if and when the bot crashes.
def scream_and_die(type, value, traceback):
    logging.critical("Crash handler executed!")
    send_message_to_user("AAAAAAHHHH!")
    send_message_to_user("FC: So much for that robot.  Too bad.")

# Core code...
# Allocate a command-line argument parser.
argparser = argparse.ArgumentParser(description="A bot that monitors weather sensors attached to the system and sends alerts via the XMPP bridge as appropriate.")

# Set the default config file and the option to set a new one.
argparser.add_argument("--config", action="store",
    default="./weather_station_bot.conf")

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument("--loglevel", action="store",
    help="Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.")

# Time (in seconds) between polling the message queues.
argparser.add_argument("--polling", action="store", help="Default: 60 seconds")

# Time (in seconds) in between sending warnings to the user.
argparser.add_argument("--time-between-alerts", action="store",
    help="Time in seconds in between sending warnings to the user.  This is to prevent getting flooded with alerts.")

# Whether or not to list the configured sensors and exit.
argparser.add_argument("--list-sensors", action="store_true",
    help="Print the list of sensors the bot recognized from the config file and exit.")

# Use imperial units instead?
argparser.add_argument("--imperial", action="store_const", const="imperial",
    help="Use imperial units instead of metric.")

# Parse the command line arguments.
args = argparser.parse_args()
if args.config:
    config_file = args.config

# Read the options in the configuration file before processing overrides on the
# command line.
config = configparser.ConfigParser()
if not os.path.exists(config_file):
    logging.error("Unable to find or open configuration file " +
        config_file + ".")
    sys.exit(1)
config.read(config_file)

# Get the URL of the message queue to contact.
server = config.get("DEFAULT", "queue")

# Get the name of the message queue to report to.
bot_name = config.get("DEFAULT", "bot_name")

# Construct the full message queue name.
message_queue = server + bot_name

# Get the default loglevel of the bot.
config_log = config.get("DEFAULT", "loglevel").lower()
if config_log:
    loglevel = set_loglevel(config_log)

# Set the number of seconds to wait in between polling runs on the message
# queues.
try:
    polling_time = int(config.get("DEFAULT", "polling_time"))
except:
    # Nothing to do here, it's an optional configuration setting.
    pass

# Get the time between alerts (in seconds) from the config file.
time_between_alerts = int(config.get("DEFAULT", "time_between_alerts"))

# Anemometer
try:
    # If this is not boolean-False, it will be replaced by the module
    # import.
    anemometer = config.get("DEFAULT", "anemometer")
    import anemometer
except:
    logging.debug("Anemometer not enabled in config file.")
    pass

# BME280 multi-sensor
try:
    # If this is not boolean-False, it will be replaced by the module
    # import.
    bme280 = config.get("DEFAULT", "bme280")
    import bme280_sensor as bme280
except:
    logging.debug("BME280 sensor not enabled in config file.")
    pass

# Rain gauge
try:
    # If this is not boolean-False, it will be replaced by the module
    # import.
    raingauge = config.get("DEFAULT", "raingauge")
    import rainfall_gauge as raingauge
except:
    logging.debug("Raingauge not enabled in config file.")
    pass

# Weather vane
try:
    # If this is not boolean-False, it will be replaced by the module
    # import.
    weathervane = config.get("DEFAULT", "weathervane")
    import weathervane
except:
    logging.debug("Weather vane not enabled in config file.")
    pass

# MOOF MOOF MOOF - modules for additional sensors go here.

# Get the number of standard deviations from the config file.
standard_deviations = int(config.get("DEFAULT", "standard_deviations"))

# Get the minimum and maximum lengths of the stat queues from the config file.
# Used for calculating some sudden changes in weather, such as the temperature
# falling or the barometric pressure suddenly rising.
minimum_length = int(config.get("DEFAULT", "minimum_length"))
maximum_length = int(config.get("DEFAULT", "maximum_length"))

# See if the file output writer is enabled in the config file.
try:
    write_file = config.get("DEFAULT", "write_file")
except:
    logging.debug("File writing not enabled in config file.")
    pass

# Now see if the "write to the file every X seconds" setting is there.
try:
    write_file_seconds = int(config.get("DEFAULT", "write_file_seconds"))
except:
    logging.debug("write_file_seconds not set.  Disabling file writing.")
    write_file = ""
    pass

# Set the measurement system from the config file.
units = config.get("DEFAULT", "units")
if units == "amu":
    print("American meat units mode activated.  Fire up the grill!")
    units = "imperial"

# Set the loglevel from the override on the command line.
if args.loglevel:
    loglevel = set_loglevel(args.loglevel.lower())

# Set the measurement type from the override on the command line.
if args.imperial:
    units = "imperial"

# Configure the logger.
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Set the message queue polling time from override on the command line.
if args.polling:
    polling_time = args.polling

# Set the time between system alerts if set on the command line.
if args.time_between_alerts:
    time_between_alerts = int(args.time_between_alerts)

# Calculate how often the bot checks the sensors.  This is how often the
# main loop runs.
status_polling = polling_time / 2

# print a list of sensors the bot recognizes from the config file.
if args.list_sensors:
    print("These are the sensors the bot recognizes from the config file:")
    if anemometer:
        print("    * Anemometer")
    if bme280:
        print("    * BME280 multi-sensor")
    if raingauge:
        print("    * Rain gauge")
    if weathervane:
        print("    * Weather vane")
    # MOOF MOOF MOOF - additional modules will be referenced here
    sys.exit(1)

# In debugging mode, dump the bot's configuration.
logger.info("Everything is configured.")
logger.debug("Values of configuration variables as of right now:")
logger.debug("Configuration file: %s" % config_file)
logger.debug("Server to report to: %s" % server)
logger.debug("Message queue to report to: %s" % message_queue)
logger.debug("Bot name to respond to search requests with: %s" % bot_name)
logger.debug("Number of standard deviations: %s" % standard_deviations)
logger.debug("Minimum stat queue length: %s" % minimum_length)
logger.debug("Maximum stat queue length: %s" % maximum_length)
logger.debug("Value of polling_time (in seconds): %s" % polling_time)
if time_between_alerts == 0:
    logger.info("time_between_alerts is set to 0 - system alerting disabled!")
else:
    logger.debug("Value of time_between_alerts (in seconds): %s" % time_between_alerts)
logger.debug("Value of status_polling (in seconds): %s" % status_polling)
logger.debug("Measurement units: %s" % units )
if write_file:
    logger.debug("Value of write_file: %s" % write_file)
if write_file_seconds:
    logger.debug("Value of write_file_seconds: %s" % write_file_seconds)
logger.debug("Sensors enabled:")
if anemometer:
    logger.debug("    * Anemometer")
if bme280:
    logger.debug("    * BME280 multi-sensor")
if raingauge:
    logger.debug("    * Rain gauge")
if weathervane:
    logger.debug("    * Weather vane")

# Set the crash handler.
sys.excepthook = scream_and_die
logger.debug("scream_and_die() set as sys.excepthook crash handler.")

# Try to contact the XMPP bridge.  Keep trying until you reach it or the
# system shuts down.
logger.info("Trying to contact XMPP message bridge...")
while True:
    try:
        send_message_to_user(bot_name + " now online.")
        break
    except:
        logger.warning("Unable to reach message bus.  Going to try again in %s seconds." % polling_time)
        time.sleep(float(polling_time))

# Build out the reference array for statistical analysis.
logger.debug("Building out reference_array.")
for i in range(0, maximum_length):
    reference_array.append(i)

# Line up the schedule of functions to run and when.
if anemometer:
    schedule.every(status_polling).seconds.do(poll_anemometer)
if bme280:
    schedule.every(status_polling).seconds.do(poll_bme280)
if raingauge:
    schedule.every(status_polling).seconds.do(poll_raingauge)
if weathervane:
    schedule.every(status_polling).seconds.do(poll_weathervane)
if write_file:
    schedule.every(write_file_seconds).seconds.do(write_file_handler)
schedule.every(polling_time).seconds.do(contact_message_queue)

# Go into a loop in which the bot polls the configured message queue to see
# if it has any HTTP requests waiting for it.
logger.debug("Entering main loop and running the scheduler.")
while True:
    schedule.run_pending()
    time.sleep(1)

# Fin.
sys.exit(0)
