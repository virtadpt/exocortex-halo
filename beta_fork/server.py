#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# server.py - A web microservice that serves as a conversation engine for
#   arbitrary chatbots; the bots ping the server to get responses or submit
#   text to further train the brain and get replies back.  The server
#   implements a REST API to faciliate this.
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# v1.0 - Initial release.

# TODO:
# - 

# By: The Doctor <drwho at virtadpt dot net>
#     0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler

import argparse
import ConfigParser
import json
import logging
import os
import sys

# Globals.

# Handle for the command line argument parser.
args = ""

# Path to and name of the configuration file.
config_file = ""

# Server's loglevel (defaults to INFO).
loglevel = ""

# The server's management API key.
apikey = ""

# RESTRequestHandler: Subclass that implements a REST API service.  The main
#   rails are the names of agent networks that will poll message queues for
#   commands.  Each time they poll, they get a JSON dump of all of the
#   commands waiting for them.
class RESTRequestHandler(BaseHTTPRequestHandler):

    # Process HTTP/1.1 GET requests.
    def do_GET(self):
        # If someone requests /, return the current internal configuration of
        # this microservice to be helpful.
        if self.path == '/':
            logger.debug("User requested /.  Returning list of configured search agents.")
            self.send_response(200)
            self.send_header("Content-type:", "application/json")
            self.wfile.write('\n')
            json.dump({"active agents": message_queue.keys()}, self.wfile)
            return

        # Figure out if the base API rail contacted is one of the agents
        # monitoring this microservice.  If not, return a 404.
        agent = self.path.strip('/')
        if agent not in message_queue.keys():
            logger.debug("Message queue for agent " + agent + " not found.")
            self.send_response(404)
            self.send_header("Content-type:", "application/json")
            self.wfile.write('\n')
            json.dump({agent: "not found"}, self.wfile)
            return

        # If the message queue is empty, return an error JSON document.
        if not len(message_queue[agent]):
            logger.debug("Message queue for agent " + agent + " is empty.")
            self.send_response(200)
            self.send_header("Content-type:", "application/json")
            self.wfile.write('\n')
            json.dump({"command": "no commands"}, self.wfile)
            return

        # Extract the earliest command from the agent's message queue.
        command = message_queue[agent].pop(0)

        # Assemble a JSON document of the earliest pending command.  Then send
        # the JSON document to the agent.  Multiple hits will be required to
        # empty the queue.
        logger.debug("Returning earliest command from message queue " + agent
            + ": " + command)
        self.send_response(200)
        self.send_header("Content-type:", "application/json")
        self.wfile.write('\n')
        json.dump({"command": command}, self.wfile)
        return

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
argparser = argparse.ArgumentParser(description="A microservice that implements the back-end brain for arbitrary chatbots.  It presents a REST API which bots for just about any service can use for their conversations.  Supports both responding to and learning from text.")

# Set the default config file and the command line option to specify a new one.
argparser.add_argument('--config', action='store',
    default='server.conf' )

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument('--loglevel', action='store', default='logging.INFO',
    help='Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.')

# Parse the command line args.
args = argparser.parse_args()
if args.config:
    config_file = args.config

# Read the configuration file.  Then load it into a config file parser object.
config = ConfigParser.ConfigParser()
if not os.path.exists(config_file):
    logging.error("Unable to find or open configuration file " +
        config_file + ".")
    sys.exit(1)
config.read(config_file)

# Get configuration options from the configuration file.
apikey = config.get("DEFAULT", "apikey")

# Figure out how to configure the logger.  Start by reading from the config
# file.
config_log = config.get("DEFAULT", "loglevel").lower()
if config_log:
    loglevel = process_loglevel(config_log)

# Then try the command line.
if args.loglevel:
    loglevel = process_loglevel(args.loglevel.lower())

# Configure the logger with the base loglevel.
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Allocate and start the Simple HTTP Server instance.
api_server = HTTPServer(("localhost", 8050), RESTRequestHandler)
logger.debug("REST API server now listening on localhost, port 8050/tcp.")
while True:
    api_server.serve_forever()

# Fin.
sys.exit(0)

