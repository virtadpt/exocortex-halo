#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# hmac_a_tron.py - A microservice that takes a JSON document POSTed to it
#   containing an arbitrary string of some kind (read: secret key) and runs an
#   HMAC (https://en.wikipedia.org/wiki/Hash-based_message_authentication_code)
#   on it.  The HMAC'd data is then returned to the client as a JSON document
#   of the form { "result": "<HMAC here>" }.  The HMAC will be base64 encoded.
#
#   This microservice also supports the generation of Javascript Web Tokens
#   (https://jwt.io/) if pyjwt (https://github.com/jpadilla/pyjwt/) is installed
#   on the system.  If it is you'll get a message on startup and the online
#   docs will be slightly different.  tl;dr - grep for 'JWT' and if you see it,
#   support is enabled.
#
#   The use case for this should be pretty obvious: You want to interact with
#   an API programmatically but it requires that your requests be HMAC'd for
#   security, or it requires a JWT for Bearer authentication.  Not every
#   framework has working HMAC or JWT implementations, so this offloads that
#   work and hopefully saves your sanity.
#
#   If you make a GET request to / you'll get the online docs.

# By: The Doctor <drwho at virtadpt dot net>

# License: GPLv3

# v3.0 - Ported to Python 3.
# v2.0 - Added Javascript Web Token support (if pyjwt is installed).  This was
#        a fair amount of work, so it makes sense to bump the version number.
#      - Refactored code to break the heavy lifting out into separate helper
#        methods.  This also made it possible to add JWT support without turning
#        it into spaghetti code.
#      - Updated online help.
# v1.0 - Initial release.

# TO-DO:
# - Refactor this code to split the GET and PUT verbs' code into separate
#   files, and move the _helper_methods() into their own library file.
# - Add other options than base64 for output encoding.

# Load modules.
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler

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

# Flag that deterines if Javascript Web Token support is enabled.
jwt_enabled = False

# Classes.
# RESTRequestHandler: Subclass that implements a REST API service.  The rails
#   are the names of the hashes usable by the HMAC algorithm (md5, sha1, etc).
class RESTRequestHandler(BaseHTTPRequestHandler):

    # Constants that make a few things easier later on.
    required_hmac_keys = [ "data", "secret" ]
    required_jwt_keys = [ "headers", "payload", "secret" ]

    # Supported hash functions.
    supported_hashes = [ "md5", "sha1", "sha224", "sha256", "sha384", "sha512" ]

    # Set up the RESTRequestHandler object.  Most of the time this is a no-op
    # but it makes it easier to make additional support togglable later.
    def __init__(self, request, client_address, server):
        if jwt_enabled:
            if "jwt" not in self.supported_hashes:
                self.supported_hashes.append("jwt")
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        return

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
        <p><pre>
        {
            "data": "foo bar baz quux",
            "secret": "12345"
        }
        </pre></p>

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

        <p><pre>
        {
            "result": "Langih3qui3uguo7GaJongaichiethahmi1g"
        }
        </pre></p>
        """
        self.wfile.write(documentation)

        # If JWT are supported, send documentation for that.
        if jwt_enabled:
            jwt_help = """
        <p>This server also supports the generation of <a href="https://jwt.io/">Javascript Web Tokens</a> as a service because not all web templating systems support them.  This functionality requires as its payload a JSON document that looks like this (because it's easier that describing it elliptically):</p>

        <p><pre>
        {
            "headers": {
                "alg": "one of HS256, HS384, HS512, RS256, RS384, RS512, ES256, ES384, ES512, PS256, PS384",
                "typ": "JWT"
            },
            "payload": {
                "key": "value",
                "more keys": "and values in the payload"
            },
            "secret": "JWT secret for the service you're accessing"
        }
        </pre></p>

        <p>For example: <b>http://localhost:10000/jwt</b></p>

        <p>The service will then return a JSON document containing a Javascript Web Token.</p>

        <p><pre>
        {
            "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhZGRyZXNzIjoiMTYwMCBQZW5uc3lsdmFuaWEgQXZlbnVlIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.52s46weize9lCN-hrIQQCAk-j7HLO7tsZ1HOPc-R_C4"
        }
        </pre></p>
        """
            self.wfile.write(jwt_help)

        # Bottom of the page.
        bottom_of_page = """
        </body>
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
        arguments = {}
        response = {}

        # Parse the URI to see if it's one of the supported hashes.
        logger.debug("URI requested by the client: " + str(self.path))
        hash = self.path.strip("/")
        if hash not in self.supported_hashes:
            logger.debug("The user tried to use an unsupported method: " + str(hash))
            self._send_http_response(404, "That hash function is unsupported.")
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
            logger.debug("The user did not send deserializable JSON.")
            self._send_http_response(400, "You need to send valid JSON.  That was not valid.")
            return
        logger.debug("Value of arguments: " + str(arguments))

        # Determine if we should generate a JWT or an HMAC using the
        # appropriate helper method.
        if hash == "jwt":
            self._generate_jwt(arguments)
        else:
            self._generate_hmac(arguments, hash)

        return

    # Helper methods start here.

    # Helper method that does the heavy lifting of generating HMACs of data.
    def _generate_hmac(self, arguments, hash):
        logger.debug("Entered method RESTRequestHandler._generate_hmac().")

        hasher = None

        # Ensure that all of the required keys are in the JSON document.
        if not self._ensure_all_hmac_keys(arguments):
            logger.debug("A required key is missing in the HMAC payload.")
            self._send_http_response(400, "All required keys to generate an HMAC were not found in the JSON document.")
            return

        # Determine which hash to use with the HMAC and run it on the data.
        if hash == "md5":
            logger.debug("Picked hash MD5.")
            hasher = hmac.new(str(arguments["secret"]), arguments["data"],
                hashlib.md5)
        if hash == "sha1":
            logger.debug("Picked hash SHA-1.")
            hasher = hmac.new(str(arguments["secret"]), arguments["data"],
                hashlib.sha1)
        if hash == "sha224":
            logger.debug("Picked hash SHA-224.")
            hasher = hmac.new(str(arguments["secret"]), arguments["data"],
                hashlib.sha224)
        if hash == "sha256":
            logger.debug("Picked hash SHA-256.")
            hasher = hmac.new(str(arguments["secret"]), arguments["data"],
                hashlib.sha256)
        if hash == "sha384":
            logger.debug("Picked hash SHA-384.")
            hasher = hmac.new(str(arguments["secret"]), arguments["data"],
                hashlib.sha384)
        if hash == "sha512":
            logger.debug("Picked hash SHA-512.")
            hasher = hmac.new(str(arguments["secret"]), arguments["data"],
                hashlib.sha512)

        # Return the HMAC'd data to the client.
        logger.debug("Value of response: " + str(hasher.hexdigest()))
        self._send_http_response(200, hasher.hexdigest().upper())
        return

    # Helper method that does the heavy lifting of generating Javascript Web
    # tokens.
    def _generate_jwt(self, arguments):
        logger.debug("Entered method RESTRequestHandler._generate_jwt().")

        jwt_token = None

        # Ensure that all of the required keys are in the JSON document.
        if not self._ensure_all_jwt_keys(arguments):
            logger.debug("A required key is missing in the JWT payload.")
            self._send_http_response(400, "All required keys to generate a JWT were not found in the JSON document.")
            return

        # Generate a JWT.
        jwt_token = jwt.encode(arguments["payload"], arguments["secret"],
            algorithm=arguments["headers"]["alg"],
            headers=arguments["headers"])

        # Return the JWT to the client.
        logger.debug("Value of response: " + str(jwt_token))
        self._send_http_response(200, jwt_token)
        return

    # Send an HTTP response, consisting of the status code, headers and
    # payload.  Takes two arguments, the HTTP status code and a JSON document
    # containing an appropriate response.
    def _send_http_response(self, code, text):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
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
    def _ensure_all_hmac_keys(self, arguments):
        all_keys_found = True
        for key in self.required_hmac_keys:
            if key not in list(arguments.keys()):
                all_keys_found = False
        if not all_keys_found:
            return False
        else:
            return True

    # Ensure that all of the keys required to generate a Javascript Web Token
    # are in the hash table.
    def _ensure_all_jwt_keys(self, arguments):
        logger.debug("Entered method RESTRequestHandler._ensure_all_jwt_keys().")
        all_keys_found = True
        for key in self.required_jwt_keys:
            if key not in list(arguments.keys()):
                all_keys_found = False
                logger.debug("Did not find find required key ''" + str(key) + "''.")
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

# Try to load the JWT Python module.  If it's not present, no big deal, it's
# optional.
try:
    import jwt
    jwt_enabled = True
    logger.info("Javasript Web Token support enabled.")
except:
    pass

# Instantiate a copy of the HTTP server.
api_server = HTTPServer((args.host, int(args.port)), RESTRequestHandler)
logger.debug("REST API server now listening on " + str(args.host) +
    ", port " + str(args.port) + "/tcp.")
while True:
    api_server.serve_forever()

# Fin.
sys.exit(0)
