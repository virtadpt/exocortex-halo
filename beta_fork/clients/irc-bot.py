#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# This is my second serious attempt at writing an IRC bot in Python.  It uses
#   the Python module called irc (https://pythonhosted.org/irc/), which
#   implements the IRC protocol natively and interfaces with the
#   beta_fork/server.py process via HTTP (on the same host or another one).
#
# Why is the class called DixieBot?  My first IRC bot was called DixieBot,
# after the Dixie Flatline
# (http://williamgibson.wikia.com/wiki/The_Dixie_Flatline).  The bot in
# question can still be found in earlier commits in this Git repository.  I
# repurposed the code to write this iteration of the bot.

# By: The Doctor <drwho at virtadpt dot net>

# License: GPLv3

# v1.0 - Initial release.
# v1.1 - Shook a lot of bugs out.  See the commit logs for details.
#      - Added wordfilter as a dependency because the bot can train itself
#        from other people in the channel, and that can be highly problematic
#        under some circumstances.  This is all stuff I don't say anyway, so
#        I'm fine with that (plus, I read the code for that module so I'm
#        okay with that; if you're not, fork() this repo and strip that code
#        out on your own, it's your problem now).
#      - Added a !join command, so the bot is now able to join channels you
#        tell it to.
#      - Added multi-channel support, which is surprisingly difficult to do.
# v1.2 - Added a respond/don't respond feature to the bot so the user can turn
#        decide whether or not the bot will respond to users on the server.

# TO-DO:
# - Add 'ghost' support to the bot - once authenticated, the bot's owner can
#   send text to the channel the bot is sitting in (@Some message here...) and
#   get replies back via private messages.  !ghost on/off
# - Other things to add to the bot:
#   listen for/stop listening for a particular regular expression
#   message a particular nick (for authenticating with an IRC service)
# - Add a memo function.  Someone can send a privmsg to the bot and it'll sit
#   on the message until the bot's owner asks for it.  Tell the bot's owner how
#   many messages are waiting when they authenticate.
# - Make it possible for the bot to register itself with the server by passing
#   the server's API key on the command line when it's started up.
# - Clean up how command line arguments are passed to the DixieBot constructor.
#   I think I can do better, but I need to get it working first.

# Load modules.
# Needed because we're doing floating point division in a few places.
from __future__ import division
from irc.dict import IRCDict
from wordfilter import Wordfilter

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

# Global variables.
# Path to the configuration file and handle to a ConfigParser instance.
config_file = "./irc.conf"
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

# Whether or not to respond to users saying things to the bot.
respond = None

# Classes.
# This is an instance of irc.bot which connects to an IRC server and channel
#   and shadows its owner.
class DixieBot(irc.bot.SingleServerIRCBot):

    # Class-level variables which form attributes.  These all refer to aspects
    # of the bot.
    joined_channels = IRCDict()
    canonical_name = ""
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

    # One instance of wordfilter.Wordfilter() to rule them all...
    wordfilter = None

    # Whether or not to use the conversation engine to respond?
    respond = None

    # Whether or not the bot's owner can speak through the bot by using
    # private messages.  By default, the bot doesn't let you do that.
    ghost = None

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

    def __init__(self, channels, nickname, server, port, owner, usessl,
        password, engine_host, engine_port, api_key, respond):

        # Initialize the class' attributes.
        for i in channels:
            self.joined_channels[i] = 1
        self.canonical_name = nick
        self.nick = nick
        self.owner = owner
        self.server = server
        self.port = port
        self.password = password
        self.authenticated = False
        self.usessl = usessl
        self.engine = 'http://' + engine_host + ':' + engine_port
        self.api_key = api_key
        self.wordfilter = Wordfilter()
        self.respond = respond
        self.ghost = False

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
        # default initializer method.
        #
        # [(server, port)] can be a list of one or more (server, port) tuples
        # because it can connect to more than one at once.
        # The other two arguments are the bot's nickname and realname.
        logger.debug("Instantiating SingleServerIRCBot superclass.")
        irc.bot.SingleServerIRCBot.__init__(self, [(self.server, self.port)],
            self.nick, self.nick, connect_factory=factory)
        logger.debug("Channels configured for this bot:")
        logger.debug("  " + str(self.joined_channels))

    # This method fires if the configured nickname is already in use.  If that
    # happens, change the bot's nick slightly.
    # Note that the name of this method is specifically what the irc module
    # looks for.
    def on_nicknameinuse(self, connection, event):
        logger.info("Bot nickname " + self.nick + " is already taken.  Falling back to bot nickname " + self.nick + "_.")
        connection.privmsg(self.owner, self.nick + " seems to be taken already.  Falling back to nickname " + self.nick + "_.")
        connection.nick(connection.get_nickname() + "_")

    # This method fires when the server accepts the bot's connection.  It walks
    # through the IRCDict of channels and tries to join each one.
    def on_welcome(self, connection, event):
        logger.debug("Entered DixieBot.on_welcome().")
        for channel in self.joined_channels:
            logger.debug("Trying to join channel " + channel + ".")
            connection.join(channel)
            logger.info("Joined channel " + channel + ".")
            connection.privmsg(self.owner, "Joined " + channel + ".")

            # Just to be silly, roll 1d10.  On a 1, say hello to the channel.
            roll = random.randint(1, 10)
            if roll == 1:
                pause = random.randint(1, 10)
                time.sleep(pause)
                logger.debug("Bot has randomly decided to announce itself.")
                connection.privmsg(channel, "Hey, bro!  I'm " + self.nick + ", the best cowboy who ever punched deck!")
        logger.debug("Exiting DixieBot.on_welcome().")

    # This method fires if the bot gets kicked from a channel.  The smart
    # thing to do is sleep for a random period of time (between one and three
    # minutes) before trying to join again.
    def on_kick(self, connection, event):
        delay = random.randint(60, 180)
        logger.debug("Got kicked from " + event.target + ".  Sleeping for " + str(delay) + " seconds.")
        connection.privmsg(self.owner, "Got kicked from " + event.target + ".  Sleeping for " + str(delay) + " seconds.")
        time.sleep(delay)
        logger.debug("Rejoining channel " + event.target + ".")
        connection.privmsg(self.owner, "Rejoining channel " + event.target + ".")
        connection.join(event.target)
        logger.info("Successfully re-joined channel " + event.target + ".")
        connection.privmsg(self.owner, "Successfully re-joined channel " + event.target + ".")
        return

    # This method fires if the bot gets kickbanned.
    def on_bannedfromchan(self, connection, event):
        logger.warn("Uh-oh - I got kickbanned from " + event.target + ".  I know when I'm not wanted.")
        self.privmsg(self.owner, "Uh-oh - I got kickbanned from " + event.target + ".  I know when I'm not wanted.")
        self.joined_channels.remove(event.target)
        return

    # This method fires when the server disconnects the bot for some reason.
    # Ideally, the bot should try to connect again after a random number of
    # seconds.
    def on_disconnect(self, connection, event):
        delay = random.randint(60, 180)
        logger.warn("Connection dropped from server " + self.server + ".  Sleeping for " + str(delay) + " seconds.")
        time.sleep(delay)
        logger.warn("Reconnecting to server " + self.server + " on port " + str(self.port) + ".")
        try:
            irc.bot.SingleServerIRCBot.connect(self, [(self.server, self.port)],
                self.nick, self.nick)
            logger.info("Successfully reconnected to server " + self.server + ".")
        except:
            logger.warn("Unable to reconnect to " + self.server + ".  Something's really wrong.")

    # This method fires when the bot receives a private message.  For the
    # moment, if it's the bot's owner always learn from the text because this
    # is an ideal way to get more interesting stuff into the bot's brain.
    # It'll make a good place to look for and respond to specific commands,
    # too.
    def on_privmsg(self, connection, line):

        # IRC nick that sent a line to the bot in private chat.
        sending_nick = line.source.split("!~")[0]

        # Line of text sent from the channel or private message.
        irc_text = line.arguments[0]

        # String that holds what may or may not be a channel name.
        possible_channel_name = None

        # String that may or may not hold a respond to a channel in ghost mode.
        irc_response = None

        # Handle to an HTTP request object.
        http_connection = ""

        # JSON document containing responses from the conversation engine.
        json_response = {}

        # See if the owner is authenticating to the bot.
        if "!auth " in irc_text:
            self._authenticate(connection, sending_nick, irc_text)
            return

        # Handle messages from the bot's owner (if authenticated).
        if sending_nick == self.owner:
            if not self.authenticated:
                connection.privmsg(sending_nick, "You're not authenticated.")
                return

            # If the owner asks for online help, provide it.
            if irc_text == "!help" or irc_text == "!commands":
                self._help(connection, sending_nick)
                return

            # See if the owner is asking the bot to self-terminate.
            if irc_text == "!quit":
                logger.info("The bot's owner has told it to shut down.")
                connection.privmsg(sending_nick,
                    "I get the hint.  Shuttin' down.")
                sys.exit(0)

            # See if the owner is asking for the bot's current configuration.
            if irc_text == "!config":
                self._current_config(connection, sending_nick)
                return

            # See if the owner is asking the bot to ping the conversation
            # engine's server.
            if irc_text == "!ping":
                self._ping(connection, sending_nick)
                return

            # See if the owner is asking the bot to change its nick.
            if "!nick" in irc_text:
                self._nick(connection, irc_text, sending_nick)
                return

            # See if the owner is asking the bot to join a channel.
            if "!join " in irc_text:
                self._join(connection, irc_text, sending_nick)
                return

            # See if the owner is flipping the self.respond flag.
            if "!respond" in irc_text:
                self._respond(connection, irc_text, sending_nick)
                return

            # See if the owner is asking for help on ghost mode.
            if "!ghosthelp" in irc_text:
                self._ghost_help(connection, sending_nick)
                return

            # See if the owner is flipping the self.ghost flag.
            if "!ghost" in irc_text:
                self._ghost_mode(connection, sending_nick)
                return

            # If the bot's in ghost mode, determine whether or not the bot's
            # owner has sent text destined for a channel the bot's sitting in.
            # If this is the case, send the channel the text sent by the
            # bot's owner.
            possible_channel_name = irc_text.split()[0]
            if self.ghost:
                if "#" in possible_channel_name:
                    logger.debug("Value of possible_channel_name: " + possible_channel_name)

                    # Test to see if the bot is in the channel in question.
                    in_channel = False
                    for channel in self.joined_channels:
                        if channel == possible_channel_name:
                            in_channel = True
                            break
                    if not in_channel:
                        logger.debug("Not in channel " + possible_channel_name + ".")
                        connection.privmsg(sending_nick,
                            "I'm not in channel " + possible_channel_name + ".")
                        return
                    logger.debug("In channel " + possible_channel_name + ".")

                    # Send the text to the channel.
                    irc_response = " ".join(irc_text.split()[1:])
                    logger.debug("Value of irc_response: " + irc_response)
                    connection.privmsg(possible_channel_name, irc_response)

            # Always learn from private messages from the bot's owner.  Do not
            # respond to them if the bot's in ghost mode.  Determine whether
            # or not a #channelname is at the head of the text and if so
            # elide it by setting the line of text from the IRC channel to
            # the IRC response which already has the #channelname removed.
            if "#" in possible_channel_name:
                irc_text = irc_response
                logger.debug("Set value of irc_text to: " + str(irc_text))

            json_response = json.loads(self._teach_brain(irc_text))
            if json_response['id'] != 200:
                logger.warn("DixieBot.on_privmsg(): Conversation engine returned error code " + str(json_response['id']) + ".")

            json_response = json.loads(self._get_response(irc_text))
            if json_response['id'] != 200:
                logger.warn("DixieBot.on_privmsg(): Conversation engine returned error code " + str(json_response['id']) + ".")
                return

            # Send the response text back to the bot's owner.
            connection.privmsg(sending_nick, json_response['response'])
            return
        else:
            logger.debug("Somebody messaged me.  The content of the message was: " + irc_text)

    # Helper method for authenticating the bot's owner.
    def _authenticate(self, connection, nick, text):
        logger.warn("IRC user " + nick + " is attempting to authenticate to the bot.")
        if self.password in text:
            connection.privmsg(nick, "Authentication confirmed.  Welcome back.")
            self.owner = nick
            self.authenticated = True
            return
        else:
            connection.privmsg(nick, "Incorrect.")
            return

    # Helper method that implements online help.
    def _help(self, connection, nick):
        connection.privmsg(nick,
            "Here are the commands I support:")
        connection.privmsg(nick,
            "!help and !commands - You're reading them right now.")
        connection.privmsg(nick,
            "!quit - Shut me down.")
        connection.privmsg(nick,
            "!auth - Authenticate your current IRC nick as my admin.")
        connection.privmsg(nick,
            "!config - Send my current configuration.")
        connection.privmsg(nick,
            "!ping - Ping the conversation engine to make sure I can contact it.")
        connection.privmsg(nick,
            "!nick <new nick> - Try to change my IRC nick.")
        connection.privmsg(nick,
            "!join <channel> - Join a channel.")
        connection.privmsg(nick,
            "!respond - Toggle respond/don't respond to users flag.")
        connection.privmsg(nick,
            "!ghosthelp - Get online help for ghost mode.")
        connection.privmsg(nick,
            "!ghost - Whether or not the bot's registered owner can remotely interact with a channel the bot's a member of using the bot as a client.")
        return

    # Helper method that tells the bot's owner what the bot's current runtime
    # configuration is.
    def _current_config(self, connection, nick):
        connection.privmsg(nick, "Here's my current runtime configuration.")
        connection.privmsg(nick, "Channels I'm connected to: ")
        for channel in self.joined_channels:
            connection.privmsg(nick, "  " + channel)
        connection.privmsg(nick, "Current nick: " + self.nick)
        connection.privmsg(nick, "Canonical name (for interacting with the conversation engine): " + self.canonical_name)
        connection.privmsg(nick, "Server and port: " + self.server + " " + str(self.port) + "/tcp")
        if self.usessl:
            connection.privmsg(nick, "My connection to the server is encrypted.")
        else:
            connection.privmsg(nick, "My connection to the server isn't encrypted.")
        if self.respond:
            connection.privmsg(nick, "I respond to people talking to me.")
        else:
            connection.privmsg(nick, "I don't respond to people talking to me.")
        return

    # Helper method that pings the bot's conversation engine.  I realize that
    # doing this is probably a little weird, but seeing as how I'm splitting
    # everything else out into helper methods to make adding functionality
    # later on easier I may as well.
    def _ping(self, connection, nick):
        connection.privmsg(nick, "Pinging the conversation engine...")
        http_connection = requests.get(self.engine + "/ping")
        if http_connection.text == "pong":
            connection.privmsg(nick, "I can hit the conversation engine.")
        else:
            connection.privmsg(nick, "I don't seem to be able to reach the conversation engine.")
        return

    # Helper method that will allow the bot to change its nick.
    def _nick(self, connection, text, nick):
        connection.privmsg(nick, "Trying to change my IRC nick...")
        self.nick = text.split()[1].strip()
        connection.nick(self.nick)
        logger.debug("New IRC nick: " + self.nick)
        connection.privmsg(nick, "Done.")
        return

    # Helper method that will allow the bot to join a channel.
    def _join(self, connection, text, nick):
        new_channel= text.split()[1].strip()
        connection.privmsg(nick, "Trying to join channel " + new_channel + ".")
        logger.debug("Trying to join channel " + new_channel + ".")
        connection.join(new_channel)
        self.joined_channels[new_channel] = 1
        connection.privmsg(nick, "Joined " + new_channel + ".")
        return

    # Helper method that flips the bot's mode from "respond when spoken to" to
    # don't respond when spoken to.
    def _respond(self, connection, text, nick):
        if self.respond == True:
            self.respond = False
            logger.info("Turn off the bot's auto-response mode.")
            connection.privmsg(nick, "I won't respond to people talking to me.")
            return
        if self.respond == False:
            self.respond = True
            logger.info("Turn on the bot's auto-response mode.")
            connection.privmsg(nick, "Now responding to people talking to me.")
            return

    # Send the user online help for ghost mode.
    def _ghost_help(self, connection, nick):
        connection.privmsg(nick, "Ghost mode lets you interact with any channel I'm sitting in remotely so you don't have to join it.")
        connection.privmsg(nick, "This is ideal if you want to maintain a certain degree of stealth.")
        connection.privmsg(nick, "I can join the channel from one server and interact with everyone like a bot, and you can connect from another server without joining any channels, !auth to me, and communicate through me.")
        connection.privmsg(nick, "If I get rumbled, I get bounced and your disposable server can be banned, and all you have to do is get a copy of my conversation engine to preserve me.  You should be okay.")
        connection.privmsg(nick, "Please note that if you have me join a number of busy channels you may not be able to keep up with all the traffic, so choose the channels I join wisely.  Keep the number small for best results.")
        connection.privmsg(nick, "Put the name of the channel you want me to send text to at the front of a private message, like this:")
        connection.privmsg(nick, "/msg botname")
        connection.privmsg(nick, "#somechannel Hello, world.")
        connection.privmsg(nick, "I will send activity in the channel back to you via the same privmsg as long as you're authenticated.")
        return

     # Flips the ghost mode flag.
    def _ghost_mode(self, connection, nick):
        if self.ghost == False:
            self.ghost = True
            logger.info("Ghost mode now activated.")
            connection.privmsg(nick, "Ghost mode activated.")
            connection.privmsg(nick, "You can now interact with the following channels through me: ")
            for channel in self.joined_channels:
                connection.privmsg(nick, "  " + channel)
            return
        if self.ghost == True:
            self.ghost = False
            logger.info("Ghost mode now deactivated.")
            connection.privmsg(nick, "Ghost mode deactivated.")
            return

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
                logger.debug("The bot's owner addressed the construct directly.  This is a special case.")

                # Extract the dialogue from the text in the IRC channel.
                dialogue_text = irc_text.split(':')[1].strip()

                # Send a request to train the conversation engine on the text.
                logger.debug("Training engine on text: " + dialogue_text)
                json_response = json.loads(self._teach_brain(dialogue_text))
                if json_response['id'] != int(200):
                    logger.warn("DixieBot.on_pubmsg(): Conversation engine returned error code " + str(json_response['id']) + ".")
                    return

                # If the bot is in ghost mode, do not respond.
                if self.ghost:
                    return

                # Get a response to the text from the channel.
                json_response = json.loads(self._get_response(irc_text))
                if json_response['id'] != int(200):
                    logger.warn("DixieBot.on_pubmsg(): Conversation engine returned error code " + str(json_response['id']) + ".")
                    return

                # Send the reply to the channel.
                connection.privmsg(line.target, json_response['response'])
                return

            # Otherwise, just learn from the bot's owner.
            json_response = json.loads(self._teach_brain(irc_text))
            if json_response['id'] != int(200):
                logger.warn("DixieBot.on_pubmsg(): Conversation engine returned error code " + str(json_response['id']) + ".")
                return

            # Check the respond/don't respond flag.  If it's set to False,
            # don't say anything.
            if not self.respond:
                return

            # If the respond/don't respond flag it set to True, decide if the
            # bot is going to respond or not.  To be polite to people, only
            # respond 5% of the time.  10% was too much.
            roll = random.randint(1, 100)
            if roll <= 5:
                json_response = json.loads(self._get_response(irc_text))
                if json_response['id'] != int(200):
                    logger.warn("DixieBot.on_pubmsg(): Conversation engine returned error code " + str(json_response['id']) + ".")
                    return

                # connection.privmsg() can be used to send text to either a
                # channel or a user.
                # Send the response.
                connection.privmsg(line.target, json_response['response'])
            return

        # If the line is not from the bot's owner, and the bot is in ghost
        # mode, relay the line to the bot's owner via privmsg.
        if self.ghost and self.authenticated:
            logger.debug("Relaying a line of text from " + line.target + " to the bot's owner.")
            connection.privmsg(self.owner, line.target + ":: " + irc_text)

        # If the line is not from the bot's owner, decide randomly if the bot
        # should learn from it, or learn from and respond to it.  Respect the
        # respond/don't respond flag.
        roll = random.randint(1, 10)
        if roll == 1:
            logger.debug("Learning from the last line seen in the channel.")
            if self.wordfilter.blacklisted(irc_text):
                logger.warn("Wordfilter: Nope nope nope...")
                return
            json_response = json.loads(self._teach_brain(irc_text))
            if json_response['id'] != int(200):
                logger.warn("DixieBot.on_pubmsg(): Conversation engine returned error code " + str(json_response['id']) + ".")
            return

        if roll == 2:
            logger.debug("Learning from the last line seen in the channel.  I might respond to it.")
            if self.wordfilter.blacklisted(irc_text):
                logger.warn("Wordfilter: Nope nope nope...")
                return
            json_response = json.loads(self._teach_brain(irc_text))
            if json_response['id'] != int(200):
                logger.warn("DixieBot.on_pubmsg(): Conversation engine returned error code " + str(json_response['id']) + ".")
                return

            # Check the respond/don't respond flag.  If it's set to False,
            # don't say anything.
            if not self.respond:
                return

            # Get and send a response.
            json_response = json.loads(self._get_response(irc_text))
            if json_response['id'] != int(200):
                logger.warn("DixieBot.on_pubmsg(): Conversation engine returned error code " + str(json_response['id']) + ".")
                return
            connection.privmsg(line.target, json_response['response'])
            return

    # This method should fire when a client in the current channel emits a QUIT
    # event relayed by the server.  It detects the bot's owner disconnecting
    # and deauthenticates them.
    def on_quit(self, connection, event):
        sending_nick = event.source.split("!~")[0]
        if event.type == "quit" and sending_nick == self.owner and self.authenticated:
            logger.info("The bot's owner has disconnected.  Deauthenticating.")
            self.authenticated = False
            connection.privmsg(line.target, "Seeya, boss.")
            return

    # Sends text to train the conversation engine on.
    def _teach_brain(self, text):

        # Custom headers required by the conversation engine.
        headers = { "Content-Type": "application/json" }

        # HTTP request object handle.
        http_request = ""

        # JSON documents sent to and received from the conversation engine.
        json_request = {}
        json_request['botname'] = self.canonical_name
        json_request['apikey'] = self.api_key
        json_request['stimulus'] = text
        json_response = {}

        # Make an HTTP request to the conversation engine.
        http_request = requests.put(self.engine + "/learn", headers=headers,
            data=json.dumps(json_request))
        json_response = json.loads(http_request.content)
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
        json_request['botname'] = self.canonical_name
        json_request['apikey'] = self.api_key
        json_request['stimulus'] = text
        json_response = {}

        # Contact the conversation engine to get a response.
        http_request = requests.get(self.engine + "/response", headers=headers,
            data=json.dumps(json_request))
        json_response = json.loads(http_request.content)
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
argparser.add_argument('--nick', action='store',
    help="The IRC nick to log in with.  Defaults to MyBot.  You really should change this.")

# Set the channel the bot will attempt to join.
argparser.add_argument('--channel', action='store',
    help="The IRC channel to join.  No default.  Specify this with a backslash (\#) because the shell will interpret it as a comment and mess with you otherwise.  If you want to specify more than one you'll have to put them in the configuration file.")

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

# The bot's owner can decide whether or not the bot will respond to other users
# by default.  Defaults to True.
argparser.add_argument('--respond', action='store_true', default=True,
    help='Whether or not the bot will respond to users talking directly to the bot.  Possible settings are True or False.  Defaults to True.  If you want the bot to be silent, set this to False.')

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
    channel = config.get("DEFAULT", "channel").split(',')
    owner = config.get("DEFAULT", "owner")
    loglevel = config.get("DEFAULT", "loglevel").lower()
    usessl = config.getboolean("DEFAULT", "usessl")
    password = config.get("DEFAULT", "password")
    engine_host = config.get("DEFAULT", "engine_host")
    engine_port = config.get("DEFAULT", "engine_port")
    api_key = config.get("DEFAULT", "api_key")
    respond = config.get("DEFAULT", "respond")
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

# Remember - command line arguments override settings in the config file!
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
    channel = args.channel.split(',')

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
    print """
You don't have a password set on the bot.  This means that anybody cold take
it over and do things with it.  That's no good.  Set a password in the config
file or on the command line and try again.
"""
    sys.exit(1)

# Flip the bit on the respond/don't respond flag.
if args.respond:
    respond = args.respond

# Prime the RNG.
random.seed()

# Instantiate a copy of the bot class and activate it.
bot = DixieBot(channel, nick, irc_server, irc_port, owner, usessl, password,
    engine_host, engine_port, api_key, respond)
bot.start()

# Fin.
sys.exit(0)

