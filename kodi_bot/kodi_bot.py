#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# kodi_bot.py - Bot written in Python that interfaces with a Kodi instance and
#   acts as a remote control for audio and video playback.  For forward
#   compatibility, this bot uses kodipydent
#   (https://github.com/haikuginger/kodipydent) because it's designed to adapt
#   to new Kodi JSON-RPC API versions.
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
import requests
import sys
import time

from kodipydent import Kodi

import parser

# Constants.

# When POSTing something to a service, the correct Content-Type value has to
# be set in the request.
custom_headers = {'Content-Type': 'application/json'}

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
polling_time = 10

# String that holds the command from the user prior to parsing.
user_command = None

# Handle to a parsed user command.
parsed_command = None

# Kodi connection information.
kodi_host = ""
kodi_port = 0
kodi_user = ""
kodi_password = ""

# Directories containing media.
media_dirs = []

# Directory containing text files to front-load the parser with.
corpora_dir = ""

# Minimum statistical confidence in a match.  Defaults to 25 out of 100.
minimum_confidence = 25

# Handle to a Kodi client connection.
kodi = None

# Types of commands the bot can parse and act on.
command_types_tmp = []
command_types = {}

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
    reply["name"] = bot_name
    reply["reply"] = message

    # Send an HTTP request to the XMPP bridge containing the message for the
    # user.
    request = requests.put(server + "replies", headers=headers,
        data=json.dumps(reply))

# Core code... let's do this.

# Set up the command line argument parser.
argparser = argparse.ArgumentParser(description="A bot that interfaces with a Kodi media server.  It can run searches on the media library as well as send commands to the server.")

# Set the default config file and the option to set a new one.
argparser.add_argument("--config", action="store",
    default="./kodi_bot.conf")

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument("--loglevel", action="store",
    help="Valid log levels: critical, error, warning, info, debug, notset.  Defaults to info.")

# Time (in seconds) between polling the message queues.
argparser.add_argument("--polling", action="store", help="Default: 10 seconds")

# Parse the command line arguments.
args = argparser.parse_args()
if args.config:
    config_file = args.config

# Read the options in the configuration file before processing overrides on the
# command line.
config = ConfigParser.ConfigParser()
if not os.path.exists(config_file):
    logging.error("Unable to find or open configuration file %s." % config_file)
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
# Get the Kodi configuration information.
kodi_host = config.get("DEFAULT", "kodi_host")
kodi_port = config.get("DEFAULT", "kodi_port")
kodi_user = config.get("DEFAULT", "kodi_user")
kodi_password = config.get("DEFAULT", "kodi_password")
media_dirs = config.get("DEFAULT", "media_dirs").split(",")
corpora_dir = config.get("DEFAULT", "corpora_dir")
minimum_confidence = config.get("DEFAULT", "minimum_confidence")
command_types_tmp = config.get("DEFAULT", "command_types").split(",")

# Debugging output, if required.
logger.info("Everything is set up.")
logger.debug("Values of configuration variables as of right now:")
logger.debug("Configuration file: %s" % config_file)
logger.debug("Server to report to: %s" % server)
logger.debug("Message queue to report to: %s" % message_queue)
logger.debug("Bot name to respond to search requests with: %s" % bot_name)
logger.debug("Time in seconds for polling the message queue: %d" % polling_time)
logger.debug("Kodi host: %s" % kodi_host)
logger.debug("Kodi port: %s" % kodi_port)
logger.debug("Kodi username: %s" % kodi_user)
logger.debug("Kodi password: %s" % kodi_password)
logger.debug("Kodi media directories: %s" % media_dirs)
logger.debug("Corpora to train the parser with: %s" % corpora_dir)

# Connect to a Kodi instance.
try:
    kodi = Kodi(kodi_host, port=int(kodi_port), username=kodi_user,
        password=kodi_password)
except:
    logger.error("Unable to connect to Kodi instance at %s:%d/tcp with username %s and password %s.  Please check your configuration file." % (kodi_host, kodi_port, kodi_user, kodi_password))
    sys.exit(1)

# Load the corpora.
corpora_dir = os.path.abspath(corpora_dir)
for i in command_types_tmp:
    command_types[i] = []
# Now we have a hash table where the keys are categories of commands to run
# and the values are empty lists.
for filename in os.listdir(corpora_dir):

    # Generate the key for the hash.
    command_type = filename.strip(".txt")

    # Test the length of the corpus file.  If it's 0, then skip the command
    # class.
    if not os.path.getsize(filename):
        logger.warn("Corpus filename %s has a length of zero bytes.  Skipping this command class." % filename)
        command_types.pop(command_type)
        continue

    # Read the contents of the corpus file in.
    try:
        with open(filename, "r") as file:
            command_types[command_type] = file.read().splitlines()
    except:
        logger.warn("Unable to open filename %s.  Skipping command class." % os.path.join(corpora_dir, filename))
        command_types.pop(command_type)
logger.debug("Recognized command types: %s" % str(command_types))

# Load the media library from Kodi.

# Go into a loop in which the bot polls the configured message queue with each
# of its configured names to see if it has any search requests waiting for it.
logger.debug("Entering main loop to handle requests.")
send_message_to_user(bot_name + " now online.")
while True:
    user_command = None

    # Check the message queue for index requests.
    try:
        logger.debug("Contacting message queue: %s" % message_queue)
        request = requests.get(message_queue)
    except:
        logger.warn("Connection attempt to message queue timed out or failed.  Going back to sleep to try again later.")
        time.sleep(float(polling_time))
        continue

    # Test the HTTP response code.
    # Success.
    if request.status_code == 200:
        logger.debug("Message queue %s found." % bot_name)

        # Extract the user command.
        user_command = json.loads(request.text)
        logger.debug("Value of user_command: %s" % user_command)
        user_command = user_command["command"]

        # Parse the user command.
        parsed_command = parser.parse(user_command)

        # If the parsed command comes back None (i.e., it wasn't well formed)
        # throw an error and bounce to the top of the loop.
        if not parsed_command:
            time.sleep(float(polling_time))
            continue

        # If the user is requesting help, assemble a response and send it back
        # to the server's message queue.
        if parsed_command == "help":
            reply = "My name is " + bot_name + " and I am an instance of " + sys.argv[0] + ".\n"
            reply = reply + """I am... send me a message that looks something like this:\n\n"""
            reply = reply + bot_name + ", [command, synonym, synonym...] args...\n\n"
            reply = reply + bot_name + ", [command, synonym, synonym...] args...\n\n"
            reply = reply + bot_name + ", [command, synonym, synonym...] args...\n\n"
            send_message_to_user(reply)
            continue

        # Tell the user what the bot is about to do.
        reply = "Doing the thing.  Please stand by."
        send_message_to_user(reply)
        parsed_command = do_the_thing(parsed_command)

        # If something went wrong...
        if not parsed_command:
            logger.warn("Something went wrong with...")
            reply = "Something went wrong with..."
            send_message_to_user(reply)
            continue

        # Reply that it was successful.
        reply = "Tell the user that it was successful."
        send_message_to_user(reply)

    # Message queue not found.
    if request.status_code == 404:
        logger.info("Message queue %s does not exist." % bot_name)

    # Sleep for the configured amount of time.
    time.sleep(float(polling_time))

# Fin.
sys.exit(0)
