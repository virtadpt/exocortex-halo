#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# smtp_bridge.py - A small server that pretends to be an SMTP server but
#   actually reformats all messages and forwards them over the configured XMPP
#   bridge server.  By default it only listens on the loopback address on port
#   25/tcp, but it can be configured differently.  Please note that the server
#   will need to be started as the root user if it's configured "normally" but
#   will automatically drop its privileges to nobody/nobody or nobody/nogroup
#   (also configurable because different distros use different UIDs and GIDs
#   for this).
#
#   Put all of your configuration options into a config file.  Treat this bot
#   just like any other SMTP server you might set up.

# By: The Doctor [412/724/301/703/415] <drwho at virtadpt dot net>

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:

# Load modules.
import argparse
import ConfigParser
import logging
import os.path
import sys

# Constants.

# Global variables.
# Handles to a command line argument parser and the parsed args.
argparser = None
args = None

# Handle to logger object.
logger = None

# Handle to a configuration file parser.
config = None

# Server-level configuration options.
loglevel = ""
smtphost = ""
smtpport = 0
queue = ""
username = ""
group = ""

# Classes.

# Functions.
# Figure out what to set the logging level to.  There isn't a straightforward
# way of doing this because Python uses constants that are actually integers
# under the hood, and I'd really like to be able to do something like
# loglevel = 'logging.' + loglevel
# I can't have a pony, either.  Takes a string, returns a Python loglevel.
def process_loglevel(loglevel):
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
argparser = argparse.ArgumentParser(description="A bot that implements an SMTP server for other processes on the system to relay mail through, but instead forwards those messages to the bot's owner via an instance of the Exocortex XMPP Bridge.")

# Set the default config file and the option to set a new one.
argparser.add_argument("--config", action="store", default="./smtp_bridge.conf")

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument("--loglevel", action="store", default="info",
    help="Valid log levels: critical, error, warning, info, debug, notset.  Defaults to info.")

# Parse the command line arguments.
args = argparser.parse_args()

# Read and parse the configuration file.
config = ConfigParser.ConfigParser()
if not os.path.exists(args.config):
    logging.error("Unable to find or open configuration file " +
        args.config + ".")
    sys.exit(1)
config.read(args.config)

# Set global config options.
queue = config.get("DEFAULT", "queue")
loglevel = config.get("DEFAULT", "loglevel")
smtphost = config.get("DEFAULT", "smtphost")
smtpport = config.get("DEFAULT", "smtpport")
username = config.get("DEFAULT", "username")
group = config.get("DEFAULT", "group")

# Figure out how to configure the logger.
if args.loglevel:
    loglevel = process_loglevel(args.loglevel.lower())
else:
    loglevel = process_loglevel(loglevel.lower())
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Print debugging output.
logger.info("SMTP bridge is configured and running.")
logger.debug("Runtime configuration settings:")
logger.debug("Configuration file: " + args.config)
logger.debug("Message queue: " + queue)
logger.debug("SMTP host: " + str(smtphost))
logger.debug("SMTP port: " + str(smtpport) + "/tcp")
logger.debug("Username to drop privileges to: " + str(username))
logger.debug("Group to drop privileges to: " + str(group))

# Fin.
sys.exit(0)
