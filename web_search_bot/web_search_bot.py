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
from optparse import OptionParser
import ConfigParser
import os
import logging

# Constants.

# Global variables.
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

# If this is a class or module, say what it is and what it does.

# Classes.

# Functions.
# get_command_line_arguments(): Sets up and parses the argument vector for
#   this bot.  Takes no arguments.  Returns a populated instance of
#   optparse.OptionParser.
def get_command_line_arguments():

    # Instantiate an argument vector parser.
    optionparser = OptionParser()

    # Lay out the command line switches the bot can accept.
    # Specify an arbitrary configuration file.
    optionparser.add_option("-c", "--conf", dest="config_file", action="store",
        type="string", help="Specify a path to a configuration file.  Defaults to ./web_search_bot.conf.")

    # Specify the default loglevel, overriding the configuration file setting.
    optionparser.add_option("-l", "--loglevel", dest="loglevel", action="store",
        help="Specify the default verbosity.  Valid options are CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET.  Defaults to INFO.")

    # Parse the command line arguments.
    (options, args) = optionparser.parse_args()

    # Return the parsed options.
    return options

# Core code...
# Get and parse command line arguments.
options = get_command_line_arguments()

# Read and parse the contents of the configuration file.
config = ConfigParser.ConfigParser()
if options.config_file:
    # Try to open the configuration file passed in the argument vector.
    if not os.path.exists(options.config_file):
        logging.error("Unable to find or open configuration file " + str(options.config_file) + ".")
        sys.exit(1)
    config.read(options.config_file)
else:
    # Try to open the default configuration file.
    if not os.path.exists('web_search_bot.conf'):
        logging.error("Unable to find or open default configuration file web_search_bot.conf.")
        sys.exit(1)
    config.read('web_search_bot.conf')

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

# Fin.
