#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# hmac_a_tron.py - A microservice that takes a string of data POSTed to it
#   along with an arbitrary string of some kind (read: secret key) and runs an
#   HMAC (https://en.wikipedia.org/wiki/Hash-based_message_authentication_code)
#   on it.  The HMAC'd data is then returned to the client.
#
#   The use case for this should be pretty obvious: You want to interact with
#   an API programmatically but it requires that your requests be HMAC'd for
#   security.  Not every framework has a working HMAC implementation, so this
#   offloads that work and hopefully saves your sanity.
#
#   If you make a GET request to / you'll get the online docs.

# By: The Doctor <drwho at virtadpt dot net>

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:

# Load modules.
from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler

import hashlib
import hmac
import logging
import sys

# Constants.
# IP/hostname and port the REST API server listens on.  Defaults to localhost
# and port 8003/tcp.
listenon_host = "localhost"
listenon_port = 10000

# Global variables.
# Loglevel.  Defaults to INFO.
loglevel = logging.INFO

# Handle to an HTTP server object.
api_server = None

# Classes.
# RESTRequestHandler: Subclass that implements a REST API service.  The rails
#   are the names of the hashes usable by the HMAC algorithm (md5, sha1, etc).
class RESTRequestHandler(BaseHTTPRequestHandler):

    # Constants that make a few things easier later on.
    required_parameters = [ "data", "secret" ]

    # Process HTTP/1.1 GET requests.
    def do_GET(self):
        # HTTP GETs only return online documentation, regardless of the payload.
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        # Top of the page.
        top_of_page = """
        <html><head><title>HMAC-A-Tron</title></head>
        """
        self.wfile.write(top_of_page)

        # Documentation.
        documentation = """
        <body>
        <p>This is a microservice that accepts POST requests with two parameters:</p>
        <p>
        <ul>
        <li>data - A string of data to be HMAC'd.  All relevant data must be concatenated prior to sending it.</li>
        <li>secret - The secret HMAC key.</li>
        </ul>
        </p>

        <p>The name of the HMAC algorithm is used as the URI.</p>

        <p>Supported HMAC algorithms:</p>
        <p>
        <ul>
        <li>md5</li>
        <li>sha1</li>
        <li>sha224</li>
        <li>sha256</li>
        <li>sha384</li>
        <li>sha512</li>
        </ul>
        </p>

        <p>For example: <b>http://localhost:10000/sha256</b></p>

        <p>The final result will be returned as a string, e.g. <b>Langih3qui3uguo7GaJongaichiethahmi1g</b></p>

        </body>
        """
        self.wfile.write(documentation)

        # Bottom of the page.
        bottom_of_page = """
        <footer></footer>
        </html>
        """
        self.wfile.write(bottom_of_page)

        return

    # Process HTTP/1.1 POST requests.
    def do_POST(self):
        pass

# Functions.

# Core code...
# Configure the logger with the base loglevel.
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Instantiate a copy of the HTTP server.
api_server = HTTPServer((listenon_host, listenon_port), RESTRequestHandler)
logger.debug("REST API server now listening on " + str(listenon_host) +
    ", port " + str(listenon_port) + "/tcp.")
while True:
    api_server.serve_forever()

# Fin.
sys.exit(0)

