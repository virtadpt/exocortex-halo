#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# copy_bot.py - Bot written in Python that copies one or more files from one
#   location to another on the host the bot is running on.  This is a tool bot,
#   the uses of which are left up to the user.
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

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
import os.path
import requests
import sys
import time

import parser

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

# Handle to a copy request from the user.
copy_request = None

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

# single_file_copy(): Function that takes as its argument a hash table
#   containing two filespecs, one a file to copy from, the other a filename
#   or directory to copy into.
def single_file_copy(filespecs):
    logger.debug("Entered function copy_files().")

    # Return the result.
    return result

# multiple_file_copy(): Function that takes as its argument a hash table
#   containing two filespecs, one a set of files to copy from or a directory
#   to copy the contents of, the other a directory to copy them into.
def multiple_file_copy(filespecs):
    logger.debug("Entered function multiple_file_copy().")

    # Return the result.
    return result

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

# online_help(): Function that returns text - online help - to the user.  Takes
#   no arguments, returns a complex string.
def online_help():
    logger.debug("Entered the function online_help().")
    message = "My name is " + bot_name + " and I am an instance of " + sys.argv[0] + ".\n"
    message = message + """
    I am designed to remotely copy one or more files from one location on the hot I am running on to another location on the host.  This is a potentially useful thing to do if used in a clever fashion.  The interactive commands I currently suppot are:

    help - Display this online help.

    Individual files:
    copy /path/to/foo.txt to /another/path/to(/bar.txt)
    copy /path/to/foo.txt into /another/path/to(/bar.txt)
    copy from /path/to/foo.txt to /another/path/to(/bar.txt)
    copy from /path/to/foo.txt into /another/path/to(/bar.txt)

    Contents of a directory:
    copy /path/to/ to /another/path
    copy /path/to into /another/path/to
    copy everything in /path/to/foo to /another/path
    copy everything in /path/to/foo into /another/path
    copy * in /path/to/foo to /another/path
    copy * in /path/to/foo into /another/path
    copy all files in /path/to/foo to /another/path
    copy all files in /path/to/foo into /another/path
    """
    return message

# Core code...

# Set up the command line argument parser.
argparser = argparse.ArgumentParser(description="A toolbot that accepts two filespecs from the user, one for one or more files to copy from, the other a filename or destination directory to copy into.")

# Set the default config file and the option to set a new one.
argparser.add_argument('--config', action='store', 
    default='./tool_bot.conf')

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument('--loglevel', action='store',
    help='Valid log levels: critical, error, warning, info, debug, notset.  Defaults to info.')

# Time (in seconds) between polling the message queues.
argparser.add_argument('--polling', action='store', help='Default: 30 seconds')

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

# Normalize the download directory.
# MOOF MOOF MOOF - Re-use this code elsewhere before deleting it!
download_directory = os.path.abspath(os.path.expanduser(download_directory))

# Ensure the download directory exists.
# MOOF MOOF MOOF - Re-use this code elsewhere before deleting it!
if not os.path.exists(download_directory):
    print "ERROR: Download directory " + download_directory + "does not exist."
    sys.exit(1)

# Ensure that the bot can write to the download directory.
# MOOF MOOF MOOF - Re-use this code elsewhere before deleting it!
if not os.access(download_directory, os.R_OK):
    print "ERROR: Unable to read contents of directory " + download_directory
    sys.exit(1)
if not os.access(download_directory, os.W_OK):
    print "ERROR: Unable to write to directory " + download_directory
    sys.exit(1)

# Set the loglevel from the override on the command line.
if args.loglevel:
    loglevel = set_loglevel(args.loglevel.lower())

# Configure the logger.
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Set the message queue polling time from override on the command line.
if args.polling:
    polling_time = args.polling

# Debugging output, if required.
logger.info("Everything is set up.")
logger.debug("Values of configuration variables as of right now:")
logger.debug("Configuration file: " + config_file)
logger.debug("Server to report to: " + server)
logger.debug("Message queue to report to: " + message_queue)
logger.debug("Bot name to respond to search requests with: " + bot_name)
logger.debug("Time in seconds for polling the message queue: " +
    str(polling_time))

# Go into a loop in which the bot polls the configured message queue with each
# of its configured names to see if it has any download requests waiting for it.
logger.debug("Entering main loop to handle requests.")
send_message_to_user(bot_name + " now online.")
while True:
    command = None

    # Check the message queue for download requests.
    try:
        logger.debug("Contacting message queue: " + message_queue)
        request = requests.get(message_queue)
    except:
        logger.warn("Connection attempt to message queue timed out or failed.  Going back to sleep to try again later.")
        time.sleep(float(polling_time))
        continue

    # Test the HTTP response code.
    # Success.
    if request.status_code == 200:
        logger.debug("Message queue " + bot_name + " found.")

        # Extract the download request.
        command = json.loads(request.text)
        logger.debug("Value of command: " + str(command))
        command = command['command']
        if not command:
            logger.debug("Empty command.")
            time.sleep(float(polling_time))
            continue

        # Parse the command.
        command = parser.parse_command(command)
        logger.debug("Parsed command: " + str(command))

        # If the user is requesting online help...
        if command == "help":
            send_message_to_user(online_help())

        # If the user is requesting a single file copy.
        if command['type'] == "single":
            single_file_copy(command)

        # If the user is requesting a multiple file copy.
        if command['type'] == "multiple":
            multiple_file_copy(command)

        if command == "unknown":
            message = "I didn't recognize that command."
            send_message_to_user(message)

    # Message queue not found.
    if request.status_code == 404:
        logger.info("Message queue " + bot_name + " does not exist.")

    # Sleep for the configured amount of time.
    time.sleep(float(polling_time))

# Fin.
sys.exit(0)

