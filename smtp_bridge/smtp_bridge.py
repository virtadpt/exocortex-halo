#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# smtp_bridge.py - A small server that pretends to be an SMTP server but
#   actually reformats all messages and forwards them over the configured XMPP
#   bridge server.  By default it only listens on the loopback address on port
#   25/tcp, but it can be configured differently.  Please note that the server
#   will need to be started as the root user if it's configured "normally" but
#   will automatically drop its privileges to nobody/nobody or nobody/nogroup
#   (also configurable because different distros use different UIDs and GIDs
#   for this).
#
#   Put all of your configuration options into a config file.  Treat this bot
#   just like any other SMTP server you might set up.

# By: The Doctor [412/724/301/703/415] <drwho at virtadpt dot net>

# License: GPLv3

# v2.0 - Ported to Python 3.
# v1.0 - Initial release.

# TO-DO:

# Load modules.
import argparse
import asyncore
import configparser
import grp
import json
import logging
import os
import os.path
import pwd
import requests
import sys

from smtpd import SMTPServer

# Global variables.
# Handles to a command line argument parser and the parsed args.
argparser = None
args = None

# Handle to logger object.
logger = None

# Handle to a configuration file parser.
config = None

# Server-level configuration options.
loglevel = ""
smtphost = ""
smtpport = 0
queue = ""
username = ""
group = ""

# Handle to an SMTP server object.
smtpd = None

# Classes.
class smtp_bridge(SMTPServer):
    headers = {"Content-type": "application/json"}

    # process_message(): Method that does the work of processing SMTP messages
    #   from the server.  It's overridden to take apart the message and send
    #   it to an XMPP bridge server.  Returns None, per the source code for
    #   smtpd.py (https://github.com/python/cpython/blob/3.7/Lib/smtpd.py)
    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        logger.debug("Entered smtp_bridge.process_message().")
        logger.debug("Value of peer: " + str(peer))
        logger.debug("Value of mailfrom: " + mailfrom)
        logger.debug("Value of rcpttos: " + str(rcpttos))
        logger.debug("Value of data: " + str(data))

        # Build the message to send.
        message = {}
        message["name"] = str(queue.split("/")[-1])
        message["reply"] = data.strip().decode()

        # Handle to a Request object.
        request = None

        # Attempt to send the message to the XMPP bridge.
        try:
            logger.debug("Sending message to queue: " + queue)
            request = requests.put(queue, headers=self.headers,
                data=json.dumps(message))
            request.raise_for_status()
        except:
            logger.debug("Got HTTP status code " + str(request.status_code) + ".")
            logger.warning("Connection attempt to message queue " + queue + " failed.")
            logger.debug(str(request))
        return None

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

# drop_privileges(): Function that drops the effective UID and GID of this
#   bot to something that isn't root for security's sake.  Takes two arguments,
#   the username and groupname as strings.  Returns True (it worked) or False
#   (it didn't).
def drop_privileges(username, group):
    logger.debug("Entered function drop_privileges().")

    # Current UID and GID.
    current_uid = os.getuid()
    current_gid = os.getgid()
    current_uid_name = pwd.getpwuid(current_uid)[0]
    current_gid_name = grp.getgrgid(current_gid)[0]
    logger.debug("Starting UID: " + str(current_uid) + " (" + current_uid_name + ")")
    logger.debug("Starting GID: " + str(current_gid) + " (" + current_gid_name + ")")

    # The effective UID and GID is what we want to switch to.
    effective_uid = pwd.getpwnam(username)[2]
    effective_gid = grp.getgrnam(group)[2]
    logger.debug("UID to switch to: " + str(effective_uid) + " (" + username + ")")
    logger.debug("GID to switch to: " + str(effective_gid) + " (" + group + ")")

    # Check for the obvious corner case - not running as root (say, we're
    # debugging or developing.)
    if current_uid != 0:
        logger.info("We're not running as root, we're already running as UID " + str(os.getuid()) + ".")
        return True

    if current_uid == 0:

        # Try to change the group ID first, so we'll still have permission to
        # do the root user ID later.
        try:
            logger.debug("Trying to drop group privileges...")
            os.setgid(effective_gid)
            logger.debug("Success!")
        except OSError as e:
            logger.error("Unable to drop group privileges! %s" % e)
            return False

        # Try to change the user ID.
        try:
            logger.debug("Trying to drop user privileges...")
            os.setuid(effective_uid)
            logger.debug("Success!")
        except OSError as e:
            logger.error("Unable to drop user privileges! %s" % e)
            return False

    # It worked.
    return True

# Core code...
# Set up the command line argument parser.
argparser = argparse.ArgumentParser(description="A bot that implements an SMTP server for other processes on the system to relay mail through, but instead forwards those messages to the bot's owner via an instance of the Exocortex XMPP Bridge.")

# Set the default config file and the option to set a new one.
argparser.add_argument("--config", action="store", default="./smtp_bridge.conf")

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument("--loglevel", action="store",
    help="Valid log levels: critical, error, warning, info, debug, notset.  Defaults to info.")

# Parse the command line arguments.
args = argparser.parse_args()

# Read and parse the configuration file.
config = configparser.ConfigParser()
if not os.path.exists(args.config):
    logging.error("Unable to find or open configuration file " +
        args.config + ".")
    sys.exit(1)
config.read(args.config)

# Set global config options.
queue = config.get("DEFAULT", "queue")
loglevel = config.get("DEFAULT", "loglevel")
smtphost = config.get("DEFAULT", "smtphost")
smtpport = config.get("DEFAULT", "smtpport")
username = config.get("DEFAULT", "username")
group = config.get("DEFAULT", "group")

# Figure out how to configure the logger.
if args.loglevel:
    loglevel = args.loglevel
loglevel = process_loglevel(loglevel.lower())
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Print debugging output.
logger.info("SMTP bridge is configured and running.")
logger.debug("Runtime configuration settings:")
logger.debug("Configuration file: " + args.config)
logger.debug("Message queue: " + queue)
logger.debug("SMTP host: " + str(smtphost))
logger.debug("SMTP port: " + str(smtpport) + "/tcp")
logger.debug("Username to drop privileges to: " + str(username))
logger.debug("Group to drop privileges to: " + str(group))

# Stand up an SMTP server.
# localaddr, upstreamaddr, (data_size_limit), (map), (enable_SMTPUTF8=False),
#   (decode_data=False)
smtpd = smtp_bridge((smtphost, int(smtpport)), (), enable_SMTPUTF8=True)
if not drop_privileges(username, group):
    print("ERROR: Unable to drop elevated privileges.  This isn't good!")
    sys.exit(1)
try:
    logger.info("Starting SMTP server daemon.")
    asyncore.loop()
except KeyboardInterrupt:
    print("Got a keyboard interrupt.  Terminating")

# Fin.
sys.exit(0)
