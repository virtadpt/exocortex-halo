#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# hmac_a_tron.py - A microservice that takes a JSON document POSTed to it
#   contianing an arbitrary string of some kind (read: secret key) and runs an
#   HMAC (https://en.wikipedia.org/wiki/Hash-based_message_authentication_code)
#   on it.  The HMAC'd data is then returned to the client as a JSON document
#   of the form { "result": "<HMAC here>" }.  The HMAC will be base64 encoded.
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
# - Refactor this code to split the GET and PUT verbs' code into separate
#   files, and move the _helper_methods() into their own library file.
# - Add other options than base64 for output encoding.

# Load modules.
from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler

import argparse
import base64
import hashlib
import hmac
import json
import logging
import sys

# Global variables.
# Handles to a command line parser and parsed argument vector.
argparser = None
args = None

# Default log level for the microservice.
loglevel = None

# Handle to an HTTP server object.
api_server = None

# Classes.
# RESTRequestHandler: Subclass that implements a REST API service.  The rails
#   are the names of the hashes usable by the HMAC algorithm (md5, sha1, etc).
class RESTRequestHandler(BaseHTTPRequestHandler):

    # Constants that make a few things easier later on.
    required_keys = [ "data", "secret" ]

    # Supported hash functions for the HMAC.
    supported_hashes = [ "md5", "sha1", "sha224", "sha256", "sha384", "sha512" ]

    # Process HTTP/1.1 GET requests.
    def do_GET(self):
        logger.debug("Entered RESTRequestHandler.do_GET().")

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
        <p>This is a microservice that accepts POST requests that have JSON payloads with two keys in them:</p>

        <p>
        <ul>
        <li>data - A string of data to be HMAC'd.  All relevant data must be concatenated prior to sending it.</li>
        <li>secret - The secret HMAC key.</li>
        </ul>
        </p>

        <p>For example:</p>
        <p><code>
        {
            "data": "foo bar baz quux",
            "secret": "12345"
        }
        </code></p>

        <p>The Content-type header must be "application/json" or you'll get an HTTP 400 error.</p>

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

        <p>The final result will be returned as a JSON document with a single key, <b>result</b>, like so:</p>
        
        <p><code>
        {
            "result": "Langih3qui3uguo7GaJongaichiethahmi1g"
        }
        </code></p>

        </body>
        """
        self.wfile.write(documentation)

        # Bottom of the page.
        bottom_of_page = """
        <br/><br/>
        <footer></footer>
        </html>
        """
        self.wfile.write(bottom_of_page)

        return

    # Process HTTP/1.1 POST requests.
    def do_POST(self):
        logger.debug("Entered RESTRequestHandler.do_POST().")

        hash = ""
        content = ""
        content_length = 0
        arguments = {}
        hasher = None
        response = {}

        # Parse the URI to see if it's one of the supported hashes.
        logger.debug("URI requested by the client: " + str(self.path))
        hash = self.path.strip("/")
        if hash not in self.supported_hashes:
            logger.debug("The user tried to use a non-existent hash: " + str(hash))
            self._send_http_response(404, "That hash is unsupported.")
            return

        # Read any content sent from the client.  If there is no
        # "Content-Length" header, something screwy is happening, in which
        # case we fire an error.        
        content = self._read_content()
        if not content:
            logger.debug("Client sent zero-length content.")
            self._send_http_response(400, "You sent no content in that request.")
            return

        # Ensure that the client sent JSON and not something else.
        if not self._ensure_json():
            logger.debug("Client didn't send JSON in the payload.")
            self._send_http_response(400, "You need to send JSON.")
            return

        # Try to deserialize the JSON sent from the client.  If we can't,
        # pitch a fit.
        arguments = self._deserialize_content(content)
        if not arguments:
            logger.debug("A required key is missing in the payload.")
            self._send_http_response(400, "You need to send valid JSON.  That was not valid.")
            return
        logger.debug("Value of arguments: " + str(arguments))
        
        # Ensure that all of the required keys are in the JSON document.
        if not self._ensure_all_keys(arguments):
            logger.debug("A required key is missing in the payload.")
            self._send_http_response(400, "All required keys were not found in the JSON document.  Look at the online help.")
            return
        
        # Determine which hash to use with the HMAC and run it on the data.
        if hash == "md5":
            logger.debug("Picked hash MD5.")
            hasher = hmac.new(str(arguments["secret"]), "", hashlib.md5)
        if hash == "sha1":
            logger.debug("Picked hash SHA-1.")
            hasher = hmac.new(str(arguments["secret"]), "", hashlib.sha1)
        if hash == "sha224":
            logger.debug("Picked hash SHA-224.")
            hasher = hmac.new(str(arguments["secret"]), "", hashlib.sha224)
        if hash == "sha256":
            logger.debug("Picked hash SHA-256.")
            hasher = hmac.new(str(arguments["secret"]), "", hashlib.sha256)
        if hash == "sha384":
            logger.debug("Picked hash SHA-384.")
            hasher = hmac.new(str(arguments["secret"]), "", hashlib.sha384)
        if hash == "sha512":
            logger.debug("Picked hash SHA-512.")
            hasher = hmac.new(str(arguments["secret"]), "", hashlib.sha512)
        hasher.update(arguments["data"])

        # Return the HMAC'd data to the client.
        response["result"] = base64.encodestring(hasher.digest()).strip()
        logger.debug("Value of response: " + str(response))
        self._send_http_response(200, json.dumps(response))
        return

    # Helper methods start here.

    # Send an HTTP response, consisting of the status code, headers and
    # payload.  Takes two arguments, the HTTP status code and a JSON document
    # containing an appropriate response.
    def _send_http_response(self, code, text):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(text)
        return

    # Read content from the client connection and return it as a string.
    # Return None if there isn't any content.
    def _read_content(self):
        content = ""
        content_length = 0
        try:
            content_length = int(self.headers["Content-Length"])
            content = self.rfile.read(content_length)
            logger.debug("Content sent by client: " + content)
        except:
            return None
        return content

    # Ensure that the content from the client is JSON.
    def _ensure_json(self):
        if "application/json" not in self.headers["Content-Type"]:
            return False
        else:
            return True

    # Try to deserialize content from the client.  Return the hash table
    # containing the deserialized JSON if it exists.
    def _deserialize_content(self, content):
        arguments = {}
        try:
            arguments = json.loads(content)
        except:
            return None
        return arguments

    # Ensure that all of the keys required to carry out an HMAC are in the
    # hash table.
    def _ensure_all_keys(self, arguments):
        all_keys_found = True
        for key in self.required_keys:
            if key not in arguments.keys():
                all_keys_found = False
        if not all_keys_found:
            return False
        else:
            return True

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
argparser = argparse.ArgumentParser(description="A microservice that implements a service for HMAC'ing arbitrary data when supplied with a secret key of some kind.  It presents a REST API which just about any HTTP client can access.")

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument('--loglevel', action='store', default=logging.INFO,
    help='Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.')

# IP address the server listens on.  Defaults to 127.0.0.1 (localhost).
argparser.add_argument('--host', action='store', default="127.0.0.1",
    help='Local IP the server listens on.  Defaults to 127.0.0.1 (all local IPs).')

# Port the server listens on.  Default 10000/tcp.
argparser.add_argument('--port', action='store', default=10000,
    help='Port the server listens on.  Default 10000/tcp.')

# Parse the command line args.
args = argparser.parse_args()
if args.loglevel:
    loglevel = process_loglevel(args.loglevel)

# Configure the logger with the base loglevel.
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Instantiate a copy of the HTTP server.
api_server = HTTPServer((args.host, args.port), RESTRequestHandler)
logger.debug("REST API server now listening on " + str(args.host) +
    ", port " + str(args.port) + "/tcp.")
while True:
    api_server.serve_forever()

# Fin.
sys.exit(0)

