#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# environment_monitor.py - This is an experimental bot which implements
#   the software side of an environment monitoring system based around (at
#   the moment) the AHT-20 temperature/humidity sensor from Adafruit
#   (https://adafru.it/4566).  It's experimental because I'm prototyping
#   sensors using a Raspberry Pi right now, and eventually want to build a
#   variant which runs entirely on a Circuit Python-based microcontroller.
#   This prototype uses the adafruit-blinka compatibility layer.
#
# Temperatures are read in degrees Centigrade from the sensor.  So, they
# will need to be converted to other scales depending upon what the user
# has configured.

#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# - Split the "send the temperature" and "send the humidity" code off into
#   separate functions.
# -

# Load modules.
import adafruit_ahtx0
import argparse
import board
import ConfigParser
import json
import logging
import os
import requests
import sys
import time

# Constants.
# When POSTing something to a service, the correct Content-Type value has to
# be set in the request.
custom_headers = {"Content-Type": "application/json:"}

# Global variables.
# Handle to a logging object.
logger = ""

# Path to and name of the configuration file.
config_file = ""

# Loglevel for the bot.
loglevel = logging.INFO

# The "http://system:port/" part of the message queue URL.
server = ""

# URL to the message queue to take marching orders from.
message_queue = ""

# The name the search bot will respond to.  The idea is, this bot can be
# instantiated any number of times with different config files to use
# different search engines on different networks.
bot_name = ""

# How often to poll the message queues for orders.
polling_time = 30

# What temperature scale to use.  Defaults to Fahrenheit.
scale = "fahrenheit"

# Temperature from the sensor.
temperature = 0.0

# String that holds the command from the user prior to parsing.
user_command = None

# Handle to a parsed user command.
parsed_command = None

# Devices found in /dev.
devices = []
device = ""
i2c_found = False

# Group that owns the I2C devices.
group = ""

# Handle to a sensor on the board.
sensor = None

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

# parse_...(): Takes a string and figures out if it was a correctly
#   formatted request to...  Requests
#   are of the form "..".  Returns ...
#   or None if it's not a well-formed request.
def parse_...(user_command):
    logger.debug("Entered function parse_...().")
    words = []

    # Clean up the search request.
    user_command = user_command.strip()
    user_command = user_command.strip(",")
    user_command = user_command.strip(".")
    user_command = user_command.strip("'")

    # If the user command is empty (i.e., nothing in the queue) return None.
    if "no commands" in user_command:
        logging.debug("Got an empty index request.")
        return None

    # Tokenize the search request.
    words = user_command.split()
    logging.debug("Tokenized index request: " + str(words))

    # Start parsing the the index request to see what kind it is.  After
    # making the determination, remove the words we've sussed out to make the
    # rest of the query easier.

    # User asked for help.
    if not len(words):
        return None
    if words[0].lower() == "help":
        logging.debug("User asked for online help.")
        return words[0]

    # User asked the construct to...
    if (words[0] == "foo") or (words[0] == "bar") or \
            (words[0] == "baz"):
        logging.info("Got a token that suggests that this is...")
    del words[0]

    # If the parsed search term is now empty, return an error.
    if not len(words):
        logging.error("The indexing request appears to be empty.")
        return None

    # The above, one or more times...

    # Return the final result.
    logging.debug("Final result: " + something_final_result)
    return something_final_result

# send_message_to_user(): Function that does the work of sending messages back
#   to the user by way of the XMPP bridge.  Takes one argument, the message to
#   send to the user.  Returns a True or False which delineates whether or not
#   it worked.
def send_message_to_user(message):
    # Set up a hash table of stuff that is used to build the HTTP request to
    # the XMPP bridge.
    reply = {}
    reply["name"] = bot_name
    reply["reply"] = message

    # Send an HTTP request to the XMPP bridge containing the message for the
    # user.
    request = requests.put(server + "replies", headers=custom_headers,
        data=json.dumps(reply))
    return

# online_help(): Utility function that sends online help to the user when
#   requested.  Takes no args.  Returns nothing.
def online_help():
    reply = "My name is " + bot_name + " and I am an instance of " + sys.argv[0] + ".\n\n"
    reply = reply + """I am... send me a message that looks something like this:\n\n"""
    reply = reply + bot_name + ", [command, synonym, synonym...] args...\n\n"
    reply = reply + bot_name + ", [command, synonym, synonym...] args...\n\n"
    reply = reply + bot_name + ", [command, synonym, synonym...] args...\n\n"
    send_message_to_user(reply)
    return

# centigrade_to_fahrenheit():  Function that takes the current temperature
#   from the environment sensor in degrees Centigrade and converts it to
#   degrees Fahrenheit.
def centigrade_to_fahrenheit(temperature):
    fahrenheit = (float(temperature) * 9/5) + 32.0
    return(fahrenheit)

# centigrade_to_kelvin(): Function that takes the current temperature from
#   the environment sensor in degrees Centigrade and converts it to degrees
#   Kelvin.
def centigrade_to_kelvin(temperature):
    kelvin = float(temperature) + 273.15
    return(kelvin)

# Core code...
# Set up the command line argument parser.
argparser = argparse.ArgumentParser(description="A bot that interfaces with an environment monitoring peripheral and keeps tabs on the temperature and relative humidty.  It reports to the user over the XMPP bridge.")

# Set the default config file and the option to set a new one.
argparser.add_argument("--config", action="store",
    default="./environment-monitor.conf")

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument("--loglevel", action="store",
    help="Valid log levels: critical, error, warning, info, debug, notset.  Defaults to info.")

# Time (in seconds) between polling the message queues.
argparser.add_argument("--polling", action="store", help="Default: 30 seconds")

# Temperature scale the user wants to use.
argparser.add_argument("--scale", action="store", default="fahrenheit",
    help="Possible temperature scales: fahrenheit, celsius, kelvin")

# Parse the command line arguments.
args = argparser.parse_args()
if args.config:
    config_file = args.config

# Read the options in the configuration file before processing overrides on the
# command line.
config = ConfigParser.ConfigParser()
if not os.path.exists(config_file):
    logging.error("Unable to find or open configuration file " +
        config_file + ".")
    sys.exit(1)
config.read(config_file)

# Get the URL of the message queue to contact.
server = config.get("DEFAULT", "queue")

# Get the names of the message queues to report to.
bot_name = config.get("DEFAULT", "bot_name")

# Construct the full message queue URL.
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

# Set the loglevel from the override on the command line.
if args.loglevel:
    loglevel = set_loglevel(args.loglevel.lower())

# Configure the logger.
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Set the message queue polling time from override on the command line.
if args.polling:
    polling_time = args.polling

# Parse the rest of the configuration file...
scale = config.get("DEFAULT", "scale")
if args.scale:
    scale = args.scale
scale = scale.lower()

# Debugging output, if required.
logging.info("Everything is set up.")
logging.debug("Values of configuration variables as of right now:")
logging.debug("Configuration file: " + config_file)
logging.debug("Server to report to: " + server)
logging.debug("Message queue to report to: " + message_queue)
logging.debug("Bot name to respond to search requests with: " + bot_name)
logging.debug("Time in seconds for polling the message queue: " +
    str(polling_time))
logging.debug("Temperature scale: %s" % scale)

# Try to contact the XMPP bridge.  Keep trying until you reach it or the
# system shuts down.
logging.info("Trying to contact XMPP message bridge...")
while True:
    try:
        send_message_to_user(bot_name + " now online.")
        break
    except:
        logging.warning("Unable to reach message bus.  Going to try again in %s seconds." % polling_time)
        time.sleep(float(polling_time))

# Make sure the /dev/i2c* devices exist.  If not, complain over the XMPP
# bridge and ABEND.
devices = os.listdir("/dev")
for device in devices:
    if "i2c" in device:
        i2c_found = True
        logging.info("Found I2C device node %s." % device)
        break
if not i2c_found:
    logging.error("Walked all of /dev, didn't find any i2c* device nodes.")
    send_message_to_user("No I2C devices found.  Are you sure it's enabled?  Shutting down...")
    sys.exit(1)
logging.debug("I2C devices found in /dev.")

# Make sure the bot's user is in the group that owns the /dev/i2c* devices.
# If not, complain over the XMPP bridge and ABEND.
group = os.stat("/dev/" + str(device)).st_gid
if group not in os.getgroups():
    logging.error("The account the bot is running under doesn't have access to any devices in /dev/i2c-*.")
    send_message_to_user("The account I am running under does not belong to the group that owns the I2C devices.  It needs to be added to group %s." % str(group))
    sys.exit(1)
logging.debug("I think I can access the I2C devices.")

# Build access handles to the I2C sensors onboard.
sensor = adafruit_ahtx0.AHTx0(board.I2C())
logging.debug("Got access to I2C device %d." %
    sensor.i2c_device.device_address)
if sensor.calibrate():
    logging.debug("Sensor calibration sequence complete.")
else:
    logging.debug("Sensor calibration failed.")

# MOOF MOOF MOOF - Split this off into two separate functions.
# Send the initial environment stats to the user.
temperature = sensor.temperature
if scale == "fahrenheit":
    temperature = celsius_to_fahrenheit(temperature)
if scale == "kelvin":
    temperature = celsius_to_kelvin(temperature)
send_message_to_user("The current temperature is %0.1f degrees %s." %
    (temperature, scale.capitalize()))
send_message_to_user("The current relative humidity is %0.1f %%." %
    (sensor.relative_humidity))

# Go into a loop in which the bot polls the configured message queue with each
# of its configured names to see if it has any search requests waiting for it.
logging.debug("Entering main loop to handle requests.")
while True:
    user_command = None

    # Check the message queue for index requests.
    try:
        logging.debug("Contacting message queue: " + message_queue)
        request = requests.get(message_queue)
    except:
        logging.warning("Connection attempt to message queue timed out or failed.  Going back to sleep to try again later.")
        time.sleep(float(polling_time))
        continue

    # Test the HTTP response code.
    # Success.
    if request.status_code == 200:
        logging.debug("Message queue " + bot_name + " found.")

        # Extract the user command.
        user_command = json.loads(request.text)
        logging.debug("Value of user_command: " + str(user_command))
        user_command = user_command["command"]

        # Parse the user command.
        parsed_command = parse_...(user_command)

        # If the parsed command comes back None (i.e., it wasn't well formed)
        # throw an error and bounce to the top of the loop.
        if not parsed_command:
            time.sleep(float(polling_time))
            continue

        # If the user is requesting help, assemble a response and send it back
        # to the server's message queue.
        if parsed_command.lower() == "help":
            online_help()
            continue

        # Tell the user what the bot is about to do.
        reply = "Doing the thing.  Please stand by."
        send_message_to_user(reply)
        parsed_command = do_the_thing(parsed_command)

        # If something went wrong...
        if not parsed_command:
            logging.warning("Something went wrong with...")
            reply = "Something went wrong with..."
            send_message_to_user(reply)
            continue

        # Reply that it was successful.
        reply = "Tell the user that it was successful."
        send_message_to_user(reply)

    # Message queue not found.
    if request.status_code == 404:
        logging.info("Message queue " + bot_name + " does not exist.")

    # Sleep for the configured amount of time.
    time.sleep(float(polling_time))

# Fin.
sys.exit(0)
