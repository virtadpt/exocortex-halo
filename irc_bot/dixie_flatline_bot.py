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

# Load modules.
from megahal import *

import argparse
import os
import random
import socket
import sys
import time

# Constants.
# There needs to be a delay between accessing the IRC server and JOINing a
# channel.
delay = 3

# Global variables.
# The IRC server, port, nick, and channel to default to.
irc_server = ""
irc_port = 6667
nick = "McCoyPauley"
channel = ""

# TCP socket descriptor used to connect to the IRC server.
ircsock = ""

# How many backward chain links to run text through.  Defaults to three.
order = 3

# The location of the database the Markov model data is kept in.  This defaults
# to ./.pymegahal-brain, per the MegaHAL python module's default.
brainfile = "./.pymegahal-brain"

# Handle for a MegaHAL brain object.
brain = ""

# In case we're starting from scratch, this will be a full path to a training
# file for the MegaHAL brain.
training_file = ""

# Classes.

# Functions.
# ping: Responds to IRC PING requests.  Takes one argument, a TCP socket object.
def ping(sock):
    sock.send("PONG :Pong\n")

# sendmsg: Sends arbitrary text to the channel.  Takes three args, a TCP socket
#   object, the name of the channel, and the message.
def sendmsg(sock, chan, msg):
    sock.send("PRIVMSG " + chan + " :" + msg + "\n")

# join_channel(): Joins an IRC channel.  Takes two args, a socket and the name
#   of the channel.
def join_channel(sock, chan):
    sock.send("JOIN " + chan + "\n")

# Core code...
# Set up a command line argument parser, because that'll make it easier to play
# around with this bot.  There's no sense in not doing this right at the very
# beginning.
argparser = argparse.ArgumentParser(description="My first attempt at writing an IRC bot.  I don't yet know what I'm going to make it do.")

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

# Set the number of backward links the Markov engine will look when generating
# responses (defaults to 3).
argparser.add_argument('--order', action='store', default=3,
    help="The number of backward links the Markov engine will look when generating responses (defaults to 3).")

# Path to the MegaHAL brainfile.  If this file doesn't exist it'll be created,
# and unless a file to train the bot is supplied in another command line
# argument it'll have to train itself very slowly.
argparser.add_argument('--brain', action='store',
    help="Path to the MegaHAL brainfile.  If this file doesn't exist it'll be created, and you'll have to supply an initial training file in another argument.")

# Path to a training file for the MegaHAL brain.
argparser.add_argument('--trainingfile', action='store',
    help="Path to a file to train the Markov brain with if you haven't done so already.  It can be any text file so long as it's plain text and there is one entry per line.")

# Parse the command line arguments.
args = argparser.parse_args()
if not args.server:
    print "ERROR: You must specify the hostname or IP of an IRC server at a minimum."
    sys.exit(1)
else:
    irc_server = args.server
if args.port:
    irc_port = args.port
if args.nick:
    nick = args.nick
if not args.channel:
    print "ERROR: You must specify a channel to join."
    sys.exit(1)
else:
    channel = "#" + args.channel
if args.order:
    order = args.order

# If a prebuilt brainfile is specified on the command line, try to load it.
if args.brain:
    brainfile = brain
    if not os.path.exists(brainfile):
        print "WARNING: The brainfile you've specified (" + brainfile + ") does not exist."
        sys.exit(1)

# If a training file is available, grab it.
if args.trainingfile:
    training_file = args.trainingfile

# Let's not people re-train existing brainfiles.  Because I'm tired and punchy.
if args.brain and args.trainingfile:
    print "WARNING: It's a bad idea to re-train an existing brainfile with a new corpus."
    print "I'll figure out how to let you do that later."
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

# Open a connection to the IRC server.
print "Connecting to IRC server..."
ircsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ircsock.connect((irc_server, irc_port))

# Connect to the IRC service.  The "\r\n" parts are crucial.
print "Sending ident information..."
ircsock.send("USER " + nick + " " + nick + " " + nick + " :"+ nick + "\r\n")
ircsock.send("NICK " + nick + "\r\n")

# Join the channel.
print "Connecting to channel..."
time.sleep(delay)
join_channel(ircsock, channel)
print "Done!"

# Loop while we're connected.
while True:
    # Get up to 2k from the server
    ircmsg = ircsock.recv(2048)

    # Clean up the line.
    ircmsg = ircmsg.strip("\n\r")

    # Detect and respond to IRC server pings, per the RFC.
    if "PING " in ircmsg:
        ping(ircsock)

    # Only pay attention to messages sent to a channel or directly.  Skip
    # the administrative stuff from the IRC server.
    if channel not in ircmsg:
        continue
    if " PRIVMSG " not in ircmsg:
        continue

    # Roll 1d10.  On a 1, post a response to the channel.  On a 2, post a reply
    # and learn from it.
    roll = random.randint(1, 10)
    if roll == 1:
        sendmsg(ircsock, channel, brain.get_reply_nolearn(ircmsg))
        continue
    if roll == 2:
        sendmsg(ircsock, channel, brain.get_reply(ircmsg))
        brain.sync()

# Fin.
brain.sync()
brain.close()
sys.exit(0)

