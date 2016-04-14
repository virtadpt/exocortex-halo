#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# paywall_breaker.py - A construct that, when given orders to do so, downloads
#   a web page while pretending to be a search engine's indexing spider, parses
#   the HTML to extract the salient stuff (i.e., the body of the page), and
#   archives it to a local Etherpad-Lite instance to read later.
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:

# Load modules.
import argparse
import ConfigParser
import logging
import os
import sys

# Constants.

# Global variables.
# Handle to an argument parser object.
argparser = None

# Handle to the parsed arguments.
args = None

# Path to a configuration file.
config_file = ""

# Handle to a configuration file parser.
config = None

# URL of the message queue to pull orders from.
queue = ""

# Name of the construct.
bot_name = ""

# Default e-mail to send messages to.
default_email = ""

# Loglevel to emit messages at.
config_log = ""

# Number of seconds in between pings to the message queue.
polling_time = 0

# Hostname of the SMTP server to use to send messages to the bot's user.
smtp_server = "localhost"

# Originating e-mail address the construct will use to identify itself.
origin_email_address = ""

# URL and API key of the Etherpad-Lite instance to use as an archive.
etherpad_url = ""
etherpad_api_key = ""

# Handle to the configuration file section containing user agent strings.
user_agent_strings = None

# Name of the search engine whose user-agent string is in the config file.
search_engine = ""

# List of search engine user agents to spoof when making requests.
user_agents = []

# Important parts of the web page that we want to extract and save.
head = ""
title = ""
body = ""

# String which holds the message to the user when the job is done.
message = ""

# Classes.

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

# Core code...
# Set up the command line argument parser.
argparser = argparse.ArgumentParser(description='A construct that polls a message queue for the URLs of paywalled web pages, tries to download the pages, copies them into an archive, and sends the results to a destination.')

# Set the default config file and the option to set a new one.
argparser.add_argument('--config', action='store', 
    default='./paywall_breaker.conf')

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument('--loglevel', action='store',
    help='Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.')

# Time (in seconds) between polling the message queues.
argparser.add_argument('--polling', action='store', default=60,
    help='Default: 60 seconds')

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
message_queue = config.get("DEFAULT", "queue")

# Get the name of the message queue to report to.
bot_name = config.get("DEFAULT", "bot_name")

# Construct the full message queue name.
message_queue = message_queue + bot_name

# Get the default e-mail address.
default_email = config.get("DEFAULT", "default_email")

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

# Get the SMTP server to send search results through from the config file if
# it's been set.
try:
    smtp_server = config.get("DEFAULT", "smtp_server")
except:
    # Nothing to do here, it's an optional configuration setting.
    pass

# Get the e-mail address that search results will be sent from.
origin_email_address = config.get("DEFAULT", "origin_email_address")

# Set the loglevel from the override on the command line.
if args.loglevel:
    loglevel = set_loglevel(args.loglevel.lower())

# Configure the logger.
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Set the message queue polling time from override on the command line.
if args.polling:
    polling_time = args.polling

# Get the URL of the Etherpad-Lite instance to contact.
etherpad_url = config.get("DEFAULT", "etherpad_url")

# Get the API key of the Etherpad-Lite instance.
etherpad_api_key = config.get("DEFAULT", "etherpad_api_key")

# Get the list of user agents from the configuration file and load them into
# a list.
user_agent_strings = config.items("user agents")
for search_engine, user_agent in user_agent_strings:
    if "engine" in search_engine:
        user_agents.append(user_agent)

# Debugging output, if required.
logger.info("Everything is configured.")
logger.debug("Values of configuration variables as of right now:")
logger.debug("Configuration file: " + config_file)
logger.debug("Message queue to report to: " + message_queue)
logger.debug("Bot name to respond to search requests with: " + bot_name)
logger.debug("Default e-mail address to send results to: " + default_email)
logger.debug("Time in seconds for polling the message queue: " +
    str(polling_time))
logger.debug("SMTP server to send search results through: " + smtp_server)
logger.debug("E-mail address that search results are sent from: " +
    origin_email_address)
logger.debug("URL of the Etherpad-Lite instance: " + etherpad_url)
logger.debug("API key for the Etherpad-Lite instance: " + etherpad_api_key)
logging.debug("User agents that will be spoofed: " + str(user_agents))



# Fin.
sys.exit(0)

