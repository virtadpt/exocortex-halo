#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# shaarli_bot.py - Bot written in Python that acts as an interface to Shaarli
#   (https://github.com/shaarli/Shaarli).  This sounds like a party trick, but
#   Shaarli is flexible enough that it has some non-obvious use cases, such
#   as storing (and sharing) notes instead of links, it can act as a card
#   catalogue for various forms of media, and probably some other things that
#   I haven't tried yet.  Basically, if you want to search and get results
#   sent back to you, this is an interface for it.  The use case I'm designing
#   for is answering questions of the form "Do I have anything about /foo/?"
#   or "Do I have anything by /bar/?"
#
#   Uses the REST API (https://shaarli.github.io/api-documentation/).
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v2.2 - Reworked the startup logic so that being unable to immediately
#       connect to either the message bus or the intended service is a
#       terminal state.  Instead, it loops and sleeps until it connects and
#       alerts the user appropriately.
#       - Moved the user-defined text closer to the top, like the other bots.
# v2.1 - Added user-definable text to the help and about-to-do-stuff parts.
#       - Changed the default polling time to 10 seconds, because this bot
#        won't be run on a Commodore 64...
# v2.0 - Ported to Python 3.
# v1.1 - Added the URL of the configured Shaarli instance to the help text.
# v1.0 - Initial release.

# TO-DO:
# - Split off online help into its own function.

# Load modules.
import argparse
import configparser
import json
import logging
import os
import requests
import sys
import time

import parser
import search

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

# URL to a Shaarli instance.
shaarli_url = ""

# Shaarli API secret.
api_secret = ""

# String that holds the command from the user prior to parsing.
user_command = None

# Handle to a parsed user command.
parsed_command = None

# Handle to a search result from Shaarli.
search_results = None

# Optional user-defined text strings for the online help and user interaction.
user_text = None

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

# clean_up_user_command(): Takes a string from the user, cleans it up, and
#   returns it for processing.
def clean_up_user_command(user_command):
    logger.debug("Entered function clean_up_user_command().")

    user_command = user_command.strip()
    user_command = user_command.strip(",")
    user_command = user_command.strip(".")
    user_command = user_command.strip("'")
    user_command = user_command.lower()

    return user_command

# send_message_to_user(): Function that does the work of sending messages back
# to the user by way of the XMPP bridge.  Takes one argument, the message to
#   send to the user.  Returns a True or False which delineates whether or not
#   it worked.
def send_message_to_user(message):
    # Headers the XMPP bridge looks for for the message to be valid.
    headers = {}
    headers["Content-type"] = "application/json"

    # Set up a hash table of stuff that is used to build the HTTP request to
    # the XMPP bridge.
    reply = {}
    reply["name"] = bot_name
    reply["reply"] = message

    # Send an HTTP request to the XMPP bridge containing the message for the
    # user.
    try:
        request = requests.put(server + "replies", headers=headers,
            data=json.dumps(reply).encode())
    except:
        logging.error("I wasn't able to contact the XMPP bridge.  Something went wrong.")
    return

# Core code...
# Set up the command line argument parser.
argparser = argparse.ArgumentParser(description="A bot that polls a message queue for search requests to an instance of Shaarli.")

# Set the default config file and the option to set a new one.
argparser.add_argument("--config", action="store", default="./shaarli_bot.conf")

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

# Get user-defined doing-stuff text if defined in the config file.
try:
    user_text = config.get("DEFAULT", "user_text")
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

# Get the URL to the Shaarli instance.
shaarli_url = config.get("DEFAULT", "shaarli_url")

# Get the API secret set in the Shaarli instance.
api_secret = config.get("DEFAULT", "api_secret")

# Debugging output, if required.
logger.info("Everything is set up.")
logger.debug("Values of configuration variables as of right now:")
logger.debug("Configuration file: " + config_file)
logger.debug("Server to report to: " + server)
logger.debug("Message queue to report to: " + message_queue)
logger.debug("Bot name to respond to search requests with: " + bot_name)
logger.debug("Time in seconds for polling the message queue: " +
    str(polling_time))
logger.debug("URL of a Shaarli instance: " + shaarli_url)
logger.debug("Shaarli API secret: " + api_secret)
if user_text:
    logger.debug("User-defined help text: " + user_text)

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

# Go into a loop in which the bot polls the configured message queue with each
# of its configured names to see if it has any search requests waiting for it.
logger.debug("Entering main loop to handle requests.")
while True:
    user_command = None

    # Check the message queue for index requests.
    try:
        logger.debug("Contacting message queue: " + message_queue)
        request = requests.get(message_queue)
    except:
        logger.warning("Connection attempt to message queue timed out or failed.  Going back to sleep to try again later.")
        time.sleep(float(polling_time))
        continue

    # Test the HTTP response code.
    # Success.
    if request.status_code == 200:
        logger.debug("Message queue " + bot_name + " found.")

        # Extract the user command.
        user_command = json.loads(request.text)
        user_command = user_command["command"]
        user_command = clean_up_user_command(user_command)
        logger.debug("Value of user_command: " + str(user_command))

        # Parse the user command.
        parsed_command = parser.parse_command(user_command)

        # If the parsed command comes back None (i.e., it wasn't well formed)
        # throw an error and bounce to the top of the loop.
        if not parsed_command:
            time.sleep(float(polling_time))
            continue

        # If the user is requesting help, assemble a response and send it back
        # to the server's message queue.
        if parsed_command == "help":
            reply = "My name is " + bot_name + " and I am an instance of " + sys.argv[0] + ".\n\n"
            if user_text:
                reply = reply + user_text + "\n\n"
            reply = reply + "I am a bot which interfaces with a Shaarli instance to run searches and send back results.  I am interfaced with the following Shaarli instance: " + shaarli_url + "\n\n"
            reply = reply + "To run a search, send me a message that looks something like this:\n\n"
            reply = reply + bot_name + ", [search for] foo bar baz...\n\n"
            reply = reply + bot_name + ", [search tags, search tags for] [tag]\n\n"
            send_message_to_user(reply)
            continue

        if parsed_command == "unknown":
            reply = "I didn't understand that command.  Please try again."
            send_message_to_user(reply)
            continue

        # Use case: Search for a string in the title or the body of an entry.
        if parsed_command["type"] == "search text":
            reply = "Searching titles and text for the string ''" + str(parsed_command["search term"]) + "''"
            send_message_to_user(reply)
            search_results = search.search(parsed_command["search term"],
                shaarli_url, api_secret, "searchterm")
            if not len(search_results):
                reply = "I don't seem to have gotten any hits on that search."
            else:
                reply = "I seem to have gotten "
                if len(search_results) == 1:
                    reply = reply + "one hit"
                if len(search_results) > 1:
                    reply = reply + str(len(search_results)) + " hits"
                reply = reply + " on that search.\n\n"
                for i in search_results:
                    if i["title"]:
                        reply = reply + i["title"] + "\n"
                    if i["url"]:
                        reply = reply + i["url"] + "\n"
                    if i["description"]:
                        reply = reply + i["description"] + "\n"
                    if i["tags"]:
                        reply = reply + "Tags: " + ", ".join(i["tags"]) + "\n"
                    reply = reply + "\n"
            send_message_to_user(reply)
            continue

        # Use case: Search for a tag and return everything that has it.
        if parsed_command["type"] == "search tags":
            reply = "Searching for the tags ''" + str(parsed_command["search term"]) + "''"
            send_message_to_user(reply)
            search_results = search.search(parsed_command["search term"],
                shaarli_url, api_secret, "searchtags")
            if not len(search_results):
                reply = "I don't seem to have found anything that has those tags."
            else:
                reply = "I seem to have found "
                if len(search_results) == 1:
                    reply = reply + "one entry"
                if len(search_results) > 1:
                    reply = reply + str(len(search_results)) + " entries"
                reply = reply + " with that combination of tags.\n\n"
                for i in search_results:
                    if i["title"]:
                        reply = reply + i["title"] + "\n"
                    if i["url"]:
                        reply = reply + i["url"] + "\n"
                    if i["description"]:
                        reply = reply + i["description"] + "\n"
                    if i["tags"]:
                        reply = reply + "Tags: " + ", ".join(i["tags"]) + "\n"
                    reply = reply + "\n"
            send_message_to_user(reply)
            continue

    # Message queue not found.
    if request.status_code == 404:
        logger.info("Message queue " + bot_name + " does not exist.")

    # Sleep for the configured amount of time.
    time.sleep(float(polling_time))

# Fin.
sys.exit(0)
