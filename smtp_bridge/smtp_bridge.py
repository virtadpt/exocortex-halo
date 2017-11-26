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

# By: The Doctor [412/724/301/703/415] <drwho at virtadpt dot net>

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:

# Load modules.
import argparse
import logging
import sys

# Constants.

# Global variables.
# Handles to a command line argument parser and the parsed args.
argparser = None
args = None

# Handles to logger object and configuration.
loglevel = None
logger = None

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

# Set up the hostname to listen for SMTP connections on.
argparser.add_argument("--listenhost", action="store", default="localhost",
    help="Specify the hostname to listen on for SMTP connections.  Defaults to localhost.")

# Set up the port to listen on for SMTP traffic.
argparser.add_argument("--listenport", action="store", default=25,
    help="Specify the network port to listen on for SMTP traffic.  Defaults to 25/tcp.")

# Set up the hostname of the XMPP bridge to contact.
argparser.add_argument("--hostname", action="store", default="localhost",
    help="Specify the hostname of an XMPP bridge to contact.  Defaults to localhost.")

# Set up the port of the XMPP bridge to contact.
argparser.add_argument("--port", action="store", default=8003,
    help="Specify the network port of an XMPP bridge to contact.  Defaults to 8003/tcp.")

# Define the name of a message queue to send messages to.
argparser.add_argument("--queue", action="store", default="replies",
    help="Specify a message queue of an XMPP bridge to contact.  Defaults to /replies.")

# Define the name of the user to drop privileges to.
argparser.add_argument("--username", action="store", default="nobody",
    help="Specify a username to drop privileges to.  Defaults to 'nobody'.")

# Define the name of the group to drop privileges to.
argparser.add_argument("--group", action="store", default="nogroup",
    help="Specify a group name to drop privileges to.  Defaults to 'nogroup'.")

# Parse the command line arguments.
args = argparser.parse_args()

# Figure out how to configure the logger.
if args.loglevel:
    loglevel = process_loglevel(args.loglevel.lower())
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

print args

# Fin.
sys.exit(0)
