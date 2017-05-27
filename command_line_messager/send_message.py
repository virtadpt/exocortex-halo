#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# send_message.py - A command line utility that sends arbitrary messages to a
#   running Exocortex XMPP Bridge.  This can be used for testing or for
#   situations in which a (relatively) simple task has not been turned into a
#   bot yet, but sending output via, say, SMTP is not feasible.

# By: The Doctor <drwho at virtadpt dot net>

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:

# Load modules.
import argparse
import json
import logging
import requests
import sys

# Constants.

# Global variables.
# Handle to an argument parser.
argparser = None

# Handle to parsed command line arguments.
args = None

# Loglevel for the tool.
loglevel = None

# URL of XMPP bridge to contact.  Assembled later.
message_queue = ""

# Hash table of custom headers that need to be sent to make it a valid request.
headers = {}

# Hash table that formats the message to send.
message = {}

# Handle to a requests object.
request = None

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
argparser = argparse.ArgumentParser(description="A command line utility which allows the user to send text or data to an instance of the Exocortex XMPP Bridge.  An ideal use case for this tool is to make interactive jobs communicate with the rest of an exocortex.")

# Set up the hostname of the XMPP bridge to contact.
argparser.add_argument('--hostname', action='store', default='localhost',
    help="Specify the hostname of an XMPP bridge to contact.  Defaults to localhost.")

# Set up the port of the XMPP bridge to contact.
argparser.add_argument('--port', action='store', default=8003,
    help="Specify the network port of an XMPP bridge to contact.  Defaults to 8003/tcp.")

# Define the name of a message queue to send messages to.
argparser.add_argument('--queue', action='store', default='replies',
    help="Specify a message queue of an XMPP bridge to contact.  Defaults to /replies.")

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument('--loglevel', action='store', default='info',
    help='Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.')

# Message to send.
argparser.add_argument('--message', action='store', nargs='*',
    help='Message to send to the XMPP bridge.')

# Parse the command line args.
args = argparser.parse_args()

# If there is no message to send, ABEND.
if not args.message:
    print "ERROR: You need to supply a message of some kind."
    sys.exit(1)

# Figure out how to configure the logger.
if args.loglevel:
    loglevel = process_loglevel(args.loglevel.lower())
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Assemble the URL of the XMPP bridge to contact.
message_queue = "http://" + args.hostname + ":" + str(args.port) + "/" + args.queue.strip('/')

logger.debug("Command line arguments presented to the script:")
logger.debug(str(args))

# Set up custom headers.
headers = {'Content-type': 'application/json'}

# Build the message to send.
message['name'] = args.queue.strip('/')
message['reply'] = " ".join(word for word in args.message)

# Attempt to contact the message queue and send a message.
try:
    logger.debug("Sending message to queue: " + message_queue)
    request = requests.put(message_queue, headers=headers,
        data=json.dumps(message))
    logger.debug("Response from server: " + request.text)
except:
    logger.warn("Connection attempt to message queue failed.")

# Fin.
sys.exit(0)
