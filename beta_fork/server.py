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
import sqlite3
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

# Path to the SQLite database that holds bot/client information.
dbpath = ""

# Handle to the SQLite database.
database = ""

# Database cursor.
cursor = ""

# IP address and port the server listens on.
host = ""
port = 0

# RESTRequestHandler: Subclass that implements a REST API service.  The main
#   rails are the names of agent networks that will poll message queues for
#   commands.  Each time they poll, they get a JSON dump of all of the
#   commands waiting for them.
class RESTRequestHandler(BaseHTTPRequestHandler):
    # API key extracted from headers of client request.
    api_key = ""

    # Process HTTP/1.1 GET requests.
    def do_GET(self):
        # If someone requests /, return the current internal configuration of
        # this microservice to be helpful.
        if self.path == '/':
            self.send_response(200)
            self.send_header("Content-type:", "text/html")
            self.end_headers()
            self.wfile.write("<html><head><title>Documentation for beta_fork() server</title></head>")
            self.wfile.write("<body>")
            self.wfile.write("<p>All API calls save this one require API keys, which are passed in HTTP headers like so:</p>")
            self.wfile.write("<code>")
            self.wfile.write("X-API-Key: someAPIkeyHere")
            self.wfile.write("</code>")

            self.wfile.write("<p>The following API rails may be accessed with GET requests:</p>")
            self.wfile.write("<ul>")
            self.wfile.write('<li>/ping - Responds with <code>{ "response": "pong" }</code></li>')
            self.wfile.write('<li>/response - Accepts a string of input from the HTTP header X-Text-To-Respond-To, returns application/json of the form <code>{ "response": "This is the response." }</code>.  Does not add text to the Markov brain.</li>')
            self.wfile.write("</ul>")

            self.wfile.write("<p>The following API rails may be accessed with PUT requests:</p>")
            self.wfile.write("<ul>")
            self.wfile.write('<li>/learn - Accepts a string of input from the HTTP header X-Text-To-Learn, returns application/json of the form <code>{ "response": "trained" }</code>.  Updates the Markov brain.</li>')
            self.wfile.write('<li>/register - Registers the API key of a new client with the server.  Requires the HTTP header X-API-Key, which is the management API key of the server.  Also requires a JSON document of the form <br><br><code>{ "name": "Name of new bot", "api-key": "New bot\'s API key", "respond": "Y/N", "learn": "Y/N" }</code><br><br>  This rail will return an application/json documnt of the form <code>{ "response": "success/failure" }</code></li>')
            self.wfile.write('<li>/deregister - Deregisters the API key of an existing client from the server, removing its access.  Requires the HTTP header X-API-Key, which is the management API key of the server.  Requires a JSON document of the form <br><br><code>{ "name": "Name of bot", "api-key": "Bot\'s API key" }</code><br><br>  This rail will return an application/json documnt of the form <code>{ "response": "success/failure" }</code></li>')
            self.wfile.write("</ul>")

            self.wfile.write("</body>")
            self.wfile.write("</body></html>")
            return

        # Respond to /ping requests.
        if self.path == '/ping':
            self.send_response(200)
            self.send_header("Content-type:", "application/json")
            self.end_headers()
            json.dump({"response": "pong"}, self.wfile)
            return

        # Respond to /response requests.
        if self.path == '/response':
            json.dump({"response": response}, self.wfile)
            return

        # If we've fallen through to here, bounce.
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
argparser.add_argument('--config', action='store', default='server.conf',
    help='Full path to a configuration file for the server.  Defaults to ./server.conf.')

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument('--loglevel', action='store', default='logging.INFO',
    help='Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.')

# Path to the SQLite database that holds bot/client information.
argparser.add_argument('--dbpath', action='store', default='clients.db',
    help='Full path to a SQLite database that contains information about the bots/clients allowed to connect to the server.  Defaults to ./clients.db.')

# IP address the server listens on.  Defaults to 0.0.0.0 (all local IPs).
argparser.add_argument('--host', action='store', default="0.0.0.0",
    help='Local IP the server listens on.  Defaults to 0.0.0.0 (all local IPs).')

# Port the server listens on.  Default 8050/tcp.
argparser.add_argument('--port', action='store', default=8050,
    help='Port the server listens on.  Default 8050/tcp.')

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
dbpath = config.get("DEFAULT", "dbpath")
host = config.get("DEFAULT", "host")
port = config.get("DEFAULT", "port")

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

# Pull the path to the client database out of the argument vector if it's there.
if args.dbpath:
    dbpath = args.dbpath

# Create the SQLite database if it doesn't exist, open it if it does.
if not os.path.exists(dbpath):
    logger.debug("Client database " + dbpath + " not found.  Creating it.")
    database = sqlite3.connect(dbpath)
    cursor = database.cursor()
    cursor.execute("CREATE TABLE clients (id INTEGER PRIMARY KEY NOT NULL)")
    cursor.execute("ALTER TABLE clients ADD COLUMN apikey TEXT")
    cursor.execute("ALTER TABLE clients ADD COLUMN name TEXT")
    cursor.execute("ALTER TABLE clients ADD COLUMN respond TEXT")
    cursor.execute("ALTER TABLE clients ADD COLUMN learn TEXT")
    database.commit()
    database.close()
logger.debug("Opening database " + dbpath + ".")
database = sqlite3.connect(dbpath)
cursor = database.cursor()

# Get the IP and port to listen on from the argument vector, if they're there.
if args.host:
    host= args.host
if args.port:
    port = args.port

# Allocate and start the Simple HTTP Server instance.
api_server = HTTPServer((host, port), RESTRequestHandler)
logger.debug("REST API server now listening on IP " + host + " and port " + str(port) + ".")
while True:
    api_server.serve_forever()

# Fin.
sys.exit(0)

