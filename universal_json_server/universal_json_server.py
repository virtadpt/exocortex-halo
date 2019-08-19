#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# universal_json_server.py - A microservice that takes a JSON document (like
#   an API or database dump) and serves it up with a REST API.  Parts of the
#   URI are used as keys, values get returned.  If there are additional keys,
#   a list of them will be returned.  If there are only values, they will be
#   returned.
#
#   The use case for this: I have a very large JSON document (a dump of the
#   CIA World Factbook (https://github.com/iancoleman/cia_world_factbook_api))
#   that I want to put behind a REST API so I can use it to answer questions
#   from other bots.  I've looked at a couple of different solutions but none
#   of them did what I wanted, which is this:
#
#   curl -X GET http://localhost:11000/countries/afghanistan/data/geographic_coordinates
#
#   and get usable output:
#
#      "geographic_coordinates": {
#        "latitude": {
#          "degrees": 33,
#          "minutes": 0,
#          "hemisphere": "N"
#        },
#        "longitude": {
#          "degrees": 65,
#          "minutes": 0,
#          "hemisphere": "E"
#        }
#      }
#
#   I can even drill down to get more precise data, because this server lets
#   me poke around in the data as well as get what I need, when I need it.
#
#   curl -X GET http://localhost:11000/countries/afghanistan/data/geographic_coordinates/longitude/degrees
#
# {
#   "degrees": 65
# }
#
#   If you make a GET request to /help you'll get the online docs.

# By: The Doctor <drwho at virtadpt dot net>
# License: GPLv3

# v2.0 - Reworked the URI parser into a "do this if" structure instead of a
#       "do this if not" structure.
#       - Added support for "is this a list?" and "is this a string?" when
#       parsing URIs.
# v1.0 - Initial release.

# TO-DO:
# -

# Load modules.
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler

import argparse
import json
import logging
import sys

# Global variables.
# Handles to a command line parser and parsed argument vector.
argparser = None
args = None

# Default log level for the microservice.
loglevel = None

# Handle to a JSON document and hash table to store it all.
infile = None
database = {}

# Handle to an HTTP server object.
api_server = None

# Classes.
# RESTRequestHandler: Subclass that implements a REST API service.  The rails
#   are the...
class RESTRequestHandler(BaseHTTPRequestHandler):
    # Set up the RESTRequestHandler object.  Most of the time this is a no-op
    # but it makes it easier to make additional support togglable later.
    def __init__(self, request, client_address, server):
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        return

    # Process HTTP/1.1 GET requests.
    def do_GET(self):
        logging.debug("Entered RESTRequestHandler.do_GET().")

        # URI from the user.
        uri = self.path.strip()
        uri = uri.split("/")

        # Key and cursor to inch around in the hash table.
        key = None
        cursor = database

        # Get rid of empty cells in the array.
        uri = list(filter(None, uri))
        logging.debug("URI from client: " + str(uri))

        # If we get a URI of "help" and only "help", return the online help.
        if len(uri) == 1:
            if uri[0] == "help":
                self._online_help()
                return

        # If we get no URI, just return the top-level keys of the hash table.
        if not len(uri):
            logging.debug("Returning top-level keys to the user.")
            self._send_http_response(200, json.dumps(list(cursor.keys()),
                sort_keys=True, indent=4))
            return

        # Inch around inside the hash table/database, matching every part of
        # the URI to a hash table key at the current position.
        for key in uri:
            # Case: Cursor is pointing at a hash table.
            if isinstance(cursor, dict):
                logging.debug("Cursor is pointing at a dict.")
                if key in cursor.keys():
                    logging.debug("Found key '" + str(key) + "' in URI.")
                    cursor = cursor[key]
                    try:
                        logging.debug("Available keys at this level: " + str(list(cursor.keys())))
                    except:
                        logging.debug("No more keys, hit the end of the JSON path.")
                    continue

            # Case: Cursor is pointing at a list.
            if isinstance(cursor, list):
                logging.debug("Cursor is pointing at a list.")
                cursor = cursor[int(key)]
                continue

            # Case: Cursor is pointing at a string.
            # This is a terminal case - it's the end of a JSON path.
            if isinstance(cursor, str):
                logging.debug("Cursor is pointing at a string.")
                break
        # Bottom of loop.

        # Return what we found.
        self._send_http_response(200, json.dumps(cursor, sort_keys=True,
            indent=4))
        return

    # Process HTTP/1.1 POST requests.
    def do_POST(self):
        logging.debug("Entered RESTRequestHandler.do_POST().")
        self._send_http_response(405, b"HTTP POST is not supported by this service.")
        return

    # Process HTTP/1.1 PUT requests.
    def do_PUT(self):
        logging.debug("Entered RESTRequestHandler.do_PUT().")
        self._send_http_response(405, b"HTTP PUT is not supported by this service.")
        return

    # Process HTTP/1.1 DELETE requests.
    def do_DELETE(self):
        logging.debug("Entered RESTRequestHandler.do_DELETE().")
        self._send_http_response(405, b"HTTP DELETE is not supported by this service.")
        return

    # Process HTTP/1.1 PATCH requests.
    def do_PATCH(self):
        logging.debug("Entered RESTRequestHandler.do_PATCH().")
        self._send_http_response(405, b"HTTP PATCH is not supported by this service.")
        return

    # Process HTTP/1.1 HEAD requests.
    def do_HEAD(self):
        logging.debug("Entered RESTRequestHandler.do_HEAD().")
        self._send_http_response(405, b"HTTP HEAD is not supported by this service.")
        return

    # Helper methods start here.
    # Return online help to the client.
    def _online_help(self):
        logging.debug("Entered RESTRequestHandler._online_help().")

        # Send headers.
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        # Top of the page.
        top_of_page = b"""
<html><head><title>Universal JSON Server</title></head>
        """
        self.wfile.write(top_of_page)

        # Documentation.
        documentation = b"""
<body>
<p>A microservice that takes a JSON document (like an API or database dump) and
serves it up with a REST API.  Parts of the URI are used as keys, values get returned.  If there are additional keys, a list of them will be returned.  If
there are only values, they will be returned.</p>

<p>My use case for this: I have a very large JSON document (a dump of the CIA
World Factbook (<a href="https://github.com/iancoleman/cia_world_factbook_api">https://github.com/iancoleman/cia_world_factbook_api</a>)) that I want to put behind a REST API so I can use it to answer questions
from other bots.  I've looked at a couple of different solutions but none of
them did what I wanted, which is this:</p>

<p>The final result will be returned as a JSON document containing whatever it finds (keys, values, some mixture of both), so an example URI like this:</p>

<p><b>http://localhost:11000/countries/afghanistan/data/geographic_coordinates</b></p>

<p>Will return results like this:</p>

<p><pre>
    {
        "geographic_coordinates": {
        "latitude": {
          "degrees": 33,
          "minutes": 0,
          "hemisphere": "N"
        },
        "longitude": {
          "degrees": 65,
          "minutes": 0,
          "hemisphere": "E"
        }
      }
    }
</pre></p>

<p>The idea is that you can explore the JSON to find the keys you want by
playing around with the URL and then access only those keys to get the data
you want.  I do this a lot when messing around with databases but didn't have
the tools I was looking for.  So, here's that tool.</p>
        """
        self.wfile.write(documentation)

        # Bottom of the page.
        bottom_of_page = b"""
</body>
<br/><br/>
<footer></footer>
</html>
        """
        self.wfile.write(bottom_of_page)
        return

    # Send an HTTP response, consisting of the status code, headers and
    # payload.  Takes two arguments, the HTTP status code and a JSON document
    # containing an appropriate response.
    def _send_http_response(self, code, text):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(text.encode())
        return

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
argparser = argparse.ArgumentParser(description="A microservice that takes an arbitrary JSON document (like a database or API dump) and serves it up as a read-only REST API.")

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument("--loglevel", action="store", default=logging.INFO,
    help="Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.")

# IP address the server listens on.  Defaults to 127.0.0.1 (localhost).
argparser.add_argument("--host", action="store", default="127.0.0.1",
    help="Local IP the server listens on.  Defaults to 127.0.0.1 (all local IPs).")

# Port the server listens on.  Default 10000/tcp.
argparser.add_argument("--port", action="store", default=11000,
    help="Port the server listens on.  Default 11000/tcp.")

# Full path to the JSON document to server.
argparser.add_argument("--json", action="store",
    help="Full path to the JSON document to serve.")

# Parse the command line args.
args = argparser.parse_args()
if args.loglevel:
    loglevel = process_loglevel(args.loglevel)

# Configure the logger with the base loglevel.
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Make sure we can open the JSON document.
if not args.json:
    logging.fatal("No JSON document supplied.")
    sys.exit(1)
try:
    with open(args.json, "r") as infile:
        database = infile.read()
    database = json.loads(database)
    logging.info("Successfully loaded JSON document " + str(args.json) + ".")
except:
    logging.fatal("Unable to read in JSON document " + str(args.json) + ".")
    sys.exit(1)

# Instantiate a copy of the HTTP server.
api_server = HTTPServer((args.host, int(args.port)), RESTRequestHandler)
logging.debug("REST API server now listening on " + str(args.host) +
    ", port " + str(args.port) + "/tcp.")
while True:
    api_server.serve_forever()

# Fin.
sys.exit(0)
