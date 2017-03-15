#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# xmppclient.py - A module of exocortex_xmpp_bridge.py that implements the
#   XMPPClient() class to break the code out so it's more modular.
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

from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError, IqTimeout
from sleekxmpp.xmlstream import scheduler

import logging
import threading

import message_queue

# XMPPClient: XMPP client class.  Implemented using threading.Thread because
#   it'll spin out on its own to connect to the XMPP server, while the custom
#   REST API server handles the distribution of requests to other agents.
class XMPPClient(ClientXMPP):

    # Bot's friendly nickname.
    nickname = ""

    # This is the bot's designated owner, which controls whether or not it
    # responds to any commands.
    owner = ""

    # Handle to the /replies processor thread.
    replies_processor = None

    # Initialize new instances of the class.
    def __init__(self, username, password, owner):

        # Store the username, password and nickname as local attributes.
        self.nickname = username.split('@')[0].capitalize()

        # Register the bot's owner.
        self.owner = owner

        logging.debug("Username: " + username)
        logging.debug("Password: " + password)
        logging.debug("Construct's XMPP nickname: " + self.nickname)
        logging.debug("Construct's owner: " + self.owner)

        # Log into the server.
        logging.debug("Logging into the XMPP server...")
        ClientXMPP.__init__(self, username, password)

        # Register event handlers to process different event types.  A single
        # event can be processed by multiple event handlers...
        self.add_event_handler("failed_auth", self.failed_auth, threaded=True)
        self.add_event_handler("no_auth", self.no_auth, threaded=True)
        self.add_event_handler("session_start", self.session_start,
            threaded=True)
        self.add_event_handler("message", self.message, threaded=True)
        self.add_event_handler("disconnected", self.on_disconnect,
            threaded=True)

        # Start the /replies processing thread.
        self.schedule("replies_processor", 20, self.process_replies_queue,
            repeat=True)

    # Fires when the construct isn't able to authenticate with the server.
    def failed_auth(self, event):
        logging.critical("Unable to authenticate with the JID " + self.username)
        return

    # Fires when all authentication methods available to the construct have
    # failed.
    def no_auth(self, event):
        logging.critical("All authentication methods with the JID " + self.username + " have failed.")
        return

    # Fires whenever an XMPP session starts.  Just about anything can go in
    # here.  'event' is an empty dict.
    def session_start(self, event):
        now_online_message = ""

        logging.debug("Sending the bot's session presence to the server and requesting the roster.")
        self.send_presence()
        self.get_roster()

        # Construct a message for the bot's owner that consists of the list of
        # bots that access the message bridge, along with appropriate
        # plurality of nouns.
        if len(message_queue.message_queue.keys()) == 1:
            now_online_message = "The bot "
        else:
            now_online_message = "The bots "

        for key in message_queue.message_queue.keys():
            if key == 'replies':
                continue
            now_online_message = now_online_message + key + ", "
        now_online_message = now_online_message.strip(", ")

        if len(message_queue.message_queue.keys()) == 1:
            now_online_message = now_online_message + " is now online."
        else:
            now_online_message = now_online_message + " are now online."

        # Send the message to the bot's owner.
        self.send_message(mto=self.owner, mbody=now_online_message)

    # Event handler that fires whenever an XMPP message is sent to the bot.
    # 'received_message' represents a message object from the server.
    def message(self, received_message):
        message_sender = str(received_message.getFrom()).strip().split('/')[0]
        message_body = str(received_message['body']).strip()
        agent_name = ""
        command = ""
        acknowledgement = ""

        logging.debug("Value of XMPPClient.message().message_sender is: " + str(message_sender))
        logging.debug("Value of XMPPClient.message().message_body is: " + str(message_body))

        # Potential message types: normal, chat, error, headline, groupchat
        # Only pay attention to 'normal' and 'chat' messages.
        if received_message['type'] not in ('chat', 'normal'):
            return

        # If the sender isn't the bot's owner, ignore the message.
        if message_sender != self.owner:
            logging.debug("Received a command from invalid bot owner " + message_sender + ".")
            return

        # If the message body is empty (which some XMPP clients do just to
        # mess with us), ignore it.
        if message_body == "None":
            logging.debug("The XMPP client sent an empty message body which is interpreted as None.  Bluh.")
            return

        # The user is asking for online help.
        if message_body == "help":
            self._online_help()
            return

        # The user is asking for a status report.
        if message_body == "Robots, report.":
            self._status_report()
            return

        # Try to split off the bot's name from the message body.  If the
        # agent's name isn't registered, bounce.
        if ',' in message_body:
            agent_name = message_body.split(',')[0]
        else:
            agent_name = message_body.split(' ')[0]
        logging.debug("Agent name: " + agent_name)

        if agent_name not in message_queue.message_queue.keys():
            logging.debug("Command sent to agent " + agent_name + ", which doesn't exist on this bot.")
            response = "Request sent to agent " + agent_name + ", which doesn't exist on this bot.  Please check your spelling."
            self.send_message(mto=self.owner, mbody=response)
            return

        # Extract the command from the message body and clean it up.
        if ',' in message_body:
            command = message_body.split(',')[1]
        else:
            command = ' '.join(message_body.split(' ')[1:])
        command = command.strip()
        command = command.strip('.')
        logging.debug("Received request: " + command)

        # Push the request into the appropriate message queue.
        message_queue.message_queue[agent_name].append(command)
        logging.debug("Added request to " + agent_name + "'s message queue.")

        # Tell the bot's owner that the request has been added to the agent's
        # message queue.
        logging.debug("Sending acknowledgement of request to " + self.owner + ".")
        acknowledgment = "Your request has been added to " + agent_name + "'s request queue."
        self.send_message(mto=self.owner, mbody=acknowledgement)
        return

    # Helper method that returns online help when queried.
    def _online_help(self):
        logging.debug("Entering XMPPClient._online_help().")
        logging.debug("User has requested online help.")

        help_text = """
Supported commands:\n
- help - This online help.\n
- Robots, report. - List all constructs this bot is configured to communicate with.\n
To send a command to one of the constructs, use your XMPP client to send a message that looks something like this:\n
"[bot name], do this thing for me."\n
Individual constructs may have their own online help, so try sending the command "[bot name], help."\n
            """

        self.send_message(mto=self.owner, mbody=help_text)
        return

    # Helper method that returns a status report when queried.
    def _status_report(self):
        logging.debug("Entering XMPPClient._status_report().")
        response = "Contents of message queues are as follows:\n\n"
        for key in message_queue.message_queue.keys():
            if key == 'replies':
                continue
            response = response + "Agent " + key + ": "
            response = response + str(message_queue.message_queue[key]) + "\n"
        self.send_message(mto=self.owner, mbody=response)
        return

    # Thread that wakes up every n seconds and processes the bot's private
    # message queue (/replies).  If there are any, picks the least recently
    # used one out and sends it to the bot's owner.
    def process_replies_queue(self):
        logging.debug("Entering XMPPClient.process_replies_queue().")
        if len(message_queue.message_queue['replies']):
            reply = message_queue.message_queue['replies'].pop(0)
            self.send_message(mto=self.owner, mbody=reply)
        return

    # Fires whenever the bot's connection dies.  I need to figure out how to
    # make the bot wait for a random period of time and then try to reconnect
    # to the server.
    def on_disconnect(self, event):
        return

if "__name__" == "__main__":
    print "No self tests yet."
    sys.exit(0)

