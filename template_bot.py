#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# template_bot.py - Bot written in Python that...
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v1.3 - Updated some comments and boilerplate.
#      - Changed ConfigParser to configparser, per Python 3 and PEP-8.
# v1.2 - Changed logging.warn() to logging.warning().
#      - Reworked the startup logic so that being unable to immediately
#      connect to either the message bus or the intended service is a
#      terminal state.  Instead, it loops and sleeps until it connects and
#      alerts the user appropriately.
#      - Changed logger to logging.
# v1.1 - Updated template to look more like the code I have in production.
#      - Added the facility for user-defined output.
# v1.0 - Initial release.

# TO-DO:
# -

# Load modules.
import argparse
import configparser
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
polling_time = 10

# String that holds the command from the user prior to parsing.
user_command = None

# Handle to a parsed user command.
parsed_command = None

# Optional user-defined text strings for the online help and user interaction.
user_text = None
user_acknowledged = None

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
        logging.debug("Got an empty command.")
        return None

    # Tokenize the search request.
    words = user_command.split()
    logging.debug("Tokenized command: " + str(words))

    # Start parsing the the command to see what kind it is.  After
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
    if user_text:
        reply = reply + user_text + "\n\n"
    reply = reply + """I am... send me a message that looks something like this:\n\n"""
    reply = reply + bot_name + ", [command, synonym, synonym...] args...\n\n"
    reply = reply + bot_name + ", [command, synonym, synonym...] args...\n\n"
    reply = reply + bot_name + ", [command, synonym, synonym...] args...\n\n"
    send_message_to_user(reply)
    return

# Core code...
# Set up the command line argument parser.
argparser = argparse.ArgumentParser(description="A bot that polls a message queue for...")

# Set the default config file and the option to set a new one.
argparser.add_argument("--config", action="store",
    default="./template_bot.conf")

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

# Get user-defined doing-stuff text if defined in the config file.
try:
    user_text = config.get("DEFAULT", "user_text")
except:
    # Nothing to do here, it's an optional configuration setting.
    pass

# Get additional user text if defined in the config file.
try:
    user_acknowledged = config.get("DEFAULT", "user_acknowledged")
except:
    # Nothing to do here, it's an optional configuration setting.
    pass

# Configure the logger.
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Set the message queue polling time from override on the command line.
if args.polling:
    polling_time = args.polling

# Parse the rest of the configuration file...

# Debugging output, if required.
logging.info("Everything is set up.")
logging.debug("Values of configuration variables as of right now:")
logging.debug("Configuration file: " + config_file)
logging.debug("Server to report to: " + server)
logging.debug("Message queue to report to: " + message_queue)
logging.debug("Bot name to respond to search requests with: " + bot_name)
logging.debug("Time in seconds for polling the message queue: " +
    str(polling_time))
if user_text:
    logging.debug("User-defined help text: " + user_text)
if user_acknowledged:
    logging.debug("User-defined command acknowledgement text: " + user_acknowledged)
# Other debugging output...

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

# Trying to contact other resources and sleeping if we can't (like the above)
# go here...

# Go into a loop in which the bot polls the configured message queue with each
# of its configured names to see if it has any search requests waiting for it.
logging.debug("Entering main loop to handle requests.")
while True:
    user_command = None

    # Check the message queue for commands.
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
        if user_acknowledged:
            send_message_to_user(user_acknowledged)
        else:
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
