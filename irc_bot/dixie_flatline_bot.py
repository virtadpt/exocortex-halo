#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# This is my first serious attempt at writing an IRC bot in Python.  It uses
#   the Python module called irc (https://pythonhosted.org/irc/), which
#   implements the IRC protocol natively, and also uses MegaHAL as its
#   conversation engine.  Don't expect this to be anything major, I'm just
#   playing around to find good and bad ways of doing this.

# By: The Doctor <drwho at virtadpt dot net>

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# - SSL/TLS support.

# Load modules.
# Needed because we're doing floating point division in a few places.
from __future__ import division

from cobe.brain import Brain

import argparse
import ConfigParser
import irc.bot
import irc.strings
import logging
import os
import random
import socket
import ssl
import sys
import time

# Constants.

# Global variables.
# Path to the configuration file and handle to a ConfigParser instance.
config_file = "dixie_flatline_bot.conf"
config = ""

# The IRC server, port, nick, and channel to default to.
irc_server = ""
irc_port = 0
nick = ""
channel = ""

# The nick of the bot's owner.
owner = ""

# The location of the database the Markov model data is kept in.  The module
# defaults to ./cobe.brain but we specify another one later in the code.
brainfile = ""

# Handle for a Cobe brain object.
brain = ""

# In case the user wants to train from a corpus to initialize the Markov brain,
# this will be a full path to a training file.
training_file = ""

# The log level for the bot.  This is used to configure the instance of logger.
loglevel = ""

# Whether or not to use SSL/TLS to connect to the IRC server.
usessl = False

# Classes.
# This is an instance of irc.bot which connects to an IRC server and channel
#   and shadows its owner.
class DixieBot(irc.bot.SingleServerIRCBot):

    # Class-level variables which form attributes.
    channel = ""
    nick = ""
    owner = ""

    # Handle to the Markov brain.
    brain = ""

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

    def __init__(self, channel, nickname, server, port, nick, owner, brain,
        usessl):
        # Initialize the class' attributes.
        self.channel = channel
        self.nick = nick
        self.owner = owner
        self.brain = brain

        # Connection factory object handle.
        factory = ""

        # If SSL/TLS support is requested, pass the ssl.wrap_socket() method
        # as a keyword argument.
        if usessl:
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
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nick, nick,
            connect_factory=factory)

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
        logger.info("Successfully joined channel " + self.channel + ".")
        connection.join(self.channel)

    # This method fires when the server disconnects the bot for some reason.
    # Ideally, the bot should try to connect again after a random number of
    # seconds.
    def on_disconnect(self, connection, event):
        logger.warn("Got bounced from channel " + self.channel + ".  Reconnecting.")
        pause = random.randint(1, 10)
        time.sleep(pause)
        irc.bot.SingleServerIRCBot.connect(self, [(server, port)], nick, nick)
        pass

    # This method would fire when the bot receives a private message.  For the
    # moment, if it's the bot's owner always learn from the text because this
    # is an ideal way to get more interesting stuff into the bot's brain.
    # It'll make a good place to look for and respond to specific commands,
    # too.
    def on_privmsg(self, connection, line):

        # IRC nick that sent a line to the bot in private chat.
        sending_nick = line.source.split("!~")[0]

        # Line of text sent from the channel.
        irc_text = line.arguments[0]

        # If it was the bot's owner, always learn from the text.
        if sending_nick == self.owner:
            # See if the owner is asking the bot to self-terminate.
            if irc_text == "!quit":
                logger.info("The bot's owner has told it to shut down.")

            logger.debug("The bot's owner messaged the construct directly.  This is a special corner case - learning from the text.")
            self.brain.learn(irc_text)
            return
        else:
            logger.debug("Somebody messaged me.  The content of the message was: " + irc_text)

    # This method fires every time a public message is posted to an IRC
    # channel.  Technically, 'line' should be 'event' but I'm just now getting
    # this module figured out...
    def on_pubmsg(self, connection, line):

        # IRC nick that sent a line to the channel.
        sending_nick = line.source.split("!~")[0]

        # Line of text sent from the channel.
        irc_text = line.arguments[0]

        # If the line is from the bot's owner, learn from it and then decide
        # whether to respond or not.
        if sending_nick == self.owner:

            # If the bot's owner addressed it directly, always respond.  Just
            # make sure to remove the bot's nick from the text to minimize
            # spurious entries in the bot's brain.
            asked_directly = irc_text.split(':')[0].strip()
            if asked_directly == self.nick:
                logger.debug("The bot's owner addressed the construct directly.  This is a special corner case.")
                self.brain.learn(irc_text.split(':')[1].strip())
                reply = self.brain.reply(irc_text)
                connection.privmsg(self.channel, reply)
                return

            # Otherwise, just learn from the bot's owner.
            logger.debug("Learning from text from the bot's owner.")
            self.brain.learn(irc_text)

            # Decide if the bot is going to respond or not.
            roll = random.randint(1, 10)
            if roll == 1:
                logger.debug("Posting a response to the channel.")
                reply = self.brain.reply(irc_text)

                # connection.privmsg() can be used to send text to either a
                # channel or a user.
                connection.privmsg(self.channel, reply)
            return

        # If the line is not from the bot's owner, decide randomly if the bot
        # should learn from it, or learn from and respond to it.
        roll = random.randint(1, 10)
        if roll == 1:
            logger.debug("Learning from the last line seen in the channel.")
            self.brain.learn(irc_text)
            return
        if roll == 2:
            logger.debug("Learning from the last line seen in the channel and responding to it.")
            self.brain.learn(irc_text)
            reply = self.brain.reply(irc_text)
            connection.privmsg(channel, reply)
            return

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
argparser = argparse.ArgumentParser(description="My first attempt at writing an IRC bot.  I don't yet know what I'm going to make it do.  For starters, it has an integrated Markov brain so it can interact with other people in the channel (and occasionally learn from them).")

# Set the default configuration file and command line option to specify a
# different one.
argparser.add_argument('--config', action='store',
    default='dixie_flatline_bot.conf', help="Path to a configuration file for this bot.")

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

# Path to the Cobe brain database.  If this file doesn't exist it'll be
# created, and unless a file to train the bot is supplied in another command
# line argument it'll have to train itself very slowly.
argparser.add_argument('--brain', action='store', default='./rom.construct',
    help="Path to the construct's brain.  If this file doesn't exist it'll be created, and you'll have to supply an initial training file in another argument.")

# Path to a training file for the Markov brain.
argparser.add_argument('--trainingfile', action='store',
    help="Path to a file to train the Markov brain with if you haven't done so already.  It can be any text file so long as it's plain text and there is one entry per line.  If a brain already exists, training more is probably bad.  If you only want the bot to learn from you, chances are you don't want this.")

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument('--loglevel', action='store', default='logging.INFO',
    help='Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.')

# Whether or not to use SSL or TLS to connect to the IRC server.
argparser.add_argument('--ssl', action='store_true', default=False,
    help='Whether or not to use SSL/TLS to connect to the IRC server.  Possible settings are True or False.  Defaults to False.  If set to True, the default IRC port will be set to 6697/tcp unless you specify otherwise.')

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
    brainfile = config.get("DEFAULT", "brain")
    loglevel = config.get("DEFAULT", "loglevel").lower()
    usessl = config.getboolean("DEFAULT", "usessl")
else:
    print "Unable to open configuration file " + config_file + "."

# Figure out how to configure the logger.  Start by reading from the config
# file, then try the argument vector.
if loglevel:
    loglevel = process_loglevel(loglevel)
if args.loglevel:
    loglevel = process_loglevel(args.loglevel.lower())

# Configure the logger.
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

logger.debug("Command line argument vector: " + str(args))

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

# If a prebuilt brainfile is specified on the command line, try to load it.
if args.brain:
    brainfile = args.brain
    logger.info("The bot's personality construct file is " + brainfile + ".  Make sure this is correct.")
    if not os.path.exists(brainfile):
        logger.fatal("WARNING: The personality construct file specified (" + brainfile + ") does not exist.")
        sys.exit(1)

# If a training file is available, grab it.
if args.trainingfile:
    training_file = args.trainingfile

# Let's not let people re-train existing Markov brains.  Because I'm tired and
# punchy.
if args.brain and args.trainingfile:
    logger.fatal("WARNING: It's a bad idea to re-train an existing brainfile with a new corpus.  I'll figure out how to do that later.")
    sys.exit(1)

# Instantiate a copy of the Cobe brain and try to load the database.  If the
# brain file doesn't exist Cobe will create it.
brain = Brain(brainfile)
if training_file:
    if os.path.exists(training_file):
        logger.info("Training the bot's Markov brain... this could take a while...")
        brain.start_batch_learning()  
        file = open(training_file)
        for line in file.readlines():
            brain.learn(line)
        brain.stop_batch_learning()  
        file.close()
        logger.info("Done!")
    else:
        logger.warn("Unable to open specified training file " + training_file + ".  The construct's going to have to learn the long way 'round.")

# Turn on SSL/TLS support.
if args.ssl:
    usessl = args.ssl

# IRCS is port 6997/tcp by default.  If the port isn't changed on the command
# line, silently reset the port the bot tries to log in on.
if args.ssl:
    irc_port = 6697

# Prime the RNG.
random.seed()

# Instantiate a copy of the bot class and activate it.
bot = DixieBot(channel, nick, irc_server, irc_port, nick, owner, brain, usessl)
bot.start()

# Fin.
sys.exit(0)

