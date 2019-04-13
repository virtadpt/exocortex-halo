#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# exocortex_web_to_speech.py - Sets up a simple API that listens on the
#   loopback interface waiting for Exocortex to contact it.  Exocortex sends it
#   an API key, a phone number, and some text.  This daemon writes the text to
#   a file and calls the text2wave utility of Festival
#   (http://www.cstr.ed.ac.uk/projects/festival/) to convert it into a .wav
#   file.  It then calls exocortex_sip_client to place a telephone call using
#   the .wav as the voice channel.  This server is actually never supposed to
#   terminate.

# This server defaults to port 3030/tcp.  You can change that by passing the
# port on the command line to listen on, like this:
#   exocortex_web_to_speech.py 16212

# One way of playing with this is with the command
#  `curl -X POST -H 'Content-Type: application/json \
#   -d '{"message":"foo", "number":"bar", "api key":"baz"}' \
#   http://localhost:<port>/`

# By: The Doctor [412/724/301/703/415/510] <drwho at virtadpt dot net>

# License: GPLv3

# v3.0 - Ported to Python 3.
# v2.0 - I've changed so much stuff, this may as well be a new rev.
# v1.1.1 - Added an optional delay between receiving a message to process and
#   placing a call.  Updated online documentation to reflect this.
# v1.1 - Change default listen-on IP to 127.0.0.1.
# - Make web.py accept a port number as a command line argument and listen on
#   that instead of 8080/tcp.  Just in case, to prevent conflict with other
#   web.py apps on the same host, it defaults to port 3030/tcp.
# - Change the default HTTP method to POST.
# - Restructured the POST method handler to do things a little more sanely.
# - Added some better error checking.
# - Moved the API key into a field of the incoming JSON request instead of an
#   HTTP header.
# - return() some HTML or JSON at the end of the HTTP request handler so that
#   Huginn has something to go from.  Probably JSON so that the PostAgent can
#   do something with it.
# - Added a HTTP GET method handler that prints some documentation.  It'll be
#   nice to have some debugging assistance.

# TO-DO:
# - Split this up into several files to make it easier to maintain later.
#   Then again, this is the first time I've looked at this code in ages.
# - Down in RESTRequestHandler.do_POST() the synthesis command still kind of
#   assumes /usr/bin/text2wave.  I really need to fix that.
# - Refactor RESTRequestHandler.do_POST() because it's huge and thus hard to
#   maintain.
# - Assembling the command to place a SIP call is really, really... bad.  I
#   need to write a proper command generator, because this is bobbins.

# Load modules.
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler

import argparse
import configparser
import json
import logging
import os
import subprocess
import sys
import tempfile

# Constants.

# Global variables.
# Handles for the CLI argument parser handler.
argparser = None
args = None

# Handle to a configuration file parser.
config = None

# Overrideable configuration settings.  Will be set by the config file first
# and reset by any command line arguments if given.
ip = None
port = 0
loglevel = None
apikey = ""
tts = ""

# Phone number to dial.
phone_number = 0

# Message to eventually convert into speech.
message = ""

# Command to use to place the phone call.
sip_client = ""

# Handle to an HTTP server.
app = None

# Classes.
# RESTRequestHandler: CLass that implements the REST API.
class RESTRequestHandler(BaseHTTPRequestHandler):
    required_keys = [ "api key", "number", "message" ]

    # Handle GET requests.  In this case, by returning HTML documentation.
    def do_GET(self):
        logger.debug("Entered RESTRequestHandler.do_GET().")

        html = """
        <head>
        <title>exocortex_web_to_speech.py help documentation</title>
        </head>

        <body>
        <p>This agent was designed to interface with Andrew Cantino's <a href="https://github.com/cantino/huginn/">Huginn</a> by providing a bridge to a speech synthesis utility (like the one in my <a href="https://github.com/virtadpt/exocortex-halo">halo</a>).  By default it listens on <a href="http://localhost:3030/">http://localhost:3030/</a> but you can set it to whatever you want by passing a different port number as a command line agument.  See the output of <b>./exocortex_web_to_speech.py --help</b> for more information.</p>

        <p>The HTTP interface is designed to work with Huginn's PostAgent.  You'll find a sample one in the code repository.</p>

        <p>To interact with this agent you need to place a <b>POST</b> request to the server and pass in a JSON document that has three strings: The message, an API key, and the phone number to dial (no spaces).  The value of the Content-Type HTTP header has to be "application/json".  It might look something like this:</p>

        <pre>
        {
          "api key":"AllYourBaseAreBelongToUs",
          "number":"2064560649",
          "message":"I'm sorry, Dave, I can't let you do that.",
          "delay": 120
        }
        </pre>

        <p>(Note: The phone number 206-456-0649 belongs to <a href="http://thetestcall.blogspot.com/">The Test Call</a>, a free and legal public service which implements some features useful for testing and debugging VoIP software.  I started using them when I got tired of rickrolling myself.  If you find their service useful, I highly recommend sending them some money!)</p>

        <p>The number "delay" is just that - a delay (in seconds) between this server receiving the call request and the request actually going out.  This is to work around VoIP providers that are kind of twitchy about placing multiple calls in a relatively short period of time, stacking up several outbound calls, and generally giving yourself some breathing room when debugging.  This defaults to 120 seconds.</p>

        <p>Huginn's PostAgent will do all of this for you so all you have to do is configure it, start it and let it run.  What you do with this agent after that is your business.</p>

        <p>If you want to experiment with it or debug any changes made, use <a href="http://curl.haxx.se/">curl</a>.  Here's one way to go about it: <b>curl -X POST -H "Content-Type: application/json" -d '{ "message":"This is where my message goes", "api key":"AllYourBaseAreBelongToUs", "number":"2064560649" }' http://localhost:3030/</b></p>
        </body>

        """

        logging.debug("User requested /.  Returning online documentation.")
        self.send_response(200)
        self.wfile.write('\n')
        self.wfile.write(html)
        return

    # Handle POST requests.
    def do_POST(self):
        logger.debug("Entered RESTRequestHandler.do_POST().  Time to run the gauntlet.")

        content = ""
        response = None

        # Reference the few global variables required in this app.
        global phone_number
        global message

        # Set up the local delay between processing this request and actually
        # placing the call.  Default to 120 seconds.
        call_delay = 120

        # Read the content sent from the client.  If there is no
        # "Content-Length" header something screwy is happening because that
        # breaks the HTTP spec so fire an error.
        content = self._read_content()
        if not content:
            return

        # Try to deserialize the JSON sent from the client.  If we can't, pitch
        # a fit.
        if not self._ensure_json():
            return
        response = self._deserialize_content(content)
        if not response:
            return

        # Normalize the keys in the JSON to lowercase.
        response = self._normalize_keys(response)

        # Ensure that all of the required keys are in the JSON document.
        if not self._ensure_all_keys(response):
            return
        logger.debug("Made it through the gauntlet - all necessary variables are in place.")

        # If a delay was specified in the request, use that instead.
        if "delay" in list(response.keys()):
            call_delay = int(response["delay"])
            logger.debug("Got a request to set the call timeout to " + str(response["delay"]) + " seconds.")

        # Generate tempfiles we're going to need for the text and generated
        # speech.
        temp_text_file = tempfile.NamedTemporaryFile(suffix='.txt', dir='/tmp/',
            delete=False)
        temp_text_filename = temp_text_file.name
        logger.debug("Temporary filename generated: " + temp_text_filename)

        # Extract the URI encoded arguments passed to the server.
        phone_number = response["number"]
        message = response["message"]

        # Write the text into the tempfile.
        temp_text_file.write(message)
        temp_text_file.close()
        logger.debug("Wrote message to tempfile.")

        # Build the command to generate speech.
        synthesis_command = tts + ' ' + temp_text_filename + ' -o ' + temp_text_filename + '.wav'
        logger.debug("Generated synthesis command: " + synthesis_command)

        # Generate the outgoing voice message.
        subprocess.call(synthesis_command, shell=True)

        # Call the SIP client to place the phone call.  Yes, this is
        # kind of ugly but to make the SIP software work on Ubuntu I had to
        # put everything into a virtualenv, which means wrapper scripts.  Yay.
        call_command = sip_client + ' ' + str(call_delay)
        call_command = call_command + ' --production'
        call_command = call_command + ' --phone-number ' + phone_number
        call_command = call_command + ' --message ' + temp_text_filename
        call_command = call_command + '.wav'
        subprocess.call(call_command, shell=True)

        # Clean up after ourselves.  Specifically cast to str() because Unicode
        # is always messin' with my Zen thing.
        os.unlink(str(temp_text_filename))
        os.unlink(str(temp_text_filename + '.wav'))

        # Send a message back to the requesting client to be a good netizen.
        self._send_http_response(200, '{"result": "Success.", "error": "No errors detected.", "id": 200}')
        return

    # Read content from the client connection and return it as a string.
    # Return None if there isn't any content.
    def _read_content(self):
        content = ""
        content_length = 0

        try:
            content_length = int(self.headers['Content-Length'])
            content = self.rfile.read(content_length)
            logging.debug("Content sent by client: " + content)
        except:
            logging.debug("Client sent zero-lenth content.  Returning error 500")
            self._send_http_response(500, '{"result": null, "error": "Client sent zero-lenth content.", "id": 500}')
            return None

        return content

    # Send an HTTP response, consisting of the status code, headers and
    # payload.  Takes two arguments, the HTTP status code and a JSON document
    # containing an appropriate response.
    def _send_http_response(self, code, response):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response))
        return

    # Ensure that the content from the client is JSON.
    def _ensure_json(self):
        if "application/json" not in self.headers['Content-Type']:
            logging.debug("Client did not send a JSON document.  Or at least the value of the Content-Type header wasn't application/json.")
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
            logging.debug("That wasn't valid JSON, it didn't deserialize properly.")
            self._send_http_response(400, '{"result": null, "error": "You need to send valid JSON.  That was not valid.", "id": 400}')
            return None

        return arguments

    # Normalize the keys in the hash table to all lowercase.
    def _normalize_keys(self, arguments):
        for key in list(arguments.keys()):
            arguments[key.lower()] = arguments[key]
            logging.debug("Normalized key " + key + " to " + key.lower() + ".")
        return arguments

    # Ensure that all of the keys required for every client access are in the
    # hash table.
    def _ensure_all_keys(self, arguments):
        all_keys_found = True

        for key in self.required_keys:
            if key not in list(arguments.keys()):
                all_keys_found = False

        if not all_keys_found:
            logging.debug("Not all of the required keys were found in the deserialized JSON.")
            self._send_http_response(400, '{"result": null, "error": "All required keys were not found in the JSON document.  Look at the online help.", "id": 400}')
            return False
        else:
            return True

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
argparser = argparse.ArgumentParser(description="A small REST API service that accepts phone numbers to call and text to turn into messages, generates an audio file with a text-to-speech synthesizer, and shells out to a SIP client to place the phone call.")
argparser.add_argument("--address", action="store", default="127.0.0.1",
    help="IP address to listen on.  Defaults to 127.0.0.1.")
argparser.add_argument("--port", action="store", default=3030,
    help="Port to listen on.  Defaults to 3030/tcp.")
argparser.add_argument("--config", action="store",
    default="./exocortex_web_to_speech.conf",
    help="Full path to a configuration file.")
argparser.add_argument('--loglevel', action='store',
    help='Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.')

# Parse the command line args, if any.
args = argparser.parse_args()

# If a configuration file has been specified on the command line, parse it.
config = configparser.ConfigParser()
if not os.path.exists(args.config):
    print("Unable to find or open configuration file " + args.config + ".")
    sys.exit(1)
config.read(args.config)

# Get the HTTP server configs from the config file.
ip = config.get ("DEFAULT", "ip")
port = config.get ("DEFAULT", "port")

# Get the API key which restricts access to this server from the config file.
apikey = config.get ("DEFAULT", "apikey")

# Get the full path to the text-to-speech utility the server will use to create
# the call audio.
tts = config.get ("DEFAULT", "tts")

# Get the full path to the SIP client utility the server will use to place the
# call.
sip_client = config.get ("DEFAULT", "sip_client")

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

# Override settings in the config file with the command line args if they exist.
if args.address:
    ip = args.address
if args.port:
    port = args.port

# Ensure that the API key is set.  ABEND if it's not.
if not apikey:
    logger.critical("You need to set an API key in the config file.")
    sys.exit(1)

# Ensure that the TTS utility exists.  ABEND if it's not.
if not os.path.exists(tts):
    logger.critical("I wasn't able to find the text-to-speech utility " + tts + ".  Please check your configuration file or install any necessary packages.")
    sys.exit(1)

# Ensure that the SIP client exists.  ABEND if it's not.
if not os.path.exists(sip_client):
    logger.critical("I wasn't able to find the SIP client " + sip_client + ".  Please check your configuration file or install any necessary packages.")
    sys.exit(1)

# Stand up the web application server.
app = HTTPServer((str(ip), int(port)), RESTRequestHandler)
logger.debug("Web to speech API server now listening on " + str(ip) + ", port " + str(port) + "/tcp.")
while True:
    app.serve_forever()

# Fin.
sys.exit(0)
