#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# rest.py - This module implements the REST API part of
#   exocortex_xmpp_bridge.py.
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# v4.0 - Refacted bot to break major functional parts out into separate modules.
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

from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler

import json
import logging

import message_queue

# Globals.

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
        # this bot in an attempt to be helpful.
        if self.path == '/':
            logging.debug("User requested /.  Returning list of configured agents.")
            self.send_response(200)
            self.send_header("Content-type:", "application/json")
            self.wfile.write('\n')
            json.dump({ "active agents": message_queue.message_queue.keys() },
                self.wfile)
            return

        # Figure out if the base API rail contacted is one of the agents
        # pulling requests from this bot.  If not, return a 404.
        agent = self.path.strip('/')
        if agent not in message_queue.message_queue.keys():
            logging.debug("Message queue for agent " + agent + " not found.")
            self.send_response(404)
            self.send_header("Content-type:", "application/json")
            self.wfile.write('\n')
            json.dump({agent: "not found"}, self.wfile)
            return

        # If the message queue is empty, return an error JSON document.
        if not len(message_queue.message_queue[agent]):
            logging.debug("Message queue for agent " + agent + " is empty.")
            self.send_response(200)
            self.send_header("Content-Type:", "application/json")
            self.wfile.write('\n')
            json.dump({"command": "no commands"}, self.wfile)
            return

        # Extract the earliest command from the agent's message queue.
        command = message_queue.message_queue[agent].pop(0)

        # Assemble a JSON document of the earliest pending command.  Then send
        # the JSON document to the agent.  Multiple hits will be required to
        # empty the queue.
        logging.debug("Returning earliest command from message queue " + agent
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
            logging.debug("Something tried to PUT to API rail /" + agent + ".  Better make sure it's not a bug.")
            self.send_response(404)
            self.send_header("Content-Type:", "application/json")
            self.wfile.write('\n')
            json.dump({agent: "not found"}, self.wfile)
            return

        logging.info("A construct has contacted the /replies API rail.")
        logging.debug("List of headers in the HTTP request:")
        for key in self.headers:
            logging.debug("    " + key + " - " + self.headers[key])

        # Read the content sent from the client.  If there is no
        # "Content-Length" header something screwy is happening because that
        # breaks the HTTP spec so fire an error.
        content = self._read_content()
        if not content:
            logging.debug("Client sent zero-length content.")
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
        reply = "Got a message from " + response['name'] + ":\n\n"
        reply = reply + response['reply']
        message_queue.message_queue['replies'].append(reply)
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
            logging.debug("Content sent by client: " + content)
        except:
            logging.debug('{"result": null, "error": "Client sent zero-lenth content.", "id": 500}')
            self._send_http_response(500, '{"result": null, "error": "Client sent zero-lenth content.", "id": 500}')
            return None

        return content

    # Ensure that the content from the client is JSON.
    def _ensure_json(self):
        if "application/json" not in self.headers['Content-Type']:
            logging.debug('{"result": null, "error": "You need to send JSON.", "id": 400}')
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
            logging.debug('400, {"result": null, "error": "You need to send valid JSON.  That was not valid.", "id": 400}')
            self._send_http_response(400, '{"result": null, "error": "You need to send valid JSON.  That was not valid.", "id": 400}')
            return None

        return arguments

    # Normalize the keys in the hash table to all lowercase.
    def _normalize_keys(self, arguments):
        for key in arguments.keys():
            arguments[key.lower()] = arguments[key]
            logging.debug("Normalizing key " + key + " to " + key.lower() + ".")
        return arguments

    # Ensure that all of the keys required for every client access are in the
    # hash table.
    def _ensure_all_keys(self, arguments):
        all_keys_found = True

        for key in self.required_keys:
            if key not in arguments.keys():
                all_keys_found = False

        if not all_keys_found:
            logging.debug('400, {"result": null, "error": "All required keys were not found in the JSON document.  Look at the online help.", "id": 400}')
            self._send_http_response(400, '{"result": null, "error": "All required keys were not found in the JSON document.  Look at the online help.", "id": 400}')
            return False
        else:
            return True

if "__name__" == "__main__":
    print "No self tests yet."
    sys.exit(0)

