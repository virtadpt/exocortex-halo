#!/usr/bin/env python3
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

# v2.0 - Ported to Python 3.
# v1.0 - Initial release.

# TO-DO:
# - Refactor the bot to split out the file copying stuff.
# - Figure out how to specify a destination filename for single file copy.
#   That take a few more neurons than I have online at the moment.

# Load modules.
import argparse
import configparser
import json
import logging
import os
import os.path
import requests
import shutil
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

# normalize_file_path(): Normalizes a full path in the file system.  Takes one
#   argument, a string representing a full or partial path to a file.  Returns
#   a string representing a fully normalized path to a file.
def normalize_file_path(file):
    logger.debug("Entered function normalize_file_path().")
    logger.debug("Value of file: " + str(file))

    norm_path = os.path.expanduser(file)
    norm_path = os.path.abspath(norm_path)
    norm_path = os.path.normpath(norm_path)

    logger.debug("Normalized file path: " + str(norm_path))
    return norm_path

# ensure_exists(): Helper function that ensure that a file or directory
#   actually exists.  Returns a True or False.
def ensure_exists(file):
    logger.debug("Entered function ensure_exists().")
    if not os.path.exists(file):
        logger.debug("The file path " + str(file) + " does not exist.")
        return False
    else:
        logger.debug("The file path " + str(file) + " exists.")
        return True

# ensure_readable(): Helper function that ensure that a file or directory is
#   readable (has the +r bit). Returns a True or False.
def ensure_readable(file):
    logger.debug("Entered function ensure_readable().")
    if not os.access(file, os.R_OK):
        logger.debug("The file path " + str(file) + " cannot be read.")
        return False
    else:
        logger.debug("The file path " + str(file) + " is readable.")
        return True

# ensure_writable(): Helper function that ensure that a file or directory is
#   writable (has the +2 bit). Returns a True or False.
def ensure_writable(file):
    logger.debug("Entered function ensure_writable().")
    if not os.access(file, os.W_OK):
        logger.debug("The file path " + str(file) + " cannot be written to.")
        return False
    else:
        logger.debug("The file path " + str(file) + " is writable.")
        return True

# copy_files(): Function that takes as its argument a hash table containing two
#   filespecs, one a set of one or more files to copy (or a directory to copy
#   the contents of), the other a directory to copy them into.  Returns
#   a message to the user.
def copy_files(filespecs):
    logger.debug("Entered function copy_files().")

    # Message for the user.
    message = ""

    # List of files in the source directory to copy.
    source_files = []

    # List of files that could not be copied.
    uncopied_files = []

    # Normalize the file paths so they are internally consistent.
    source_path = normalize_file_path(filespecs['from'])
    destination_path = normalize_file_path(filespecs['to'])

    # Ensure the source filepath exists.
    if not ensure_exists(source_path):
        message = "ERROR: The source path " + str(source_path) + " does not exist.  I can't do anything."
        return message

    # Ensure the source can be read.  Bounce if it isn't.
    if not ensure_readable(source_path):
        message = "ERROR: The source path " + str(source_path) + " is not readable."
        return message

    # Ensure the destination directory exists.
    if not ensure_exists(destination_path):
        message = "ERROR: The destination path " + str(destination_path) + " does not exist.  I can't do anything."
        return message

    # Ensure that the destination is writable.  Note that it doesn't have to be
    # readable.  Bounce if it isn't.
    if not ensure_writable(destination_path):
        message = "ERROR: The destination path " + str(destination_path) + " cannot be written to."
        return message

    # Build a list of one or more files to copy in the source directory.
    if os.path.isfile(source_path):
        source_files.append(source_path)
    else:
        source_files = os.listdir(source_path)

    # Roll through the list of files, test them, and copy them.  If they can't
    # be copied push them onto the list of files that errored out.  We don't
    # test if the files exist because we pulled their filenames out of the
    # directory listing.
    for file in source_files:
        source_file = os.path.join(source_path, file)
        #source_file = normalize_file_path(source_file)

        if not ensure_readable(source_file):
            uncopied_files.append(file)
            continue

        try:
            logger.debug("Attempting to copy " + str(file) + " to " + str(destination_path) + ".")
            shutil.copy2(source_file, destination_path)
        except:
            uncopied_files.append(file)

    # Build the message to return to the user.
    message = "Contents of directory " + source_path + " are as copied as I can make them."
    if uncopied_files:
        message = message + "\nI was unable to copy the following files:\n"
        message = message + str(uncopied_files)
        logger.debug("Files that could not be copied: " + str(uncopied_files))

    # Return the message.
    return message

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

# online_help(): Function that returns text - online help - to the user.  Takes
#   no arguments, returns a complex string.
def online_help():
    logger.debug("Entered the function online_help().")
    message = "My name is " + bot_name + " and I am an instance of " + sys.argv[0] + ".\n"
    message = message + """
I am designed to remotely copy one or more files from one location on the hot I am running on to another location on the host.  When specifying files, please ensure that you specify as full a path as possible to the source file, because this bot defaults to its current working directory, which may not be what you want.  This is a potentially useful bot if used in a clever fashion.  The interactive commands I currently suppot are:

    help - Display this online help.

    Individual files:
    copy /path/to/foo.txt /another/path/to
    copy /path/to/foo.txt to /another/path/to
    copy /path/to/foo.txt into /another/path/to
    copy from /path/to/foo.txt to /another/path/to
    copy from /path/to/foo.txt into /another/path/to

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
argparser.add_argument("--config", action="store",
    default="./copy_bot.conf")

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument("--loglevel", action="store",
    help="Valid log levels: critical, error, warning, info, debug, notset.  Defaults to info.")

# Time (in seconds) between polling the message queues.
argparser.add_argument("--polling", action="store", help="Default: 30 seconds")

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

        # Extract the command.
        command = json.loads(request.text)
        command = command["command"]

        # Parse the command.
        command = parser.parse_command(command)
        logger.debug("Parsed command: " + str(command))

        # If the command was empty, return to the top of the loop.
        if not command:
            logger.debug("Empty command.")
            time.sleep(float(polling_time))
            continue

        if command == "unknown":
            message = "I didn't recognize that command."
            send_message_to_user(message)
            continue

        # If the user is requesting online help...
        if command == "help":
            send_message_to_user(online_help())
            continue

        # If the user is requesting a multiple file copy.
        if command['type'] == "copy":
            message = copy_files(command)
            send_message_to_user(message)
            continue

    # Message queue not found.
    if request.status_code == 404:
        logger.info("Message queue " + bot_name + " does not exist.")

    # Sleep for the configured amount of time.
    time.sleep(float(polling_time))

# Fin.
sys.exit(0)
