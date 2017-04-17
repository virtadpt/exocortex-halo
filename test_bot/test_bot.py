#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# test_bot.py - A bot that just parrots back whatever text you send it.  This
#   bot is nothing more than a test for debugging certain kinds of other bots.

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# - 

# Load modules.
import argparse
import ConfigParser
import json
import logging
import os
import requests
import sys
import time

# Global variables.
# Handle to an argument parser object.
argparser = None

# Handle to the parsed arguments.
args = None

# Path to a configuration file.
config_file = ""

# Handle to a configuration file parser.
config = None

# The "http://system:port/" part of the message bus URL.
server = ""

# Name of the construct.
bot_name = ""

# URL of the message queue to pull orders from.
message_queue = ""

# Loglevel to emit messages at.
config_log = ""

# Number of seconds in between pings to the message queue.
polling_time = 0

# Configuration for the logger.
loglevel = None

# Handle to a requests object.
request = None

# Command from the message queue.
command = ""

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
    headers = {'Content-type': 'application/json'}

    # Set up a hash table of stuff that is used to build the HTTP request to
    # the XMPP bridge.
    reply = {}
    reply['name'] = bot_name
    reply['reply'] = message

    # Send an HTTP request to the XMPP bridge containing the message for the
    # user.
    request = requests.put(server + "replies", headers=headers,
        data=json.dumps(reply))
    return

# Core code...
# Allocate a command-line argument parser.
argparser = argparse.ArgumentParser(description="A construct that does nothing but listen for text from the user and echo it back.  This bot exists to help test certain other kinds of bots.  Maybe it'll be helpful for showing people how to write their own kinds of bots.")

# Set the default config file and the option to set a new one.
argparser.add_argument("--config", action="store", 
    default="./test_bot.conf")

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument("--loglevel", action="store",
    help="Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.")

# Time (in seconds) between polling the message queues.
argparser.add_argument("--polling", action="store", help="Default: 30 seconds")

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

# Set the loglevel from the override on the command line.
if args.loglevel:
    loglevel = set_loglevel(args.loglevel.lower())

# Configure the logger.
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Set the message queue polling time from override on the command line.
if args.polling:
    polling_time = args.polling

# In debugging mode, dump the bot'd configuration.
logger.info("Everything is configured.")
logger.debug("Values of configuration variables as of right now:")
logger.debug("Configuration file: " + config_file)
logger.debug("Server to report to: " + server)
logger.debug("Message queue to report to: " + message_queue)
logger.debug("Bot name to respond to search requests with: " + bot_name)

# Go into a loop in which the bot polls the configured message queue to see
# if it has any HTTP requests waiting for it.
logger.debug("Entering main loop to handle requests.")
send_message_to_user(bot_name + " now online.")
while True:

    # Reset the command from the message bus, just in case.
    command = ""

    # Check the message queue for commands.
    try:
        logger.debug("Contacting message queue: " + message_queue)
        request = requests.get(message_queue)
        logger.debug("Response from server: " + request.text)
    except:
        logger.warn("Connection attempt to message queue timed out or failed.  Going back to sleep to try again later.")
        time.sleep(float(polling_time))
        continue

    # Test the HTTP response code.
    # Success.
    if request.status_code == 200:
        logger.debug("Message queue " + bot_name + " found.")

        # Extract the command.
        command = json.loads(request.text)
        logger.debug("Command from user: " + str(command))
        command = command['command']
        if not command:
            logger.debug("Empty command.")
            time.sleep(float(polling_time))
            continue

        # Echo the command back to the user if something was actually sent.
        # We want to skip the "no commands" message that means that there was
        # nothing in the message queue.
        if "no commands" not in command:
            send_message_to_user("Message received.  You just told me:")
            send_message_to_user(command)
        else:
            logger.debug("Skipping the null command.  Telling you to keep you in the loop.")

    # Bottom of loop.  Go to sleep for a while before running again.
    time.sleep(float(polling_time))

# Fin.
sys.exit(0)

