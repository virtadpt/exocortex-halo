#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# This is the base class for an Exocortex bot that:
# - Reads a configuration file.  By default, if the name of the construct is
#   HAL (for example), it'll look in the current working directory for the
#   filename HAL.conf.
# - Logs into the XMPP server it considers home base.
# - Sends its on-startup status report to its owner's XMPP address as it
#   executes its startup process.
# - Opens a unique port on localhost that its REST API listens on.
# - Goes into an event loop in which it listens for commands to execute,
#   carries them out, and sends the results to its own via the configured
#   output XMPP address.

# - If commanded to restart, the bot will run its cleanup-and-shutdown
#   procedure without actually shutting down, and then go into its startup
#   cycle, which will cause it to re-load everything.
# - This can be a command in a private message from its owner or a signal from
#   the shell it's running under shell.

# http://localhost:31337/v1/event/get
# The REST API takes each command and emits an event that looks like this:
# {
#   "agent": "agentname",
#   "command": "some command that needs to be parsed.",
#   "guid": "<guid>"
# }

# Each agent network running in Huginn looks at each event, but if the value
# of the "agent" field doesn't match its name, it ignores it.  If it does
# match it'll POST back to the microservice telling it to delete it from the
# event queue:
# http://localhost:31337/v1/event/delete
# {
#   "guid": "<guid>"
# }

# By: The Doctor <drwho at virtadpt dot net>
#     0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3
# Pre-requisite modules have their own licenses.

# Load modules.
import json
import os
import random
import resource
import string
import sys
import logging
from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError, IqTimeout
import time
import uuid

# Classes.
class ExocortexBot(ClientXMPP):
    # This is a simple XMPP bot written using the SleekXMPP library which,
    # at the moment, logs into an XMPP server listening on the loopback host.
    # It also starts up a small web application server listening on whatever
    # host and port it's told to which makes received messages available in
    # the form of JSON documents (documented above).

    # Class attributes go up here so they're easy to find.
    owner = ""
    username = ""
    password = ""
    imalive = ""
    host = ""
    port = ""

    # A list of commands defined on bots descended from this particular class.
    # There's undoubtedly a better way to go about this, but it's late and I
    # don't want to forget to do this.
    commands = ['status', 'shut down/shutdown', 'help']

    # Initialize the bot when it's instantiated.
    def __init__(self, owner, username, password, imalive, host, port):

        self.owner = owner.split()[0]
        self.jid = username
        self.password = password
        self.imalive = imalive
        self.host = host
        self.port = port

        # Log into the server.
        ClientXMPP.__init__(self, jid, password)

        # Set appropriate event handlers for this session.  Please note that a
        # single event many be processed by multiple matching event handlers.
        self.add_event_handler("session_start", self.start, threaded=True)
        self.add_event_handler("message", self.message, threaded=True)

        # Register plugins to support XEPs.
        self.register_plugin('xep_0030') # Service discovery
        self.register_plugin('xep_0199') # Ping

    # Event handler the fires whenever an XMPP session starts (i.e., it
    # logs into the server on this JID.  You can put just about any session
    # initialization code here that you want.  The argument 'event' is an empty
    # dict.
    def start(self, event):
        # Tell the server the bot has initiated a session.
        self.send_presence()
        self.get_roster()

        # Start a private chat with the bot's owner.
        self.send_message(mto=self.owner, mbody="%s is now online." %
            self.botname)

    # Event handler that fires whenever a message is sent to this JID. The
    # argument 'msg' represents a message stanza.  This method is meant to be
    # extensible when the base class is used to build other kinds of bots.
    def message(self, msg):
        # Potential message types: normal, chat, error, headline, groupchat
        if msg['type'] in ('chat', 'normal'):
            # If it's not the bot's owner messaging, ignore.
            msg_from = str(msg.getFrom())
            msg_from = string.split(msg_from, '/')[0]
            if msg_from != self.owner:
                print "\n\nChat request did not come from self.owner.\n\n"
                return

            # To make parsing easier, lowercase the message body before
            # matching against it.
            message = msg['body'].lower()
            if "help" in message:
                self.send_message(mto=msg['from'],
                    mbody="Hello.  My name is %s.  I am a generic ExocortexBot bot.  %s  I support the following commands:\n\n%s" % (self.botname, self.function, self.commands))
                return

            # Return a status report to the user.
            if "status" in message:
                status = self._process_status(self.botname)
                self.send_message(mto=msg['from'], mbody=status)
                return

            # Print all known commands.
            if "list commands" in message or "commands" in message:
                self.send_message(mto=msg['from'],
                    mbody="This Exocortex bot supports the following commands:\n %s" % str(self.commands))
                return

            # If the user tells the bot to terminate, do so.
            # "quit"
            if "shut down" in message or "shutdown" in message:
                self._shutdown(msg['from'])

            # End of event handler.
            return

    # Helper method that cleanly shuts down the bot.  Broken out so that
    # it's not part of the parser's code, plus it makes it overloadable in the
    # future so that subclasses can extend it. The argument 'destination' is the
    # JID to send the shutdown messages to.
    def _shutdown(self, destination):
        # Alert the user that the bot is shutting down...
        self.send_message(mto=destination,
            mbody="%s is shutting down..." % self.botname)
        self.disconnect(wait=True)

        # Bounce!
        sys.exit(0)

    # This method prints out some basic system status information for the
    # user, should they ask for it.
    def _process_status(self, botname):
        procstat = ""

        # Pick information out of the OS that we'll need later.
        current_pid = os.getpid()
        procfile = "/proc/" + str(current_pid) + "/status"

        # Start assembling the status report.
        status = "%s is fully operational on %s.\n" % (botname, time.ctime())
        status = status + "I am operating from directory %s.\n" % os.getcwd()
        status = status + "My current process ID is %d.\n" % current_pid

        # Pull the /proc/<pid>/status info into a string for analysis.
        try:
            s = open(procfile)
            procstat = s.read()
            s.close()
        except:
            status = status + "I was unable to read my process status info.\n"

        # Determine how much RAM the bot is using.
        memory_utilization = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        status = status + "I am currently using %d KB of RAM.\n" % memory_utilization

        # Get the current system load.
        status = status + "The current system load is %s." % str(os.getloadavg())
        return status

# Core code...
if __name__ == '__main__':
    # I really need to put unit tests here.
    sys.exit(0)
# Fin.
