#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# exocortex_xmpp_bridge.py - A service that logs into an XMPP server with
#   credentials from a configuration file, builds message queues for agents
#   designated in the config file, and listens for messages sent from the
#   designated owner.  Each message must contain the name of the agent and a
#   command.  The service pushes messages for the agents into matching message
#   queues that are accessed later via a REST interface.  Messages to
#   unmatched agents are dropped and an error is sent back to the bot's owner
#   so they don't get stuck in spurious message queues that nothing can ever
#   access.
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# v6.0 - Changes to use SliXMPP.  Reworked some stuff to clean it up while I
#        was at it.  Chief among them, declaring some of the globals rather
#        than freestyling them later.  This may as well be a major release.
#      - Replaced xmpp_client.process() with xmpp_client.loop.run_forever()
#        because .process() is going away in v1.9.0 of SliXMPP due to asyncio
#        replacing threading.  May as well try to get ahead of the game for
#        once.
#      - Made generated and customized strings more pythonic.
#      - Figured out how to run the HTTP server in a separate thread and
#        moved it to start before the xmppclient.XMPPClient object because the
#        latter runs in the foreground.
# v5.0 - Ported to Python 3.
# v4.0 - Refacted bot to break major functional parts out into separate modules.
#      - Made the interface and port the REST API listens on configurable.
#        Defaults to the old localhost:8003.
#      - Fixed the bug in which the loglevel in the config file was always
#        ignored in favor of the command line.
# v3.0 - Rewriting to use SleekXMPP, because I'm tired of XMPPpy's lack of
#        documentation.  The code is much more sleek, if nothing else.
#      - Refactored the core message processing method to split out the
#        common stuff (online help and status reports) into helper methods.
# v2.2 - Added a universal API rail '/replies' so that bots can send replies
#        to their user over XMPP by hitting their configured XMPP bridge over
#        HTTP.
# v2.1.1 - Started pulling 'search' out of text because this bot is used for
#        much more than just web searches.
# v2.1 - Working on the "goes into a coma and pegs the CPU problem" by adding
#        XEP-0199 client-to-server pings to keep the server alive.
#      - Added online help to the command parser.
# v2.0 - Rewrote using xmpppy (http://xmpppy.sourceforge.net/) because it's
#        more lightweight than SleekXMPP and hopefully has fewer interactions.
#        Also, if I need to, I should be able to drop nbXMPP
#        (https://python-nbxmpp.gajim.org/) in with minimal code modification.
#      - Added some code that lets the bot interact more with its owner to
#        provide feedback.  I got tired of having to read the logs to see what
#        was going on, okay?
#      - Renamed a bunch of stuff because I tore out the old XMPPBot and wrote
#        a new class from scratch.  It made it easier to keep track of in my
#        head... until I did so, in fact, I had a hard time rewriting this
#        bot.
# v1.1 - Switched out OptionParser in favor of argparse.
#      - Refactored the code to make a little more sense.  argparse helped a
#        lot with that.
#      - Reworked logging a little.
#      - Declared variables at the tops of everything for maintainability.
#        Having to deal with a phantom variable that pops out of nowhere is
#        kind of annoying.
#      - Setting SleekXMPP to "block=True" makes it easier to kill from the
#        command line.
#      - Set the default loglevel to INFO.
# v1.0 - Initial release.

# TODO:
# - Write a signal handler that makes the agent reload its configuration file
#   (whether it's the default one or specified on the command line).
# - Consider adding a SQLite database to serialize the message queues to in
#   the event the microservice ABENDs or gets shut down.  Don't forget a
#   scream-and-die error message to not leave the user hanging.
# - Maybe add a signal handler that'll cause the bot to dump its message queues
#   to the database without dying?
# - Figure out how to make slightly-mistyped search agent names (like all-
#   lowercase instead of proper capitalization, or proper capitalization
#   instead of all caps) match when search requests are pushed into the
#   message queue.  I think I can do this, I just need to play with it.

# By: The Doctor <drwho at virtadpt dot net>
#     0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

from http.server import HTTPServer

import argparse
import configparser
import json
import logging
import os
import sys
import _thread

import message_queue
import rest
import xmppclient

# Globals.
# IP/hostname and port the REST API server listens on.  Defaults to localhost
# and port 8003/tcp.
listenon_host = "localhost"
listenon_port = 8003

# JID of the bot's registered owner.
owner = ""

# Username/JID and password the bot uses to log into an XMPP server.
username = ""
password = ""

# Logging for the XMPP bridge.  Defaults to INFO.
loglevel = None

# An array of strings containing the names of the bots that will take orders
# through this bot and send responses back.
agents = []

# Handle for the command line argument parser.
args = ""

# Path to and name of the configuration file.
config_file = ""

# Handle for the XMPP client.
xmpp_client = None

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

# start_rest_server(): Wrapper function that starts an instance of HTTPServer
#   in a thread so that it won't block execution.  Takes two args, a hostname
#   or IP address to listen on, and a TCP port to listen on.  Doesn't return
#   anything because it hangs off of a thread and runs until the bridge shuts
#   down.
def start_rest_server(host, port):
    logger.debug("Entered start_rest_server().")

    # Handle to an HTTPServer.
    api_server = None

    # Allocate an instance of HTTPServer that listens on a particular IP and
    # port, and instantiates my custom REST API object.
    api_server = HTTPServer((host, port), rest.RESTRequestHandler)
    logger.debug(api_server)
    logger.info("REST API server now listening on %s, port %s/tcp." %
        (host, port))

    logger.debug("Kicking off the API server.")
    api_server.serve_forever()

# Core code...
# Set up the command line argument parser.
argparser = argparse.ArgumentParser(description="A construct that logs into an XMPP server with credentials from a configuration file, builds message queues for the other constructs listed in the config file, and listens for messages sent from the construct's designated owner.")

# Set the default config file and the command line option to specify a new one.
argparser.add_argument('--config', action='store',
    default='exocortex_xmpp_bridge.conf' )

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument('--loglevel', action='store',
    help='Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.')

# Parse the command line args.
args = argparser.parse_args()
if args.config:
    config_file = args.config

# Read the configuration file.  Then load it into a config file parser object.
config = configparser.ConfigParser()
if not os.path.exists(config_file):
    logging.error("Unable to find or open configuration file %s." % config_file)
    sys.exit(1)
config.read(config_file)

# Get configuration options from the configuration file.
listenon_host = config.get("DEFAULT", "hostname")
listenon_port = int(config.get("DEFAULT", "port"))
owner = config.get("DEFAULT", "owner")
username = config.get("DEFAULT", "username")
password = config.get("DEFAULT", "password")
agents = config.get("DEFAULT", "agents")

# Get the names of the agents to set up queues for from the config file.
for i in agents.split(','):
    message_queue.message_queue[i] = []

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

# In debug mode, output the configuration variables.
logger.debug("Value of listenon_host: %s" % listenon_host)
logger.debug("Value of listenon_port: %s" % listenon_port)
logger.debug("Value of owner: %s" % owner)
logger.debug("Value of username: %s" % username)
logger.debug("Value of password: %s" % password)
logger.debug("Value of agents: %s" % agents)

# Start the REST API server on a low-level thread.  It doesn't need to have
# full thread functionality, it just has to have an object hanging off of it
# with a running event loop.  We do this first because slixmpp.xmppclient runs
# in the foreground, and I haven't figured out how to change that yet.
# https://docs.python.org/3/library/_thread.html
_thread.start_new_thread(start_rest_server, (listenon_host, listenon_port))

# Instantiate the XMPP client module.
logger.debug("Initializing the XMPP client object.")
xmpp_client = xmppclient.XMPPClient(username, password, owner)

# Register some XEP plugins.
xmpp_client.register_plugin("xep_0030") # Service discovery
xmpp_client.register_plugin("xep_0078") # Legacy authentication
xmpp_client.register_plugin("xep_0199") # XMPP ping

# https://github.com/mightyBroccoli/xmpp-chatbot/blob/master/main.py
# Added for troubleshooting the "won't wake back up" problem.
xmpp_client.register_plugin("xep_0012") # Last activity
xmpp_client.register_plugin("xep_0085") # Chat state notifications
xmpp_client.register_plugin("xep_0128") # Service discovery extensions

# Connect to the XMPP server and start processing message streams.
xmpp_client.connect()
xmpp_client.loop.run_forever()

# Fin.
sys.exit(0)
