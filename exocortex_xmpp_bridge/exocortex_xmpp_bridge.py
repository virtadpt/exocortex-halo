#!/usr/bin/env python2
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
#   This is a branch of exocortex_xmpp_bridge.py that uses xmpppy
#   (http://xmpppy.sourceforge.net/) in an attempt to build a more stable
#   implementation that doesn't tie its threads in knots.  Thus, this is a
#   substantial rewrite.
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

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
# - Refactor command parser to break out commands and search requests into
#   smaller methods.  It's pretty messy, and thus difficult to debug.

# By: The Doctor <drwho at virtadpt dot net>
#     0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler

import halolib

import argparse
import ConfigParser
import json
import logging
import os
import sys
import threading
import xmpp

# Globals.
# Handle for the XMPP client thread.
xmpp_client_thread = None

# This hash table's keys are the names of agents, the associated values are
# lists which implement the message queues.
message_queue = {}

# Add the message queue so this bot's agents can send replies.
message_queue['replies'] = []

# Handle for the command line argument parser.
args = ""

# Path to and name of the configuration file.
config_file = ""

# Logging for the XMPP bridge.  Defaults to INFO.
loglevel = ""

# XMPPClient: XMPP client class.  Implemented using threading.Thread because
#   it'll spin out on its own to connect to the XMPP server, while the custom
#   REST API server handles the distribution of requests to other agents.
class XMPPClient(threading.Thread):
    # Username information needed to log into the XMPP server.
    username = ""
    nickname = ""
    JID = ""
    password = ""
    server = ""

    # This is the bot's designated owner, which controls whether or not it
    # responds to any commands.
    owner = ""

    # Local reference to a method that will run when the thread is instructed
    # to terminate itself.
    on_end = None

    # This flag determines whether or not the thread will terminate itself.
    shutdown = False

    # Handles to parts of an active XMPP connection.
    connection = False
    connection_resource = False
    authentication_resource = False
    roster = ""
    xmpp_ping = ""

    # Initialize new instances of the class.
    def __init__(self, username, password):
        logger.debug("Now initializing an instance of the XMPPClient thread.")
        threading.Thread.__init__(self)

        # Store the username, password and nickname as local attributes.
        self.username = username
        self.password = password
        self.nickname = self.username.split('@')[0]

        # Register the bot's owner.
        self.owner = owner

        # Generate a JID, because that seems to be a specific data structure
        # in xmpppy.
        self.JID = xmpp.JID(username)

        # Build an XEP-0199 client-to-server ping stanza.
        self.xmpp_ping = self.build_xmpp_ping()

        # Start the thread.
        logger.debug("Initiating the XMPPClient thread by calling self.start().")
        self.start()

    # run(): Method that is started by self.start() above which does the actual
    #   work of the thread.
    def run(self):
        logger.debug("Entered XMPPClient.run().")

        now_online = ""
        now_online_message = ""

        # Connect to the XMPP server.  ABEND if we can't.
        self.connection = xmpp.Client(self.JID.getDomain(), debug=[])
        self.connection_resource = self.connection.connect()
        if not self.connection_resource:
            logger.fatal("Unable to connect to XMPP server " + self.JID.getDomain() + " with JID " + self.JID + "!")
            sys.exit(1)

        # Test for an encrypted connection, because that's how I roll.
        if self.connection_resource != 'tls':
            logger.warning("Unable to establish a TLS encrypted connection to server " + self.JID.getDomain() + "!")

        # Authenticate to the server.  ABEND if we can't.
        self.authentication_resource = self.connection.auth(self.JID.getNode(),
            self.password, self.nickname)
        if not self.authentication_resource:
            logger.fatal("Failed authentication to XMPP server " + self.JID.getDomain() + " with JID " + str(self.JID) + "!")
            sys.exit(1)

        # Tell the XMPP server that we're ready to rock by sending a presence
        # stanza.
        logger.info("Successful authentication to XMPP server.  Sending initial presence stanza.")
        self.connection.sendInitPresence()

        # Get the login account's buddy list (XMPP stanza: roster).
        logger.debug("Pulling buddy list from server's database...")
        self.roster = self.connection.getRoster()

        # Register a handler that processes messages from the connection's
        # data stream.
        self.connection.RegisterHandler("message", self.process_message)

        # Send a message to the bot's owner that it is now online.
        logger.info("Now informing " + self.owner + " that the configured agents are now online.")
        if len(message_queue.keys()) == 1:
            now_online_message = "The bot "
        else:
            now_online_message = "The bots "

        for key in message_queue.keys():
            if key == 'replies':
                continue
            now_online_message = now_online_message + key + ", "
        now_online_message = now_online_message.strip(", ")

        if len(message_queue.keys()) == 1:
            now_online_message = now_online_message + " is now online."
        else:
            now_online_message = now_online_message + " are now online."

        now_online = xmpp.protocol.Message(to=xmpp.JID(self.owner),
            body=now_online_message)
        self.connection.send(now_online)

        # Initiate the server XMPP ping thread.
        logger.debug("Initiating the background XMPP server ping thread.")
        self.send_xmpp_ping()

        # Go into the work loop.
        logger.debug("Entering XMPPClient.run() work loop.")
        while not self.shutdown:

            # See if there are any messages in the XMPP bot's private message
            # queue 'replies'.  If there are, pick the least recently added
            # one out and transmit it to the bot's user.  This is getting a
            # little hairy so I really should make it readable.
            if len(message_queue['replies']):
                reply = message_queue['replies'].pop(0)
                response = xmpp.protocol.Message(to=xmpp.JID(self.owner),
                    body=reply)
                self.connection.send(response)

            try:
                # See if there is a stanza in the incoming connection stream.
                self.connection.Process(10)

            except KeyboardInterrupt:
                logger.debug("Received KeyboardInterrupt.")
                self.shutdown = True

        # If we get down to here, the thread has been told to terminate.
        logger.debug("XMPPClient.run() has entered the termination phase.")
        return

    # process_message(): Method that is attached to an XMPPClient.connection
    #   object which fires whenever a message arrives from the connection data
    #   stream
    def process_message(self, connection, message):
        logger.debug("Processing an XMPP message stanza.")

        # Variables used to dissect and respond to XMPP message stanzas.
        message_sender = ""
        message_type = ""
        message_body = ""
        agent_name = ""
        response = ""
        response_body = ""
        acknowledge = ""
        acknowledge_text = ""
        command = ""

        # Only pay attention to messages from the bot's owner.  We don't
        # respond because we don't want to leak any information to someone
        # probing this aspect of the exocortex.
        message_sender = message.getFrom()
        message_sender = str(message_sender).split('/')[0]
        logger.debug("Value of XMPPClient.process_message().message_sender is: " + message_sender)
        if message_sender != self.owner:
            logger.debug("Received a command from invalid bot owner " + message_sender + ".")
            return

        # Only pay attention to one-to-one message stanzas.
        message_type = message.getType()
        logger.debug("Value of XMPPClient.process_message().message_type is: " + message_type)
        if message_type not in ('normal', 'chat'):
            logger.debug("Received a message stanza of type " + str(message_type) + ", which is not what I'm looking for.")
            return

        # Extract the message body for parsing.
        message_body = str(message.getBody()).strip()
        logger.debug("Value of XMPPClient.process_message().message_body is: " + str(message_body))

        # If the agent's name is None (some XMPP clients send stanzas with
        # no bodies), silently bounce.
        if message_body == "None":
            logger.debug("The XMPP client sent an empty message body which is interpreted as None.  Bluh.")
            return

        # If the user asks for help, display the list of acknowledged commands.
        if message_body == "help":
            logger.debug("User has requested online help.")
            resonse_body = "Supported commands:\n- help - This online help."
            response_body = response_body + "- Robots, report. - List all constructs this bot is configured to communicate with.\n"
            response = xmpp.protocol.Message(to=xmpp.JID(self.owner),
                body=response_body)
            self.connection.send(response)

            response_body = "To send a command to one of the constructs, use an XMPP client to send a message that looks something like this:\n"
            response_body = response_body + "[bot name], top [n] hits for [search term].\n"
            response_body = response_body + "Individual constructs may have their own online help, so try sending the command '[bot name], help.'\n"
            response = xmpp.protocol.Message(to=xmpp.JID(self.owner),
                body=response_body)
            self.connection.send(response)

            return

        # Respond to a command for a status report.
        if message_body == "Robots, report.":

            # Configured message queues.
            for key in message_queue.keys():
                if key == 'replies':
                    continue
                response_body = response_body + key + " "
            response = xmpp.protocol.Message(to=xmpp.JID(self.owner),
                body=response_body)
            self.connection.send(response)

            # Contents of message queues.
            response_body = "Contents of message queues are as follows:"
            response = xmpp.protocol.Message(to=xmpp.JID(self.owner),
                body=response_body)
            self.connection.send(response)

            for key in message_queue.keys():
                if key == 'replies':
                    continue
                response_body = "Agent " + key + ": "
                response_body = response_body + str(message_queue[key])
                response = xmpp.protocol.Message(to=xmpp.JID(self.owner),
                    body=response_body)
                self.connection.send(response)
            return

        # Try to split off the bot's name from the message body.  If the
        # agent's name isn't registered, bounce.
        if ',' in message_body:
            agent_name = message_body.split(',')[0]
        else:
            agent_name = message_body.split(' ')[0]
        logger.debug("Agent name: " + agent_name)

        if agent_name not in message_queue.keys():
            logger.debug("Command sent to agent " + agent_name + ", which doesn't exist on this bot.")

            # Build a response message stanza to inform the user that the
            # agent they're trying to contact doesn't exist.
            response_body = "Request sent to agent " + agent_name + ", which doesn't exist on this bot.  Please check your spelling."
            response = xmpp.protocol.Message(to=xmpp.JID(self.owner),
                body=response_body)
            self.connection.send(response)
            return

        # Extract the command from the message body and clean it up.
        if ',' in message_body:
            command = message_body.split(',')[1]
        else:
            command = message_body.split(' ')[1]
        command = command.strip()
        command = command.strip('.')
        logger.debug("Received request: " + command)

        # Push the request into the appropriate message queue.
        logger.debug("Added request to " + agent_name + "'s message queue.")
        message_queue[agent_name].append(command)

        # Tell the bot's owner that the request has been added to the agent's
        # message queue.
        logger.debug("Sending acknowledgement of request to " + self.owner + ".")
        acknowledge_text = "Your request has been added to " + agent_name + "'s request queue."
        acknowledge = xmpp.protocol.Message(to=xmpp.JID(self.owner),
            body=acknowledge_text)
        self.connection.send(acknowledge)
        return

    # Constructs an XEP-0199 client-to-server ping Iq stanza, which will be
    # re-used all the time.
    def build_xmpp_ping(self):
        xmpp_ping_stanza = ""
        xmpp_ping = ""

        xmpp_ping_stanza = "<iq from='" + self.username + "' "
        xmpp_ping_stanza = xmpp_ping_stanza + "id='c2s1' type='get'>"
        xmpp_ping_stanza = xmpp_ping_stanza + "\n"
        xmpp_ping_stanza = xmpp_ping_stanza + "  <ping xmlns='urn:xmpp:ping'/>"
        xmpp_ping_stanza = xmpp_ping_stanza + "\n"
        xmpp_ping_stanza = xmpp_ping_stanza + "</iq>"
        xmpp_ping = xmpp.Iq(node=xmpp_ping_stanza)

        return xmpp_ping

    # This is a self-contained method which sends an XEP-0199 ping to the
    # server every 60 seconds to keep the client's connection alive.
    def send_xmpp_ping(self):
        self.connection.send(self.xmpp_ping)
        threading.Timer(60, self.send_xmpp_ping).start()

# RESTRequestHandler: Subclass that implements a REST API service.  The main
#   rails are the names of agents or constructs that will poll message queues
#   for commands.  Each time they poll, they get a JSON dump of the next
#   command waiting for them in chronological order.
class RESTRequestHandler(BaseHTTPRequestHandler):

    # Constants that make a few things easier later on.
    required_keys = ["name", "reply"]

    # Process HTTP/1.1 GET requests.
    def do_GET(self):
        # If someone requests /, return the current internal configuration of
        # this microservice to be helpful.
        if self.path == '/':
            logger.debug("User requested /.  Returning list of configured agents.")
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
            self.send_header("Content-Type:", "application/json")
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
        self.send_header("Content-Type:", "application/json")
        self.wfile.write('\n')
        json.dump({"command": command}, self.wfile)
        return

    # Replies from a construct will look like this:
    #
    # {
    #   "name": "<bot's name>",
    #   "reply": "<The bot's witty repartee' goes here.>"
    # }

    # Process HTTP/1.1 PUT requests.
    def do_PUT(self):
        content = ""
        content_length = 0
        response = {}
        reply = ""

        # Figure out if the API rail is the 'replies' rail, meaning that a
        # construct wants to send a response back to the user.  If not, return
        # a 404.
        agent = self.path.strip('/')
        if agent != "replies":
            logger.debug("Something tried to PUT to API rail /" + agent + ".  Better make sure it's not a bug.")
            self.send_response(404)
            self.send_header("Content-Type:", "application/json")
            self.wfile.write('\n')
            json.dump({agent: "not found"}, self.wfile)
            return

        logger.info("A construct has contacted the /replies API rail.")
        logging.debug("List of headers in the HTTP request:")
        for key in self.headers:
            logging.debug("    " + key + " - " + self.headers[key])

        # Read the content sent from the client.  If there is no
        # "Content-Length" header something screwy is happening because that
        # breaks the HTTP spec so fire an error.
        content = self._read_content()
        if not content:
            logger.debug("Client sent zero-length content.")
            return

        # Try to deserialize the JSON sent from the client.  If we can't,
        # pitch a fit.
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

        # Generate a reply to the bot's owner and add it to the bot's private
        # message queue.
        reply = "Got a message back from " + response['name'] + ":\n\n"
        reply = reply + response['reply']
        message_queue['replies'].append(reply)
        self.send_response(200)
        return

    # Send an HTTP response, consisting of the status code, headers and
    # payload.  Takes two arguments, the HTTP status code and a JSON document
    # containing an appropriate response.
    def _send_http_response(self, code, response):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response))
        return

    # Read content from the client connection and return it as a string.
    # Return None if there isn't any content.
    def _read_content(self):
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

# Core code...
# If we're running in a Python environment earlier than v3.0, set the
# default text encoding to UTF-8 because XMPP requires it.
if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf-8')

# Set up the command line argument parser.
argparser = argparse.ArgumentParser(description="A microservice that logs into an XMPP server with credentials from a configuration file, builds message queues for the Huginn agent networks listed in the config file, and listens for messages sent from the microservice's designated owner.")

# Set the default config file and the command line option to specify a new one.
argparser.add_argument('--config', action='store',
    default='exocortex_xmpp_bridge.conf' )

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
owner = config.get("DEFAULT", "owner")
username = config.get("DEFAULT", "username")
password = config.get("DEFAULT", "password")
agents = config.get("DEFAULT", "agents")

# Get the names of the agents to set up queues for from the config file.
for i in agents.split(','):
    message_queue[i] = []

# Figure out how to configure the logger.  Start by reading from the config
# file.
config_log = config.get("DEFAULT", "loglevel").lower()
if config_log:
    loglevel = halolib.set_loglevel(config_log)

# Then try the command line.
if args.loglevel:
    loglevel = halolib.set_loglevel(args.loglevel.lower())

# Configure the logger with the base loglevel.
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Instantiate the XMPP client thread.
logger.debug("Initializing the XMPP client thread.")
xmpp_client_thread = XMPPClient(username, password)

# Allocate and start the Simple HTTP Server instance.
api_server = HTTPServer(("localhost", 8003), RESTRequestHandler)
logger.debug("REST API server now listening on localhost, port 8003/tcp.")
while True:
    api_server.serve_forever()

# Fin.
xmpp_client_thread.join()
sys.exit(0)

