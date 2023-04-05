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

# v1.0 - Initial release.

# TO-DO:
# - Develop a template module that makes it easy for a user to develop new
#   modules.  Also develop documentation that describes all of the changes
#   that will have to be made to integrate them.
# - Make the online help module dynamic; when the user asks for help, the list
#   of sensors that are active is printed.  This list needs to reflect the
#   enabled sensors.
# - Make it possible to run the bot with an argument like --list-sensors and
#   get a list of all of the configured sensors the bot knows about.

# Load modules.
import argparse
import configparser
import json
import logging
import os
import requests
import sys
import time

import globals
#import parser

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

# Minimum and maximum lengths of the weather condition queues.
minimum_length = 0
maximum_length = 0

# Configuration for the logger.
loglevel = None

# Used to determine when to poll the message queue.
loop_counter = 0

# Handle to a requests object.
request = None

# Command from the message queue.
command = ""

# Multiple of polling_time that must pass between sending alerts.  Defaults to
# 3600 seconds (one hour).
time_between_alerts = 3600

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
    message = "My name is " + bot_name + " and I am an instance of " + sys.argv[0] + ".\n"

    message = message + """
    I continually monitor inputs from multiple weather sensors physically attached to the system I am running on.  I can return specific data points upon request or I can send alerts when weather conditions change significantly.
    """

    # Continue building the help message.
    # MOOF MOOF MOOF - this needs to be dynamically generated.
    message = message + """
    I am configured for the following sensors at this time: foo bar baz
    """
    return message

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
    help="Time in seconds in between sending warnings to the user.  This is to prevent getting flooded with alerts when a big job runs.")

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
    polling_time = config.get("DEFAULT", "polling_time")
except:
    # Nothing to do here, it's an optional configuration setting.
    pass

# Get the time between alerts (in seconds) from the config file.
time_between_alerts = int(config.get("DEFAULT", "time_between_alerts"))

# Here is where the config file options that specify the sensors to use go.

# Get the number of standard deviations from the config file.
standard_deviations = config.get("DEFAULT", "standard_deviations")

# Get the minimum and maximum lengths of the stat queues from the config file.
# Used for calculating some sudden changes in weather, such as the temperature
# falling or the barometric pressure suddenly rising.
minimum_length = config.get("DEFAULT", "minimum_length")
maximum_length = config.get("DEFAULT", "maximum_length")

# Set the loglevel from the override on the command line.
if args.loglevel:
    loglevel = set_loglevel(args.loglevel.lower())

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
status_polling = int(polling_time) / 4

# In debugging mode, dump the bot'd configuration.
logger.info("Everything is configured.")
logger.debug("Values of configuration variables as of right now:")
logger.debug("Configuration file: " + config_file)
logger.debug("Server to report to: " + server)
logger.debug("Message queue to report to: " + message_queue)
logger.debug("Bot name to respond to search requests with: " + bot_name)
logger.debug("Number of standard deviations: " + str(standard_deviations))
logger.debug("Minimum stat queue length: " + str(minimum_length))
logger.debug("Maximum stat queue length: " + str(maximum_length))
logger.debug("Value of polling_time (in seconds): " + str(polling_time))
if time_between_alerts == 0:
    logger.info("time_between_alerts is set to 0 - system alerting disabled!")
else:
    logger.debug("Value of time_between_alerts (in seconds): " + str(time_between_alerts))
logger.debug("Value of loop_counter (in seconds): " + str(status_polling))

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

# Go into a loop in which the bot polls the configured message queue to see
# if it has any HTTP requests waiting for it.
logger.debug("Entering main loop to handle requests.")
while True:

    # Reset the command from the message bus, just in case.
    command = ""

    # Start checking the weather sensors.  If anything is too far out of
    # whack, send an alert via the XMPP bridge's response queue.
    # MOOF MOOF MOOF - I'm leaving the System Bot code in place as a reminder
    # of what this will look like, at least until I start writing actual
    # methods for the sensors I have right now.


    sysload_counter = system_stats.check_sysload(sysload_counter,
        time_between_alerts, status_polling, standard_deviations,
        minimum_length, maximum_length, send_message_to_user)
    cpu_idle_time_counter = system_stats.check_cpu_idle_time(
        cpu_idle_time_counter, time_between_alerts, status_polling,
        send_message_to_user)
    memory_free_counter = system_stats.check_memory_utilization(
        memory_free_counter, time_between_alerts, status_polling,
        memory_remaining, send_message_to_user)
    temperature_counter = system_stats.check_hardware_temperatures(
        temperature_counter, time_between_alerts, status_polling,
        standard_deviations, minimum_length, maximum_length,
        send_message_to_user)

    # Increment loop_counter by status_polling.
    loop_counter = loop_counter + status_polling

    # If loop_counter is equal to polling_time, check the message queue for
    # commands.
    if int(loop_counter) >= int(polling_time):
        try:
            logger.debug("Contacting message queue: " + message_queue)
            request = requests.get(message_queue)
            logger.debug("Response from server: " + request.text)
        except:
            logger.warn("Connection attempt to message queue timed out or failed.  Going back to sleep to try again later.")
            time.sleep(float(status_polling))
            continue

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
                logger.debug("Resetting loop_counter.")
                loop_counter = 0
                time.sleep(float(polling_time))
                continue

            # Parse the command.
            #command = parser.parse_command(command)
            #logger.debug("Parsed command: " + str(command))

            # If the user is requesting online help...
            #if command == "help":
            #    send_message_to_user(online_help())

            # If the user is requesting system load...
            # MOOF MOOF MOOF - this is how to handle a specific command.
            if command == "load":
                load = system_stats.sysload()
                message = "The current system load is " + str(load["one_minute"]) + " on the one minute average and " + str(load["five_minute"]) + " on the five minute average."
                send_message_to_user(message)

            # Fall-through.
            if command == "unknown":
                message = "I didn't recognize that command."
                send_message_to_user(message)

        # NOTE: We don't short-circuit all of the above checks with the
        # continue statement because we want the loop to fall down here every
        # time it runs to...
        # Reset loop counter.
        logger.debug("Resetting loop_counter.")
        loop_counter = 0

    # Bottom of loop.  Go to sleep for a while before running again.
    time.sleep(float(status_polling))

# Fin.
sys.exit(0)
