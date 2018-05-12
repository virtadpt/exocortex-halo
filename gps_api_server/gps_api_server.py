#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# gps_api_server.py - A microservice that listens on a port (or mapped URL) for
#   HTTP(S) connections from software running on a portable computer, mobile
#   phone, or other device containing GPS coordinates.  These coordinates will
#   then be served to other HTTPS(S) clients that supply the correct
#   credentials.  Methods supported:
#   - GET with HTTP Basic authentication.

# By: The Doctor <drwho at virtadpt dot net> [4d7d 5c94  fa44 a235]

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# - Refactor this service into multiple source files because this is going to
#   get pretty hairy by the time it's done.
# - Add POST with API key authentication.
# - Add PUT with API key authentication.
# - Support API key as URL parameter.
# - Other clients can request another URI and get the coordinates as a JSON
#       document.
# - Multiple devices can send coordinates to this service and they'll be kept
#       separate.

# Load modules.
from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler

import argparse
import base64
import cgi
import ConfigParser
import logging
import os
import sys
import urlparse

# Constants.

# Global variables.
# Handles for the CLI argument parser handler.
argparser = None
args = None

# Handle to a configuration file parser.
config = None

# Overrideable configuration settings.  Will be set by the config file first
# and reset by any command line arguments if given.
ip = "0.0.0.0"
port = 4040
loglevel = None
apikey = ""

# Handle to an HTTP server.
app = None

# Authentication name and key.
authname = None
authkey = None
key = None

# Classes.
# RESTRequestHandler: CLass that implements the REST API.
class RESTRequestHandler(BaseHTTPRequestHandler):

    # Handle HEAD requests.  It's possible that there are GPS tracker clients
    # out there that support this so I want to at least have a stub in place.
    def do_HEAD(self):
        logger.debug("Entered RESTRequestHandler.do_HEAD().")
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write("Received HEAD request.\n")
        logger.debug("Client is using a GPS tracker that sends HEAD requests for some reason.")
        return

    # Handle authentication test HEAD requests.
    def do_AUTHHEAD(self):
        logger.debug("Entered RESTRequestHandler.do_AUTHHEAD().")
        self.send_response(401)
        self.send_header("WWW-Authenticate", "Basic realm=\"GPS Coordinates\"")
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write("Received AUTHHEAD request.\n")
        return

    # Handle GET requests.
    def do_GET(self):
        global key
        logger.debug("Entered RESTRequestHandler.do_GET().")

        # Test: Unauthenticated client connection.
        if self.headers.getheader("Authorization") == None:
            logger.debug("No authorization header in HTTP request.")
            self.do_AUTHHEAD()
            self.wfile.write("No authentication header received from client.\n")
            pass
        # Test: Authenticated client connection.
        elif self.headers.getheader("Authorization") == ("Basic " + key):
            logger.debug("Got valid authentication header.")
            self.wfile.write("You are authenticated to the server.  Doing whatever it is you want me to do.\n")
            pass
        # Fall-through: Bad authentication.
        else:
            logger.debug("No authorization header in HTTP request.")
            self.do_AUTHHEAD()
            #self.wfile.write(self.headers.getheader("Authorization") + "\n")
            self.wfile.write("Authentication failed.\n")
            pass
        return

    # Handle PUT requests.
    def do_PUT(self):
        logger.debug("Entered RESTRequestHandler.do_PUT().")
        self.send_response(200)
        self.end_headers()
        self.wfile.write("Received PUT request.\n")
        return

    # Handle POST requests.
    def do_POST(self):
        logger.debug("Entered RESTRequestHandler.do_POST().")
        self.send_response(200)
        self.end_headers()

        type = ""
        length = 0
        parameters = None
        payload = None

        type = self.headers["Content-Type"]
        length = int(self.headers["Content-Length"])
        parameters = self.rfile.read(length)

        if type == "multipart/form-data":
            payload = cgi.parse_multipart(parameters, self.headers)
        elif type == "application/x-www-form-urlencoded":
            payload = urlparse.parse_qs(parameters, keep_blank_values=1)

        self.wfile.write("Received POST request.\n")
        logger.debug("Requested path: " + str(self.path))
        logger.debug("Request headers: " + str(self.headers))
        logger.debug("Request parameters: " + str(parameters))
        logger.debug("Request payload: " + str(payload))
        return

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
argparser = argparse.ArgumentParser(description="A small REST API service that accepts authenticated HTTP(S) connections and takes a pair of GPS coordinates in latitude/longitude format as input.  It will serve those coordianates as JSON documents on a different URI.")
argparser.add_argument("--address", action="store",
    help="IP address to listen on.  Defaults to 0.0.0.0.")
argparser.add_argument("--port", action="store",
    help="Port to listen on.  Defaults to 4040/tcp.")
argparser.add_argument("--config", action="store",
    default="./gps_api_server.conf",
    help="Full path to a configuration file.")
argparser.add_argument('--loglevel', action='store',
    help='Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.')

# Parse the command line args, if any.
args = argparser.parse_args()

# If a configuration file has been specified on the command line, parse it.
config = ConfigParser.ConfigParser()
if not os.path.exists(args.config):
    print "Unable to find or open configuration file " + args.config + "."
    sys.exit(1)
config.read(args.config)

# Get the HTTP server configs from the config file.
ip = config.get("DEFAULT", "ip")
port = config.get("DEFAULT", "port")

# Get the default loglevel of the bot from the config file.
config_log = config.get("DEFAULT", "loglevel")
if config_log:
    loglevel = set_loglevel(config_log)

# Set the loglevel from the override on the command line if it exists.
if args.loglevel:
    loglevel = set_loglevel(args.loglevel.lower())

# Configure the logger.
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Get the authentication name and key from the config ifle.
authname = config.get("DEFAULT", "authname")
if not authname:
    print "ERROR: No authentication name configured.  You need one!"
    sys.exit(1)
authkey = config.get("DEFAULT", "authkey")
if not authkey:
    print "ERROR: No authentication key configured.  You need one!"
    sys.exit(1)
key = base64.b64encode(authname + ":" + authkey)
logger.debug("Authentication name: " + authname)
logger.debug("Authentication key: " + authkey)
logger.debug("Calculated authentication key: " + key)

# Override settings in the config file with the command line args if they exist.
if args.address:
    ip = args.address
if args.port:
    port = args.port

# Stand up the web application server.
app = HTTPServer((str(ip), int(port)), RESTRequestHandler)
logger.debug("GPS coordinates API server now listening on " + str(ip) + ", port " + str(port) + "/tcp.")
while True:
    app.serve_forever()

# Fin.
sys.exit(0)
