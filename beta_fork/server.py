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
# - Refactor common code into separate methods so it's easier to understand
#   and maintain.  There is a scary amount of repeated code in here, this will
#   make it much more elegant.

# By: The Doctor <drwho at virtadpt dot net>
#     0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler
from cobe.brain import Brain

import argparse
import ConfigParser
import json
import logging
import os
import re
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

# Full path to a Markov brain file and handle to the Markov brain object.
brainfile = ""
brain = ""

# In case the user wants to train from a corpus to initialize the Markov brain,
# this will be a full path to a training file.
training_file = ""

# RESTRequestHandler: Subclass that implements a REST API service.  The main
#   rails are the names of agent networks that will poll message queues for
#   commands.  Each time they poll, they get a JSON dump of all of the
#   commands waiting for them.
class RESTRequestHandler(BaseHTTPRequestHandler):
    # Keys that MUST be present in all JSON documents sent from the client.
    required_keys = ["botname", "apikey", "stimulus"]

    # Process HTTP/1.1 GET requests.
    def do_GET(self):
        content = ""
        content_length = 0
        arguments = {}
        response = ""

        # Variables that hold data from the database accesses.
        row = ""
        name = ""
        bots_api_key = ""
        respond = ""

        # If someone requests /, return the current internal configuration of
        # this microservice to be helpful.
        if self.path == '/':
            self.send_response(200)
            self.send_header("Content-type:", "text/html")
            self.end_headers()

            # Top of the page.
            self.wfile.write("<html><head><title>Documentation for beta_fork() server</title></head>")
            self.wfile.write("<body>")
            self.wfile.write("<p>All interaction with this service will take the form of JSON documents (Content-Type: application/json).  The following keys are required:</p>")
            self.wfile.write('<p><code>{ "botname": "bot\'s name", "apikey": "bot\'s unique API key", "stimulus": "Text the client wants to send the server." }</code></p>')

            # HTTP GET requests.
            self.wfile.write("<p>The following API rails may be accessed with GET requests:</p>")
            self.wfile.write("<ul>")
            self.wfile.write('<li>/ping - Responds with <code>"pong"</code></li>')
            self.wfile.write('<li>/response - Accepts a string of input in the <code>content</code> key and returns a JSON document of the form <code>{ "response": "This is the response.", "id": 200 }</code>, where "id" is the HTTP status code.  Does not add text to the Markov brain.</li>')
            self.wfile.write("</ul>")

            # HTTP PUT requests.
            self.wfile.write("<p>The following API rails may be accessed with PUT requests:</p>")
            self.wfile.write("<ul>")
            self.wfile.write('<li>/learn - Accepts a string of input in the <code>content</code> key and returns a JSON document of the form <code>{ "response": "trained", "id": XXX }</code>, where "id" is the HTTP status code.  Updates the Markov brain.</li>')
            self.wfile.write('<li>/register - Registers the API key of a new client with the server.  Requires the HTTP header X-API-Key, which is the management API key of the server.  Also requires a JSON document of the form <br><br><code>{ "botname": "Name of new bot", "apikey": "New bot\'s API key", "stimulus": "", "respond": "Y/N", "learn": "Y/N" }</code><br><br>  This rail will return an application/json documnt of the form <code>{ "response": "success/failure", "id": XXX }</code>, where XXX is the HTTP status code.</li>')
            self.wfile.write('<li>/deregister - Deregisters the API key of an existing client from the server, removing its access.  Requires the HTTP header X-API-Key, which is the management API key of the server.  Requires a JSON document of the form <br><br><code>{ "botname": "Name of bot", "apikey": "Bot\'s API key", "stimulus": "" }</code><br><br>  This rail will return an application/json documnt of the form <code>{ "response": "success/failure" }</code></li>')
            self.wfile.write("</ul>")

            # How to interact with the service with cURL.
            self.wfile.write('<p>To better understand how to interact with the service, you can use <a href="http://curl.haxx.se/">cURL</a> utility.</p>')
            self.wfile.write('<p>An HTTP GET request: <code>curl -X GET -H "Content-Type: application/json" -d \'{ "botname": "Alice", "apikey": "abcd", "stimulus": "This is some text I want to get a response to." }\' http://localhost:8050/response</code></p>')
            self.wfile.write('An HTTP PUT request: <code>curl -X PUT -H "Content-Type: application/json" -d \'{ "botname": "Alice", "apikey": "abcd", "stimulus": "This is some text I want to train the Markov engine on.  I do not expect to get a response to the text at the same time." }\' http://localhost:8050/learn</code>')
            self.wfile.write('<p>An HTTP PUT request to register a new bot: <code>curl -X PUT -H "Content-Type: application/json" -H "X-API-Key: ManagementAPIKeyHere" -d \'{ "botname": "ChairmanKage", "apikey": "allezcuisine", "stimulus": "", "respond": "Y", "learn": "Y" }\' http://localhost:8050/register</code></p>')

            # Bottom of the page.
            self.wfile.write("</body>")
            self.wfile.write("</body></html>")
            return

        # Respond to /ping requests.
        if self.path == '/ping':
            self.send_response(200)
            self.send_header("Content-type:", "text/html")
            self.end_headers()
            self.wfile.write("pong")
            return

        # Respond to /response requests.
        if self.path == '/response':
            # For debugging purposes, dump the headers the server gets from
            # the client.
            logging.debug("List of headers in the HTTP request:")
            for key in self.headers:
                logging.debug("    " + key + " - " + self.headers[key])

            # Read any content sent from the client.  If there is no
            # "Content-Length" header, something screwy is happening, in which
            # case we fire an error.
            content = self._read_content()
            if not content:
                logger.debug("Client sent zero-lenth content.")
                return

            # Ensure that the client sent JSON and not something else.
            if not self._ensure_json():
                return

            # Try to deserialize the JSON sent from the client.  If we can't,
            # pitch a fit.
            arguments = self._deserialize_content(content)
            if not arguments:
                return

            # Normalize the keys in the JSON to lowercase.  This is kind of an
            # ugly hack because it's a little wasteful of memory, but the hash
            # table is so small that we can deal with it.
            arguments = self._normalize_keys(arguments)

            # Ensure that all of the required keys are in the JSON document.
            if not self._ensure_all_keys(arguments):
                return

            # See if the bot is in the database.
            row = self._bot_in_database(arguments['botname'],
                arguments['apikey'])
            if not row:
                self._send_http_response(404, '{"response": "Bot not found.", "id": 404}')
                return

            # Take apart the response.  This is a little messy but necessary
            # to get at the very end of the tuple.
            (name, bots_api_key, respond) = row[0]

            # If the bot does not have permission to respond, send back an
            # error.  Again, this is a little messy but it's easier to get to
            # a Bool than it is playing with identifying single letters.  And
            # I'm sick while I'm writing this.
            respond = respond.lower()
            if respond == 'n':
                respond = False
            if not respond:
                self._send_http_response(401, '{"response": "Bot does not have permission to respond.", "id": 401}')
                return

            # Ask the Markov brain for a response and return it to the client.
            response = brain.reply(arguments['stimulus'])
            json.dump({"response": response, "id": 200}, self.wfile)
            return

        # If we've fallen through to here, bounce.
        return

    # Process HTTP/1.1 PUT requests.
    def do_PUT(self):
        content = ""
        content_length = 0
        arguments = {}
        response = ""
        sentences = []
        all_keys_found = True

        # Variables that hold data from the database accesses.
        row = ""
        name = ""
        bots_api_key = ""
        learn = ""

        if self.path == "/learn":
            logger.info("A client has contacted the /learn API rail.")

            # For debugging purposes, dump the headers the server gets from
            # the client.
            logging.debug("List of headers in the HTTP request:")
            for key in self.headers:
                logging.debug("    " + key + " - " + self.headers[key])

            # Read any content sent from the client.  If there is no
            # "Content-Length" header, something screwy is happening, in which
            # case we fire an error.
            content = self._read_content()
            if not content:
                logger.debug("Client sent zero-lenth content.")
                return

            # Ensure that the client sent JSON and not something else.
            if not self._ensure_json():
                return

            # Try to deserialize the JSON sent from the client.  If we can't,
            # pitch a fit.
            arguments = self._deserialize_content(content)
            if not arguments:
                return

            # Normalize the keys in the JSON to lowercase.  This is kind of an
            # ugly hack because it's a little wasteful of memory, but the hash
            # table is so small that we can deal with it.
            arguments = self._normalize_keys(arguments)

            # Ensure that all of the required keys are in the JSON document.
            if not self._ensure_all_keys(arguments):
                return

            # See if the bot is in the database.
            row = self._bot_in_database(arguments['botname'],
                arguments['apikey'])
            if not row:
                self._send_http_response(404, '{"response": "Bot not found.", "id": 404}')
                return

            # Take apart the response.  This is a little messy but necessary
            # to get at the very end of the tuple.
            (name, bots_api_key, learn) = row[0]

            # If the bot does not have permission to teach the Markov brain,
            # send back an error.  Again, this is a little messy but it's
            # easier to get to a Bool to work with than it is playing with
            # identifying single letters.  And I'm sick while I'm writing this.
            learn = learn.lower()
            if learn == 'n':
                learn = False
            if not learn :
                logger.info("Bot does not have permission to update the Markov brain.")
                self._send_http_response(401, '{"response": "Bot does not have permission to update the brain.", "id": 401}')
                return

            # Run the text through the Markov brain to update it and return a
            # success message.
            sentence_ends = re.compile('[.!?]')
            sentences = sentence_ends.split(arguments['stimulus'])

            # Get rid of the spurious entry at the end of the array...
            sentences.pop()
            logger.debug("List of sentences to learn from: " + str(sentences))

            # Run the sentences through the markov brain.
            if not len(sentences):
                logger.info("No sentences to update the Markov brain.")
                json.dump('{400, "response": "failed", "id": 400}', self.wfile)
                return
            for i in sentences:
                response = brain.learn(i)
            logger.info("Bot has updated the Markov brain.")
            json.dump('{200, "response": "trained", "id": 200}', self.wfile)
            return

        if self.path == "/register":
            logger.info("A client has contacted the /register API rail.  This makes things somewhat interesting.")

            # For debugging purposes, dump the headers the server gets from
            # the client.
            logging.debug("List of headers in the HTTP request:")
            for key in self.headers:
                logging.debug("    " + key + " - " + self.headers[key])

            # Read any content sent from the client.  If there is no
            # "Content-Length" header, something screwy is happening, in which
            # case we fire an error.
            content = self._read_content()
            if not content:
                logger.debug("Client sent zero-lenth content.")
                return

            # Ensure that the client sent JSON and not something else.
            if not self._ensure_json():
                return

            # Try to deserialize the JSON sent from the client.  If we can't,
            # pitch a fit.
            arguments = self._deserialize_content(content)
            if not arguments:
                return

            # Ensure that the management API key was sent in an HTTP header.
            # If it wasn't, abort.
            if "x-api-key" not in self.headers.keys():
                logger.info("User tried to /register a bot but didn't include the management API key.")
                self._send_http_response(401, '{"result": null, "error": "failure", "id": 401}')
                return

            # Check the included management API key against the one in the
            # server's config file.
            if self.headers['x-api-key'] != apikey:
                logger.info("User tried to /register a bot with an incorrect management API key.")
                self._send_http_response(401, '{"result": null, "error": "failure", "id": 401}')
                return

            # Normalize the keys in the JSON to lowercase.  This is kind of an
            # ugly hack because it's a little wasteful of memory, but the hash
            # table is so small that we can deal with it.
            arguments = self._normalize_keys(arguments)

            # Ensure that all of the required keys are in the JSON document.
            if not self._ensure_all_keys(arguments):
                return

            # There are additional JSON keys that have to be present for this
            # API rail.  This can probably be split out into a separate helper
            # method later.
            if "respond" not in arguments.keys():
                all_keys_found = False
            if "learn" not in arguments.keys():
                all_keys_found = False
            if not all_keys_found:
                logger.debug('{"result": null, "error": "All required keys were not found in the JSON document.  Look at the online help.", "id": 400}')
                self._send_http_response(400, '{"result": null, "error": "All required keys were not found in the JSON document.  Look at the online help.", "id": 400}')
                return

            # Ensure that the values of the respond and learn keys are either
            # Y or N.  Start by normalizing the values before testing them.
            valid_responses = ['Y', 'N']
            arguments['respond'] = arguments['respond'].upper()
            if arguments['respond'] not in valid_responses:
                self._send_http_response(400, '{"result": null, "error": "The only valid values for respond are Y or N.", "id": 400}')
                return

            arguments['learn'] = arguments['learn'].upper()
            if arguments['learn'] not in valid_responses:
                self._send_http_response(400, '{"result": null, "error": "The only valid values for learn are Y or N.", "id": 400}')
                return

            # See if the bot is in the database already.  Send back an error
            # 409 (Conflict) if it is.
            row = self._bot_in_database(arguments['botname'],
                arguments['apikey'])
            if row:
                logger.info("Bot already in database.")
                self._send_http_response(409, '{"response": "failure", "id": 409}')
                return

            # Add the bot to the database.
            if self._add_bot_to_database(arguments['botname'],
                arguments['apikey'], arguments['respond'], arguments['learn']):
                self._send_http_response(200, '{"response": "success", "id": 200}')
            else:
                self._send_http_response(400, '{"response": "failure", "id": 400}')
            return

        # If we've fallen through to here, bounce.
        return

    # Send an HTTP response, consisting of the status code, headers and
    # payload.  Takes two arguments, the HTTP status code and a JSON document
    # containing an appropriate response.
    def _send_http_response(self, code, response):
        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(response)
        return

    # Read content from the client connection and return it as a string.
    # Return None if there isn't any content.
    def _read_content(self):
        logger.debug("Entered _read_content().")
        content = ""
        content_length = 0

        try:
            content_length = int(self.headers['Content-Length'])
            content = self.rfile.read(content_length)
            logger.debug("Content sent by client: " + content)
        except:
            logger.debug('{"result": null, "error": "Client sent zero-lenth content.", "id": 500}')
            self._send_http_response(500, '{"result": null, "error": "Client sent zero-lenth content.", "id": 500}')
            return None

        return content

    # Ensure that the content from the client is JSON.
    def _ensure_json(self):
        if "application/json" not in self.headers['Content-Type']:
            logger.debug('{"result": null, "error": "You need to send JSON.", "id": 400}')
            self._send_http_response(400, '{"result": null, "error": "You need to send JSON.", "id": 400}')
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
            logger.debug('400, {"result": null, "error": "You need to send valid JSON.  That was not valid.", "id": 400}')
            self._send_http_response(400, '{"result": null, "error": "You need to send valid JSON.  That was not valid.", "id": 400}')
            return None

        return arguments

    # Normalize the keys in the hash table to all lowercase.
    def _normalize_keys(self, arguments):
        for key in arguments.keys():
            arguments[key.lower()] = arguments[key]
            logger.debug("Normalizing key " + key + " to " + key.lower() + ".")
        return arguments

    # Ensure that all of the keys required for every client access are in the
    # hash table.
    def _ensure_all_keys(self, arguments):
        all_keys_found = True

        for key in self.required_keys:
            if key not in arguments.keys():
                all_keys_found = False

        if not all_keys_found:
            logger.debug('400, {"result": null, "error": "All required keys were not found in the JSON document.  Look at the online help.", "id": 400}')
            self._send_http_response(400, '{"result": null, "error": "All required keys were not found in the JSON document.  Look at the online help.", "id": 400}')
            return False
        else:
            return True

    # Check to see if a bot is already in the database.  Return None if the
    # bot is not in the database (because it'll be treated as False) or the
    # row from the database (because it's non-False) The JSON response is
    # highly dependent on where in the code this method is being called from,
    # so the HTTP response is handled below the method call.
    def _bot_in_database(self, botname, apikey):
        row = ""

        cursor.execute("SELECT name, apikey, respond FROM clients WHERE name=? AND apikey=?", (botname, apikey, ))
        row = cursor.fetchall()
        if not row:
            return None
        else:
            return row

    # Add the bot to the database.  Return True if it worked and False if it
    # didnt'.
    def _add_bot_to_database(self, name, apikey, respond, learn):
        try:
            cursor.execute("INSERT INTO clients (name, apikey, respond, learn) VALUES (?, ?, ?, ?)", (name, apikey, respond, learn, ))
        except:
            logger.info("Unable to add bot " + botname + " to database.")
            database.rollback()
            return False

        # Success!  Commit the transaction and return True.
        database.commit()
        return True

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

# Path to the Cobe brain database.  If this file doesn't exist it'll be
# created, and unless a file to train the bot is supplied in another command
# line argument it'll have to train itself very slowly.
argparser.add_argument('--brain', action='store', default='./rom.construct',
    help="Path to the construct's brain.  If this file doesn't exist it'll be created, and you'll have to supply an initial training file in another argument.")

# Path to a training file for the Markov brain.
argparser.add_argument('--trainingfile', action='store',
    help="Path to a file to train the Markov brain with if you haven't done so already.  It can be any text file so long as it's plain text and there is one entry per line.  If a brain already exists, training more is probably bad.  If you only want the bot to learn from you, chances are you don't want this.")

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
dbpath = config.get("DEFAULT", "dbpath")
host = config.get("DEFAULT", "host")
port = config.get("DEFAULT", "port")
apikey = config.get("DEFAULT", "apikey")
brain = config.get("DEFAULT", "brain")

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
    cursor.execute("CREATE TABLE clients (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL)")
    cursor.execute("ALTER TABLE clients ADD COLUMN name TEXT")
    cursor.execute("ALTER TABLE clients ADD COLUMN apikey TEXT")
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

# If a prebuilt brainfile is specified on the command line, try to load it.
if args.brain:
    brainfile = args.brain
    logger.info("The bot's personality construct file is " + brainfile + ".  Make sure this is correct.")
    if not os.path.exists(brainfile):
        logger.warn("The personality construct file specified (" + brainfile + ") does not exist.  A blank one will be constructed.")

# If a training file is available, grab it.
if args.trainingfile:
    training_file = args.trainingfile

# Instantiate a copy of the Cobe brain and try to load the database.  If the
# brain file doesn't exist Cobe will create it.
brain = Brain(brainfile)
if training_file:
    if os.path.exists(training_file):
        logger.info("Initializing the personality matrix... this could take a while...")
        brain.start_batch_learning()
        file = open(training_file)
        for line in file.readlines():
            brain.learn(line)
        brain.stop_batch_learning()
        file.close()
        logger.info("Done!")
    else:
        logger.warn("Unable to open specified training file " + training_file + ".  The construct's going to have to learn the hard way.")

# Allocate and start the Simple HTTP Server instance.
api_server = HTTPServer((host, port), RESTRequestHandler)
logger.debug("REST API server now listening on IP " + host + " and port " + str(port) + ".")
while True:
    api_server.serve_forever()

# Fin.
sys.exit(0)

