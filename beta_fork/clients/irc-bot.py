#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# This is my second serious attempt at writing an IRC bot in Python.  It uses
#   the Python module called irc (https://pythonhosted.org/irc/), which
#   implements the IRC protocol natively and interfaces with the
#   beta_fork/server.py process via HTTP (on the same host or another one).

# By: The Doctor <drwho at virtadpt dot net>

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# - Split some of the longer stuff in DixieBot.on_pubmsg() and
#   DixieBot().on_privmsg() out into separate methods.
# - Add 'ghost' support to the bot - once authenticated, the bot's owner can
#   send text to the channel the bot is sitting in (@Some message here...) and
#   get replies back via private messages.  !ghost on/off
# - Add a memo function.  Someone can send a privmsg to the bot and it'll sit
#   on the message until the bot's owner asks for it.  Tell the bot's owner how
#   many messages are waiting when they authenticate.
# - Make it possible for the bot to register itself with the server by passing
#   the server's API key on the command line.
# - Clean up how command line arguments are passed to the DixieBot constructor.
#   I think I can do better, but I need to get it working first.

# Load modules.
# Needed because we're doing floating point division in a few places.
from __future__ import division

import argparse
import ConfigParser
import irc.bot
import irc.strings
import json
import logging
import os
import random
import requests
import socket
import ssl
import sys
import time

# Constants.

# Global variables.
# Path to the configuration file and handle to a ConfigParser instance.
config_file = "irc.conf"
config = ""

# The IRC server, port, nick, and channel to default to.
irc_server = ""
irc_port = 0
nick = ""
channel = ""

# The nick of the bot's owner.
owner = ""

# The log level for the bot.  This is used to configure the instance of logger.
loglevel = ""

# Whether or not to use SSL/TLS to connect to the IRC server.
usessl = False

# The password the bot's owner will use to authenticate to the bot.  You can't
# always be sure that the owner will be able to get their nick so as a backup
# make it possible to authenticate to the bot.
password = ""

# Hostname the conversation engine is running on.
engine_host = ""

# Port the conversation engine is listening on.
engine_port = 0

# This particular bot's API key for accessing the conversation engine.
api_key = ""

# Classes.
# This is an instance of irc.bot which connects to an IRC server and channel
#   and shadows its owner.
class DixieBot(irc.bot.SingleServerIRCBot):

    # Class-level variables which form attributes.  These all refer to aspects
    # of the bot.
    channel = ""
    nick = ""
    owner = ""

    # Connection information.
    server = ""
    port = 0

    # The bot's owner's authentication password.
    password = ""

    # Is the bot's owner authenticated or not?
    authenticated = ""

    # Whether or not the connection is SSL/TLS encrypted or not.
    usessl = ""

    # Response engine's hostname and port.
    engine = ""

    # Bot's API key to interface with the response engine.
    api_key = ""

    # Methods on the connection object to investigate:
    # connect() - Connect to a server?
    # connected() - 
    # disconnect() -
    # get_nickname() - 
    # get_server_name() - 
    # info() - 
    # ircname() - 
    # is_connected() - See if the connection is still up?
    # part() - Leave channel?
    # privmsg() - Send privmsg?
    # quit() - Terminate IRC connection?
    # reconnect() - Reconnect to server?
    # send_raw() - 
    # stats() - 
    # time() - 

    def __init__(self, channel, nickname, server, port, owner, usessl,
        password, engine_host, engine_port, api_key):
        # Initialize the class' attributes.
        self.channel = channel
        self.nick = nick
        self.owner = owner
        self.server = server
        self.port = port
        self.password = password
        self.authenticated = False
        self.usessl = usessl
        self.engine = 'http://' + engine_host + ':' + engine_port
        self.api_key = api_key

        # Connection factory object handle.
        factory = ""

        # If SSL/TLS support is requested, pass the ssl.wrap_socket() method
        # as a keyword argument.
        if self.usessl:
            logger.debug("Constructing SSL/TLS server connector.")
            factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
        else:
            logger.debug("Constructing plaintext server connector.")
            factory = irc.connection.Factory()
 
        # Initialize an instance of this class by running the parent class'
        # Default initializer method.
        #
        # [(server, port)] can be a list of one or more (server, port) tuples
        # because it can connect to more than one at once.
        # The other two arguments are the bot's nickname and realname.
        logger.debug("Instantiating SingleServerIRCBot superclass.")
        irc.bot.SingleServerIRCBot.__init__(self, [(self.server, self.port)],
            self.nick, self.nick, connect_factory=factory)

    # This method fires if the configured nickname is already in use.  If that
    # happens, change the bot's nick slightly.
    # Note that the name of this method is specifically what the irc module
    # looks for.
    def on_nicknameinuse(self, connection, event):
        logger.info("Bot nickname " + self.nick + " is already taken.  Falling back to bot nickname " + self.nick + "_.")
        connection.nick(connection.get_nickname() + "_")

    # This method fires when the server accepts the bot's connection.  It joins
    # the configured channel.
    def on_welcome(self, connection, event):
        connection.join(self.channel)
        logger.info("Successfully joined channel " + self.channel + ".")

        # Just to be silly, roll 1d10.  On a 1, say hello to the channel.
        roll = random.randint(1, 10)
        if roll == 1:
            pause = random.randint(1, 10)
            time.sleep(pause)
            connection.privmsg(self.channel, "Hey, bro!  I'm " + self.nick + ", the best cowboy who ever punched deck!")

    # MOOF MOOF MOOF
    # This method fires if the bot gets kick/banned from a channel.

    # This method fires when the server disconnects the bot for some reason.
    # Ideally, the bot should try to connect again after a random number of
    # seconds.
    def on_disconnect(self, connection, event):
        logger.warn("Got bounced from channel " + self.channel + ".  Reconnecting.")
        pause = random.randint(1, 10)
        time.sleep(pause)
        irc.bot.SingleServerIRCBot.connect(self, [(self.server, self.port)],
            self.nick, self.nick)

    # This method would fire when the bot receives a private message.  For the
    # moment, if it's the bot's owner always learn from the text because this
    # is an ideal way to get more interesting stuff into the bot's brain.
    # It'll make a good place to look for and respond to specific commands,
    # too.
    def on_privmsg(self, connection, line):

        # IRC nick that sent a line to the bot in private chat.
        sending_nick = line.source.split("!~")[0]

        # Line of text sent from the channel or private message.
        irc_text = line.arguments[0]

        # Handle to an HTTP request object.
        http_connection = ""

        # JSON document containing responses from the conversation engine.
        json_response = {}

        # See if the owner is authenticating to the bot.
        if "!auth " in irc_text:
            logger.warn("IRC user " + sending_nick + " is attempting to authenticate to the bot.")
            if self.password in irc_text:
                connection.privmsg(sending_nick, "Authentication confirmed.  Welcome back.")
                self.owner = sending_nick
                self.authenticated = True
                return
            else:
                connection.privmsg(sending_nick, "Incorrect.")
                return

        # Handle messages from the bot's owner (if authenticated).
        if sending_nick == self.owner:
            if not self.authenticated:
                connection.privmsg(sending_nick, "You're not authenticated.")
                return

            # If the owner asks for online help, provide it.
            if irc_text == "!help" or irc_text == "!commands":
                connection.privmsg(sending_nick,
                    "Here are the commands I support:")
                connection.privmsg(sending_nick,
                    "!help and !commands - You're reading them right now.")
                connection.privmsg(sending_nick,
                    "!quit - Shut me down.")
                connection.privmsg(sending_nick,
                    "!auth - Authenticate your current IRC nick as my admin.")
                connection.privmsg(sending_nick, 
                    "!config - Send my current configuration.")
                connection.privmsg(sending_nick, 
                    "!ping - Ping the conversation engine to make sure I can contact it.")
                return

            # See if the owner is asking the bot to self-terminate.
            if irc_text == "!quit":
                logger.info("The bot's owner has told it to shut down.")
                connection.privmsg(sending_nick,
                    "I get the hint.  Shuttin' down.")
                sys.exit(0)

            # See if the owner is asking for the bot's current configuration.
            if irc_text == "!config":
                connection.privmsg(sending_nick, "Here's my current runtime configuration.")
                connection.privmsg(sending_nick, "Channel I'm connected to: " + self.channel)
                connection.privmsg(sending_nick, "Current nick: " + self.nick)
                connection.privmsg(sending_nick, "Server and port: " + self.server + " " + str(self.port) + "/tcp")
                if self.usessl:
                    connection.privmsg(sending_nick, "My connection to the server is encrypted.")
                else:
                    connection.privmsg(sending_nick, "My connection to the server isn't encrypted.")
                return

            # See if the owner is asking the bot to ping the conversation
            # engine's server.
            if irc_text == "!ping":
                connection.privmsg(sending_nick, "Pinging the conversation engine...")
                http_connection = requests.get(self.engine + "/ping")
                if http_connection.text == "pong":
                    connection.privmsg(sending_nick, "I can hit the conversation engine.")
                else:
                    connection.privmsg(sending_nick, "I don't seem to be able to reach the conversation engine.")
                return

            # Always learn from and respond to non-command private messages
            # from the bot's owner.
            json_response = self._teach_brain(irc_text)
            if json_response['id'] != 200:
                logger.warn("DixieBot.on_pubmsg(): Conversation engine returned error code " + str(json_response['id']) + ".")

            json_response = self._get_response(irc_text)
            if json_response['id'] != 200:
                logger.warn("DixieBot.on_pubmsg(): Conversation engine returned error code " + str(json_response['id']) + ".")
                return

            # Send the response text back to the bot's owner.
            connection.privmsg(sending_nick, json_response['response'])
            return
        else:
            logger.debug("Somebody messaged me.  The content of the message was: " + irc_text)

    # This method fires every time a public message is posted to an IRC
    # channel.  Technically, 'line' should be 'event' but I'm just now getting
    # this module figured out...
    def on_pubmsg(self, connection, line):
        # JSON document from the conversation engine.
        json_response = {}

        # IRC nick that sent a line to the channel.
        sending_nick = line.source.split("!~")[0]
        logger.debug("Sending nick: " + sending_nick)

        # Line of text sent from the channel.
        irc_text = line.arguments[0]

        # If the line is from the bot's owner, learn from it and then decide
        # whether to respond or not.  Just in case somebody grabs the nick of
        # the bot's owner, don't respond if they're not authenticated (because
        # that could go real bad, real fast...)
        if sending_nick == self.owner and self.authenticated:

            # If the bot's owner addressed it directly, always respond.  Just
            # make sure to remove the bot's nick from the text to minimize
            # spurious entries in the bot's brain.
            asked_directly = irc_text.split(':')[0].strip()
            if asked_directly == self.nick:
                logger.debug("The bot's owner addressed the construct directly.  This is a special corner case.")

                # Extract the dialogue from the text in the IRC channel.
                dialogue_text = irc_text.split(':')[1].strip()

                # Send a request to train the conversation engine on the text.
                logger.debug("Training engine on text: " + dialogue_text)
                json_response = self._teach_brain(dialogue_text)
                if json_response['id'] != 200:
                    logger.warn("DixieBot.on_pubmsg(): Conversation engine returned error code " + str(json_response['id']) + ".")
                    return

                # Get a response to the text from the channel.
                json_response = self._get_response(irc_text)
                if json_response['id'] != 200:
                    logger.warn("DixieBot.on_pubmsg(): Conversation engine returned error code " + str(json_response['id']) + ".")
                    return

                # Send the reply to the channel.
                connection.privmsg(self.channel, json_response['response'])
                return

            # Otherwise, just learn from the bot's owner.
            json_response = self._teach_brain(irc_text)
            if json_response['id'] != 200:
                logger.warn("DixieBot.on_pubmsg(): Conversation engine returned error code " + str(json_response['id']) + ".")
                return

            # Decide if the bot is going to respond or not.
            roll = random.randint(1, 10)
            if roll == 1:
                json_response = self._get_response(irc_text)
                if json_response['id'] != 200:
                    logger.warn("DixieBot.on_pubmsg(): Conversation engine returned error code " + str(json_response['id']) + ".")

                # connection.privmsg() can be used to send text to either a
                # channel or a user.
                connection.privmsg(self.channel, json_response['response'])
            return

        # If the line is not from the bot's owner, decide randomly if the bot
        # should learn from it, or learn from and respond to it.
        roll = random.randint(1, 10)
        if roll == 1:
            logger.debug("Learning from the last line seen in the channel.")
            json_response = self._teach_brain(irc_text)
            if json_response['id'] != 200:
                logger.warn("DixieBot.on_pubmsg(): Conversation engine returned error code " + str(json_response['id']) + ".")
            return

        if roll == 2:
            logger.debug("Learning from the last line seen in the channel and responding to it.")
            json_response = self._teach_brain(irc_text)
            if json_response['id'] != 200:
                logger.warn("DixieBot.on_pubmsg(): Conversation engine returned error code " + str(json_response['id']) + ".")

            json_response = self._get_response(irc_text)
            if json_response['id'] != 200:
                logger.warn("DixieBot.on_pubmsg(): Conversation engine returned error code " + str(json_response['id']) + ".")
                return
            connection.privmsg(channel, json_response['response'])
            return

    # This method should fire when a client in the current channel emits a QUIT
    # event (relayed by the server.  It detects the bot's owner disconnecting
    # and deauthenticates them.
    def on_quit(self, connection, event):
        sending_nick = event.source.split("!~")[0]
        if event.type == "quit" and sending_nick == self.owner and self.authenticated:
            logger.info("The bot's owner has disconnected.  Deauthenticating.")
            self.authenticated = False
            connection.privmsg(self.channel, "Seeya, boss.")
            return

    # Sends text to train the conversation engine on.
    def _teach_brain(self, text):

        # Custom headers required by the conversation engine.
        headers = { "Content-Type": "application/json" }

        # HTTP request object handle.
        http_request = ""

        # JSON documents sent to and received from the conversation engine.
        json_request = {}
        json_request['botname'] = self.nick
        json_request['apikey'] = self.api_key
        json_request['stimulus'] = text
        json_response = {}

        # Make an HTTP request to the conversation engine.
        http_request = requests.put(self.engine + "/learn", headers=headers,
            data=json_request)
        json_response = json.loads(http_request.text)
        return json_response

    # Gets a response from the conversation engine.  Return a response.
    def _get_response(self, text):

        # Custom headers required by the conversation engine.
        headers = { "Content-Type": "application/json" }

        # HTTP request object handle.
        http_request = ""

        # Response to send to the channel or user.
        response = ""

        # JSON documents sent to and received from the conversation engine.
        json_request = {}
        json_request['botname'] = self.nick
        json_request['apikey'] = self.api_key
        json_request['stimulus'] = text
        json_response = {}

        # Contact the conversation engine to get a response.
        http_request = requests.get(self.engine + "/response", headers=headers,
            data=json_request)
        json_response = json.loads(http_request.text)
        return json_response

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
# Set up a command line argument parser, because that'll make it easier to play
# around with this bot.  There's no sense in not doing this right at the very
# beginning.
argparser = argparse.ArgumentParser(description="My second attempt at writing an IRC bot.  I don't yet know what I'm going to make it do.  This bot connects back to a server running the conversation engine to get responses (and occasionally train it a little more).  Specifics for connecting to the server go in the configuration file.")

# Set the default configuration file and command line option to specify a
# different one.
argparser.add_argument('--config', action='store',
    default='irc.conf', help="Path to a configuration file for this bot.")

# Set the IRC server.
argparser.add_argument('--server', action='store',
    help="The IRC server to connect to.  Mandatory.")

# Set the port on the IRC server to connect to (defaults to 6667/tcp).
argparser.add_argument('--port', action='store', default=6667,
    help="The port on the IRC server to connect to.  Defaults to 6667/tcp.")

# Set the nickname the bot will log in with.
argparser.add_argument('--nick', action='store', default='McCoyPauley',
    help="The IRC nick to log in with.  Defaults to MyBot.  You really should change this.")

# Set the channel the bot will attempt to join.
argparser.add_argument('--channel', action='store',
    help="The IRC channel to join.  No default.  Specify this with a backslash (\#) because the shell will interpret it as a comment and mess with you otherwise.")

# Set the nick of the bot's owner, which it will learn from preferentially.
argparser.add_argument('--owner', action='store',
    help="This is the nick of the bot's owner, so that it knows who to take commands and who to train its Markov brain from.")

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument('--loglevel', action='store', default='logging.INFO',
    help='Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.')

# Whether or not to use SSL or TLS to connect to the IRC server.
argparser.add_argument('--ssl', action='store_true', default=False,
    help='Whether or not to use SSL/TLS to connect to the IRC server.  Possible settings are True or False.  Defaults to False.  If set to True, the default IRC port will be set to 6697/tcp unless you specify otherwise.')

# The bot's owner can give the bot its authentication password on the command
# line.
argparser.add_argument('--password', action='store',
    help="The password the bot's owner can use to authenticate to the bot and give it owners.  This will also change the bot's idea of what its owner's nick is in case that changes for whatever reason.")

# Parse the command line arguments.
args = argparser.parse_args()

# If a configuration file is specified on the command line, load and parse it.
config = ConfigParser.ConfigParser()
if args.config:
    config_file = args.config
    config.read(config_file)

# Get configuration options from the config file.
if os.path.exists(config_file):
    irc_server = config.get("DEFAULT", "server")
    irc_port = config.get("DEFAULT", "port")
    nick = config.get("DEFAULT", "nick")
    channel = config.get("DEFAULT", "channel")
    owner = config.get("DEFAULT", "owner")
    loglevel = config.get("DEFAULT", "loglevel").lower()
    usessl = config.getboolean("DEFAULT", "usessl")
    password = config.get("DEFAULT", "password")
    engine_host = config.get("DEFAULT", "engine_host")
    engine_port = config.get("DEFAULT", "engine_port")
    api_key = config.get("DEFAULT", "api_key")
else:
    print "Unable to open configuration file " + config_file + "."

# Figure out how to configure the logger.  Start by reading from the config
# file, then try the argument vector.
if loglevel:
    loglevel = process_loglevel(loglevel)
if args.loglevel:
    loglevel = process_loglevel(args.loglevel.lower())
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# IRC server to connect to.
if args.server:
    irc_server = args.server

# Port on the IRC server.
if args.port:
    irc_port = args.port

# Nickname to present as.
if args.nick:
    nick = args.nick

# Channel to connect to.
if args.channel:
    channel = args.channel

# Nick of the bot's owner to follow around.
if args.owner:
    owner = args.owner
logger.info("The bot's registered owner is " + owner + ".  Make sure this is correct.")

# Turn on SSL/TLS support.
if args.ssl:
    usessl = args.ssl

# IRCS is port 6997/tcp by default.  If the port isn't changed on the command
# line, silently reset the port the bot tries to log in on.
if args.ssl:
    irc_port = 6697

# Read the bot's authentication password from the command line if it exists.
if args.password:
    password = args.password

# If the bot doesn't have an authentication password set, don't let the bot
# start up because somebody will eventually take it over and that'll be bad.
if not password:
    print "You don't have a password set on the bot.  This means that anybody cold take"
    print "it over and do things with it.  That's no good.  Set a password in the config"
    print "file or on the command line and try again."
    sys.exit(1)

# Prime the RNG.
random.seed()

# Instantiate a copy of the bot class and activate it.
bot = DixieBot(channel, nick, irc_server, irc_port, owner, usessl, password,
    engine_host, engine_port, api_key)
bot.start()

# Fin.
sys.exit(0)

