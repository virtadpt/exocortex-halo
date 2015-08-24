#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# exocortex_xmpp_bridge.py - A microservice that logs into an XMPP server with
#   credentials from a configuration file, builds message queues for Huginn
#   Huginn agent networks in the config file, and listens for messages sent 
#   from the designated owner.  Each message must contain the name of the
#   agent the command is for.  The microservice pushes messages for the agents
#   into matching message queues retrieved later via a REST interface.
#   Messages to unmatched agents are dropped and an error is sent back to the
#   sender if the address of origin is this agent's designated owner.

# TODO:
# - Write a signal handler that makes the agent reload its configuration file
#   (whether it's the default one or specified on the command line).

# By: The Doctor <drwho at virtadpt dot net>
#     0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

import ConfigParser
import logging
from optparse import OptionParser
import sleekxmpp
import sys

# XMPPBot: XMPP bot class built from SleekXMPP that connects to an XMPP server
#   specified in the configuration file with matching credentials.
class XMPPBot(sleekxmpp.ClientXMPP):

    # Initializer method for the XMPPBot class.
    def __init__(self, jid, password):
        super(XMPPBot, self).__init__(jid, password)

        # Set up an event handler for when the XMPPBot starts up.
        self.add_event_handler('session_start', self.start)

        # Set up an event handler that processes incoming messages.
        self.add_event_handler('message', self.message)

    # Method that fires as an event handler when XMPPBot starts running.
    def start(self, event):

        # Needed to tell the XMPP server "I'm here!"
        self.send_presence()

        # If the XMPP account has a roster ("Buddy list") on the server, pull
        # it.
        # Note: This can time out under bad conditions.  Consider putting it
        # inside a try/except to retry or error out.
        self.get_roster()

        logging.debug("I've successfully connected to the XMPP server.")

    # Method that fires as an event handler when an XMPP message is received
    # from someone
    def message(self, message):
        # Test to see if the message came from the agent's owner.  If it did
        # not, drop the message and return.
        if message['from'] != owner:
            logging.warn("Received a message from someone that isn't authorized.")
            logging.warn("Message was sent from JID " + message['from'] + ".")
            return

        # Potential message types: normal, chat, error, headline, groupchat
        if message['type'] in ('normal', 'chat'):
            # Extract the XMPP message body for processing.
            message_body = message['body']

            # Split off the part of the sentence before the first comma or the
            # first space.  That's where the name of the agent can be found.
            # Bad agent names wind up in spurious message queues, and will
            # eventually time out and be deleted by the MQTT broker.
            if ',' in message_body:
                agent = message_body.split(',')[0]
            else:
                agent = message_body.split(' ')[0]

            # Extract the command to the agent and clean it up.
            command = message_body.split(',')[1]
            command = command.strip()
            command = command.strip('.')
            command = command.lower()
            logging.debug(command)

            # Push the command into the agent's message queue.
            # MOOF MOOF MOOF

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
if __name__ == '__main__':
    # If we're running in a Python environment earlier than v3.0, set the
    # default text encoding to UTF-8 because XMPP requires it.
    if sys.version_info < (3, 0):
        reload(sys)
        sys.setdefaultencoding('utf-8')

    # Instantiate a command line options parser.
    optionparser = OptionParser()

    # Define command line switches for the bot, starting with being able to
    # specify an arbitrary configuration file for a particular bot.
    optionparser.add_option("-c", "--conf", dest="configfile", action="store",
        type="string", help="Specify a config file for this agent.  Defaults to exocortex_xmpp_bridge.conf.")

    # Add a command line option that lets you override the config file's
    # loglevel.  This is for kicking a bot into debug mode without having to
    # edit the config file.
    optionparser.add_option("-l", "--loglevel", dest="loglevel", action="store",
        help="Specify the default logging level of the bot.  Valid options are CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET.  Defaults to INFO.")

    # Parse the command line args.
    (options, args) = optionparser.parse_args()

    # Read the configuration file.  There is a command line argument for
    # specifying a configuration file, but it defaults to taking the name
    # of the bot and appending '.conf' to it.  Then load it into a config file
    # parser object.
    config = ConfigParser.ConfigParser()
    if options.configfile:
        # MOOF MOOF MOOF - test to see if the config file exists.
        config.read(options.configfile)
    else:
        # MOOF MOOF MOOF - test to see if the config file exists.
        config.read("exocortex_xmpp_bridge.conf")
    conf = config.sections()[0]

    # Get configuration options from the configuration file.
    owner = config.get(conf, "owner")
    username = config.get(conf, "username")
    password = config.get(conf, "password")

    # Get the names of the agents to set up queues for from the config file.
    # MOOF MOOF MOOF

    # Figure out how to configure the logger.  Start by reading from the config
    # file.
    config_log = config.get(conf, "loglevel").lower()
    if config_log:
        loglevel = process_loglevel(config_log)

    # Then try the command line.
    if options.loglevel:
        loglevel = process_loglevel(options.loglevel.lower())

    # Default to WARNING.
    if not options.loglevel and not loglevel:
        loglevel = logging.WARNING

    # Configure the logger with the base loglevel.
    logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")

    # Instantiate a copy of XMPPBot.
    xmppbot = XMPPBot(username, password)

    # Enable the Service Discovery plugin.
    xmppbot.register_plugin("xep_0030")

    # Enable the Ping plugin.
    xmppbot.register_plugin("xep_0199")

    # Set up a dictionary, the keys of which are the names of agents from the
    # configuration file.  The values are arrays which implement the message
    # queues.
    # MOOF MOOF MOOF

    # Connect to the XMPP server and commence operation.  SleekXMPP's state
    # engine will run inside its own thread because we need to contact other
    # services.
    if xmppbot.connect():
        xmppbot.process(block=False)
    else:
        logging.fatal("Uh-oh - unable to connect to JID " + username + ".")
        sys.exit(1)

    # Start up the Simple HTTP Server instance.
    # MOOF MOOF MOOF

# Fin.

