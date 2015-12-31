#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# This is my first serious attempt at writing an IRC bot in Python.  It uses
#   implements some of the protocol natively, and uses MegaHAL as its
#   conversation engine.  Don't expect this to be anything major, I'm just
#   playing around.

# By: The Doctor <drwho at virtadpt dot net>

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# - Use a real logger.

# Load modules.
from megahal import *

import argparse
import ConfigParser
import irc
import os
import random
import socket
import sys
import time

# Constants.

# Global variables.
# Path to the configuration file and handle to a ConfigParser instance.
config_file = ""
config = ""

# The IRC server, port, nick, and channel to default to.
irc_server = ""
irc_port = 6667
nick = "McCoyPauley"
channel = ""

# The nick of the bot's owner.
owner = ""

# How many backward chain links to run text through.  Defaults to three.
order = 3

# Criteria for which the bot will learn from its owner:
# - Four or more letters
# - Three or more words
# - No lone numbers
min_letters_per_word = 4
min words_per_line = 3

# The location of the database the Markov model data is kept in.  This defaults
# to ./.pymegahal-brain, per the MegaHAL python module's default.
brainfile = "./.pymegahal-brain"

# Handle for a MegaHAL brain object.
brain = ""

# In case the user wants to train from a corpus to initialize the Markov brain,
# this will be a full path to a training file.
training_file = ""

# Classes.

# Functions.

# Core code...
# Set up a command line argument parser, because that'll make it easier to play
# around with this bot.  There's no sense in not doing this right at the very
# beginning.
argparser = argparse.ArgumentParser(description="My first attempt at writing an IRC bot.  I don't yet know what I'm going to make it do.  For starters, it has an integrated Markov brain so it can interact with other people in the channel (and occasionally learn from them).")

# Set the default configuration file and command line option to specify a
# different one.
argparser.add_argument('--config', action='store',
    default='dixie_flatline_bot.py', help="Path to a configuration file for this bot.")

# Set the IRC server.
argparser.add_argument('--server', action='store',
    help="The IRC server to connect to.  Mandatory.")

# Set the port on the IRC server to connect to (defaults to 6667/tcp).
argparser.add_argument('--port', action='store', default=6667,
    help="The port on the IRC server to connect to.  Defaults to 6667/tcp.")

# Set the nickname the bot will log in with.
argparser.add_argument('--nick', action='store', default='MyBot',
    help="The IRC nick to log in with.  Defaults to MyBot.  You really should change this.")

# Set the channel the bot will attempt to join.
argparser.add_argument('--channel', action='store',
    help="The IRC channel to join.  No default.  Specify this without the \# because the shell will interpret it as a command and mess with you.")

# Set the nick of the bot's owner, which it will learn from preferentially.
argparser.add_argument('--owner', action='store',
    help="This is the nick of the bot's owner, so that it knows who to take commands and who to train its Markov brain from.")

# Set the number of backward links the Markov engine will look when generating
# responses (defaults to 3).
argparser.add_argument('--order', action='store', default=3,
    help="The number of backward links the Markov engine will look when generating responses (defaults to 3).  Once the brain is built, this can no longer be changed.")

# Path to the MegaHAL brain database.  If this file doesn't exist it'll be
# created, and unless a file to train the bot is supplied in another command
# line argument it'll have to train itself very slowly.
argparser.add_argument('--brain', action='store',
    help="Path to the MegaHAL brainfile.  If this file doesn't exist it'll be created, and you'll have to supply an initial training file in another argument.")

# Path to a training file for the MegaHAL brain.
argparser.add_argument('--trainingfile', action='store',
    help="Path to a file to train the Markov brain with if you haven't done so already.  It can be any text file so long as it's plain text and there is one entry per line.  If a brain already exists, training more is probably bad.  If you only want the bot to learn from you, chances are you don't want this.")

# Parse the command line arguments.
args = argparser.parse_args()

# If a configuration file is specified on the command line, load and parse it.
config = ConfigParser.ConfigParser()
if args.config:
    config_file = args.config
if not os.path.exists(config_file):
    print "Unable to open configuration file " + config_file + "."
    sys.exit(1)
config.read(config_file)

# IRC server to connect to.
if not args.server:
    print "ERROR: You must specify the hostname or IP of an IRC server at a minimum."
    sys.exit(1)
else:
    irc_server = args.server

# Port on the IRC server.
if args.port:
    irc_port = args.port

# Nickname to present as.
if args.nick:
    nick = args.nick

# Channel to connect to.
if not args.channel:
    print "ERROR: You must specify a channel to join."
    sys.exit(1)
else:
    channel = "#" + args.channel

# Nick of the bot's owner to follow around.
if args.owner:
    owner = args.owner
else:
    print "ERROR: You must specify the nick of the bot's owner."
    sys.exit(1)

# Order of the Markov chains to construct.
if args.order:
    order = args.order

# If a prebuilt brainfile is specified on the command line, try to load it.
if args.brain:
    brainfile = args.brain
    if not os.path.exists(brainfile):
        print "WARNING: The brainfile you've specified (" + brainfile + ") does not exist."
        sys.exit(1)

# If a training file is available, grab it.
if args.trainingfile:
    training_file = args.trainingfile

# Let's not let people re-train existing Markov brains.  Because I'm tired and
# punchy.
if args.brain and args.trainingfile:
    print "WARNING: It's a bad idea to re-train an existing brainfile with a new corpus."
    print "I'll figure out how to do that later."
    sys.exit(1)

# If an existing brain was specified, try to open it.  Else, create a new one
# using the training corpus.
brain = MegaHAL(order=order, brainfile=brainfile)
if training_file:
    print "Training the bot's Markov brain... this could take a while..."
    brain.train(training_file)
    print "Done!"

# Prime the RNG.
random.seed()



# Roll 1d10.  On a 1, post a response to the channel.  On a 2, post a reply
# and learn from it.
roll = random.randint(1, 10)
if roll == 1:
    print "Responding to text without adding to the Markov brain."
    sendmsg(ircsock, channel, brain.get_reply_nolearn(ircmsg))
    continue
if roll == 2:
    print "Responding to the text."
    sendmsg(ircsock, channel, brain.get_reply(ircmsg))
    brain.sync()

# Fin.
brain.sync()
brain.close()
sys.exit(0)

