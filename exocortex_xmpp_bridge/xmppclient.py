#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# xmppclient.py - A module of exocortex_xmpp_bridge.py that implements the
#   XMPPClient() class to break the code out so it's more modular.
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# v6.0 - SleekXMPP is dead.  Ported to SliXMPP
#        (https://codeberg.org/poezio/slixmpp/).  This involved doing a lot of
#        reworking of the XMPP client stuff, so I figure it's worth a major
#        version.
#      - Restructured generated and customized strings to be more pythonic.
#      - Minor reformatting for readability.
#      - Fixed some incorrect comments because I'm a dumbass who was more
#        worried about getting things working than keeping the implicit docs
#        up to date.
#      - Turned XMPPClient.on_disconnect() into something more than just a
#        stub.  It should fire whenever the bot loses its link for some reason
#        and needs to log in again.
# v5.0 - Reworking for Python 3.
# v4.1 - Explicitly setting the stanza type to "chat" makes the bridge work
#        reliably with more XMPP clients (such as converse.js).
#      - Also fixed typos in some comments.  Oops.
#      - I've long since started using double quotes whever possible, so I went
#        back through and switched out single quotes for doubles wherever
#        possible.
# v4.0 - Refactored bot to break major functional parts out into separate
#        modules.
#      - Fixed a bug in which I miscounted the number of keys in the message
#        queue.  Oops.
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

from slixmpp import ClientXMPP
from slixmpp.exceptions import IqError, IqTimeout

import asyncio
import logging
import random
import time

import message_queue

# XMPPClient: XMPP client class.  Internally, this has changed a great deal
#   because I migrated the code to SliXMPP, which doesn't use threading anymore
#   but an asynchronous event system.  For example, the scheduler isn't a
#   separate object anymore but built in automatically (which eliminated one
#   import).
class XMPPClient(ClientXMPP):

    # Bot's friendly nickname.
    nickname = ""

    # This is the bot's designated owner, which controls whether or not it
    # responds to any commands.
    owner = ""

    # Handle to the /replies processor thread.
    replies_processor = None

    # Default stanza type to make the bridge work reliably with more clients.
    stanza_type = "chat"

    # Initialize new instances of the class.
    def __init__(self, username, password, owner):
        logging.debug("Entered xmppclient.XMPPClient.__init__().")

        # Store the username, password and nickname as local attributes.
        self.nickname = username.split("@")[0].capitalize()

        # Register the bot's owner.
        self.owner = owner

        logging.debug("Username: %s" % username)
        logging.debug("Password: %s" % password)
        logging.debug("Construct's XMPP nickname: " + self.nickname)
        logging.debug("Construct's owner: " + self.owner)

        # Log into the server.
        logging.debug("Logging into the XMPP server...")
        ClientXMPP.__init__(self, username, password)

        # Register event handlers to process different event types.  A single
        # event can be processed by multiple event handlers.  These are
        # organized (roughly) in the order that they would fire on startup,
        # beginning with various types of login failure.
        self.add_event_handler("failed_auth", self.failed_auth)
        self.add_event_handler("no_auth", self.no_auth)
        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)
        self.add_event_handler("disconnected", self.on_disconnect)

        # Start the /replies processing task now that we're logged in.
        self.schedule("replies_processor", 1, self.process_replies_queue,
            repeat=True)

    # Fires when the construct isn't able to authenticate with the server.
    def failed_auth(self, event):
        logging.critical("Unable to authenticate with the JID " + self.username)
        return

    # Fires when all authentication methods available to the construct have
    # failed.
    def no_auth(self, event):
        logging.critical("All authentication methods for the JID %s have failed." % self.username)
        return

    # Fires whenever an XMPP session starts.  Just about anything can go in
    # here.  "event" is an empty dict.
    def session_start(self, event):
        now_online_message = ""

        logging.debug("Sending the bot's session presence to the server and requesting the roster.")
        self.send_presence()
        self.get_roster()

        # Construct a message for the bot's owner that consists of the list of
        # bots that access the message bridge, along with appropriate
        # plurality of nouns.
        if len(list(message_queue.message_queue.keys())) == 2:
            now_online_message = "The bot "
        else:
            now_online_message = "The bots "

        for key in list(message_queue.message_queue.keys()):
            if key == "replies":
                continue
            now_online_message = now_online_message + key + ", "
        now_online_message = now_online_message.strip(", ")

        if len(list(message_queue.message_queue.keys())) == 2:
            now_online_message = now_online_message + " is now online."
        else:
            now_online_message = now_online_message + " are now online."

        # Send the message to the bot's owner.
        self.send_message(mto=self.owner, mbody=now_online_message,
            mtype=self.stanza_type)

    # Event handler that fires whenever an XMPP message is sent to the bot.
    # "received_message" represents a message object from the server.
    def message(self, received_message):
        message_sender = str(received_message.get_from()).strip().split("/")[0]
        message_body = str(received_message["body"]).strip()
        agent_name = ""
        command = ""
        acknowledgement = ""

        logging.debug("Value of XMPPClient.message().message_sender is: %s" %
            message_sender)
        logging.debug("Value of XMPPClient.message().message_body is: %s" %
            message_body)

        # Potential message types: normal, chat, error, headline, groupchat
        # Only pay attention to "normal" and "chat" messages.
        if received_message["type"] not in ("chat", "normal"):
            return

        # If the sender isn't the bot's owner, ignore the message.  We don't
        # owe the send a response for security reasons.
        if message_sender != self.owner:
            logging.debug("Received a command from invalid bot owner %s." %
                message_sender)
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
        if "," in message_body:
            agent_name = message_body.split(",")[0]
        else:
            agent_name = message_body.split(" ")[0]
        logging.debug("Agent name: %s" % agent_name)

        if agent_name not in list(message_queue.message_queue.keys()):
            response = "Request sent to agent " + agent_name + ", which doesn't exist on this bot.  Please check your spelling."
            logging.debug(response)
            self.send_message(mto=self.owner, mbody=response,
                mtype=self.stanza_type)
            return

        # Extract the command from the message body and clean it up.
        if "," in message_body:
            command = message_body.split(",")[1]
        else:
            command = " ".join(message_body.split(" ")[1:])
        command = command.strip()
        command = command.strip(".")
        logging.debug("Received request: %s" % command)

        # Push the request into the appropriate message queue.
        message_queue.message_queue[agent_name].append(command)
        logging.debug("Added request to %s's message queue." % agent_name)

        # Tell the bot's owner that the request has been added to the agent's
        # message queue.
        acknowledgment = "Your request has been added to " + agent_name + "'s request queue."
        logging.debug(acknowledgement)
        self.send_message(mto=self.owner, mbody=acknowledgement,
            mtype=self.stanza_type)
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

        self.send_message(mto=self.owner, mbody=help_text,
            mtype=self.stanza_type)
        return

    # Helper method that returns a status report when queried.
    def _status_report(self):
        logging.debug("Entering XMPPClient._status_report().")
        response = "Contents of message queues are as follows:\n\n"
        for key in list(message_queue.message_queue.keys()):
            if key == "replies":
                continue
            response = response + "Agent " + key + ": "
            response = response + str(message_queue.message_queue[key]) + "\n"
        self.send_message(mto=self.owner, mbody=response,
            mtype=self.stanza_type)
        return

    # Thread that wakes up every n seconds and processes the bot's private
    # message queue (/replies).  If there are any, picks the least recently
    # used one out and sends it to the bot's owner.
    def process_replies_queue(self):
        logging.debug("Entering XMPPClient.process_replies_queue().")
        if len(message_queue.message_queue["replies"]):
            reply = message_queue.message_queue["replies"].pop(0)
            self.send_message(mto=self.owner, mbody=reply,
                mtype=self.stanza_type)
        return

    # Fires whenever the bot's connection dies.  I need to figure out how to
    # make the bot wait for a random period of time and then try to reconnect
    # to the server.
    # What this is supposed to do is manually tear down the connection if it
    # dies (which is a belt-and-suspenders kind of thing, to make sure the
    # internal state is consistent) and then start it up again.
    def on_disconnect(self, event):
        logging.debug("Entering XMPPClient.on_disconnect().")
        logging.info("Connection to XMPP server disappeared.  Attempting to reconnect to JID %s." % self.username)

        # This holds the random period of time the bot will sleep during
        # reconnection attempts.  It's kept in a variable because the value
        # will be referenced in user output, so it shouldn't change.
        random_sleep = 0.0

        # Initialize the RNG from the current system time.  We're not
        # generating a cryptographic key or anything, so we can do this.
        random.seed()

        # Start a loop in which the bot will attempt to reconnect until it is
        # either successful or the user gives up and shuts the bot down.
        while True:

            # Force a disconnection attempt in case the XMPPClient's internal
            # state needs it.
            logging.debug("Forcing a disconnection.")
            self.disconnect(reason="Just woke up, trying again.")

            # Sleep for a random number of seconds (between 1 and 10, at a
            # guess) to give the network connection(s) a chance to stabilize.
            # The specific use case I'm thinking of is a laptop that has to
            # get back on the local wireless network and then re-negotiate a
            # VPN connection.  This can take a while from the user's (and thus
            # the bot's) point of view.
            random_sleep = random.rantint(1, 10)
            logging.debug("Going to sleep for %s seconds." % random_sleep)
            time.sleep(random_sleep)
            logging.debug("Woke up after %s seconds." % random_sleep)

            # Try reconnecting.  Re-use the random sleep as the timeout just
            # because we can.
            logging.info("Attempting to reconnect.")
            self.reconnect(wait=random_sleep, reason="Just woke up.")

            # Test the connection by sending the bot's presence and pulling its
            # roster.  We have to do this after a login anyway, so it kills
            # two birds with one stone.
            try:
                logging.debug("Pinging the server by sending a presence request and pulling the JID's roster.")
                self.send_presence()
                self.get_roster()

                # If the above two calls worked, break out of the loop because
                # login was successful.
                logging.info("Re-login successful!")
                break
            except:
                logging.warn("Re-login attempt failed.")

        logging.debug("Bounced out of the re-login attempt loop, exiting XMPPClient.on_disconnect().")
        return

if "__name__" == "__main__":
    print("No self tests yet.")
    sys.exit(0)
