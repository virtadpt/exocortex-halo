#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# web_search_bot.py - Bot written in Python that polls a RESTful message queue
#   for search commands of the form "<botname>, get me <number of hits> hits
#   for <search terms>", runs the searches on a number of search engines,
#   collates them, and POSTs them to a Huginn
#   (https://github.com/cantino/huginn) instances webhook so something can be
#   done with them.
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
import httplib
import logging
import os
import sys

# Constants.

# Global variables.
# Path to and name of the configuration file.
config_file = ""

# Loglevel for the bot.
loglevel = logging.INFO

# URL to the message queue to take marching orders from.
message_queue = ""

# Because this bot will have two possible modes, clearnet and darknet, it will
# report to two different message queues, one for each name.  At the very least,
# it needs a clearnet name but variables for both will be declared.
clearnet_name = ""
darknet_name = ""

# The webhook service the bot reports search results to requires an API key to
# authenticate with.
api_key = ""

# URL of the webhook service to send search results to.
webhook = ""

# How often to poll the message queues for orders.
polling_time = 0

# If this is a class or module, say what it is and what it does.

# Classes.

# Functions.
# set_loglevel(): Turn a string into a numerical value which Python's logging
#   module can use because.  Takes a string, returns a loglevel.
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
argparser = argparse.ArgumentParser(description='A bot that polls one or more message queues for commands, parses them, runs web searches in response, and sends the results to a destination.')

# Set the default config file and the option to set a new one.
argparser.add_argument('--config', action='store', 
    default='./web_search_bot.conf')

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument('--loglevel', action='store',
    help='Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.')

# Time (in seconds) between polling the message queues.
argparser.add_argument('--polling', action='store', default=60,
    help='Default: 60 seconds')
args = argparser.parse_args()

# Parse the command line arguments.
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

# Get the message queue to contact.
message_queue = config.get("DEFAULT", "queue")

# Get the names of the message queues to report to.
clearnet_name = config.get("DEFAULT", "clearnet_name")
try:
    darknet_name = config.get("DEFAULT", "darknet_name")
except:
    # Nothing to do here, it's an optional configuration setting.
    pass

# Get the API key used to authenticate to the webhook service.
api_key = config.get("DEFAULT", "api_key")

# Get the URL of the webhook to report to.
webhook = config.get("DEFAULT", "webhook")

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

# Set the message queue polling time from override on the command line.
if args.polling:
    polling_time = args.polling

# Fin.
sys.exit(0)

