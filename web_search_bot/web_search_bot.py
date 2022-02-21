#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# web_search_bot.py - Bot written in Python that polls a RESTful message queue
#   for search commands of the form "<botname>, get me <number of hits> hits
#   for <search terms>", runs the searches on an instance of Searx, and e-mails
#   them to the user (or a designated e-mail address).
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v5.7 - Fixed some help and error text that's been annoying me for a while.
#      - Changed some comment alignment.
# v5.6 - Fixed a bug where Searx crashing could take the bot down with it.
#      - Minor edits to the message text that reflect how I'm changing shortcode
#        use.
# v5.5 - Fixed a bug in which mailing search results didn't work.  I broke
#   this when I pulled the comand parser into a separate file.
# v5.4 - Pulled out search category code.  It never worked right.
# v5.3 - Added some new commands to the parser to implement searching in
#        specific Searx categories.
#      - Added code to pull the list of known categories from Searx.
#      - Split the command parser out into a separate module.
#      - Moved the stuff queried from the Searx /config document into a
#        separate global module.
#      - Broke the send_message_to_user() function out into the globals
#        module.  Had to rework it a bit.
#      - Broke some of the local config stuff out into the globals module
#        to neaten things up a bit.
#      - How the hell did I not put the "query Searx" bit inside a
#        try..except? Note to self: Never assume that the configured Searx
#        instance is responsive.
# v5.2 - Reworked the startup logic so that being unable to immediately
#        connect to either the message bus or the intended service is a
#        terminal state.  Instead, it loops and sleeps until it connects and
#        alerts the user appropriately.
# v5.1 - Made it possible to optionally define additional user text to add to
#        the bot's online help.  My use case for this is when you run multiple
#        instances of this bot and you want to keep them all straight by
#        customizing their personae a bit.
#      - Made it possible to optionally define the "I'm doing stuff" text the
#        bot sends when it's executing commands.
#      - Changed the default polling time to 10 seconds, because this bot
#        won't be run on a Commodore 64...
#      - Broke online help out into a separate function.
#      - Updated the comments for the function declarations to match other
#        bots in the suite.
# v5.0 - Ported to Python 3.
#      - Deleted the regex matcher because it's not used.
# v4.0 - Added the ability to tell the bot to run a search on a particular
#        search engine that Searx has enabled.
#      - Added a function that pulls a list of search engines the configured
#        Searx instance has enabled and stores them locally so they can be used
#        to run specific, targeted searches.
#      - Updated online help.
#      - Added the ability to list the search engines Searx has enabled.
# v3.0 - Rewrote the bot's command parser using PyParsing
#        (http://pyparsing.wikispaces.com/) because I got tired of trying
#        to maintain my own parser.  This is much more robust.
# v2.0 - Rewrote much of this bot's functionality to use Searx
#        (https://github.com/asciimoo/searx) rather than a user-supplied list
#        of arbitrary search engines.  This means that it's possible to
#        customize the general kinds of searches you can potentially run based
#        upon which Searx instances you use (by standing up more than one copy
#        of this bot) and each Searx instance can have a different combination
#        of sites to search turned on (such as a personal and a public YaCy
#        instance) or different custom Searx engines installed.
#      - Now tops out at fifty (50) search results.
#      - Made some of the code a little less awkward.
# v1.1 - Added a "no search results found" handler.
#      - Added an error handler for the case where contacting the message queue
#        either times out or fails outright.
#      - Added functionality which makes it possible to e-mail search results
#        to arbitrary addresses.
#      - Moved the list of links to filter out of the returned HTML into the
#        configuration file and added some code to read them in and clean them
#        up.  It'll be much easier to maintain that way.
#      - Got rid of the command line option where you can manually pass a
#        search request to the bot for testing.
# v1.0 - Initial release.

# TO-DO:
# - Add a feature such that Web Search Bot can optionally be configured to
#   ONLY search a defined subset of the enabled search engines of the Searx
#   instance it's configured for.  For example, the Searx instance could be
#   normally configured, but a copy of Web Search Bot could be configured to
#   only search Google.  This would probably take the form of transparently
#   prepending the !g bang code to the search term before encoding it to pass
#   to Searx.  This would also imply some sanity checking code to make sure
#   those configured !bangs are actually enabled in Searx's /config dump.
# - Pull the argument vector and config file parsing stuff into their own
#   functions to neaten up the core code.
# - Break out the "handle HTTP result code" handler into a function.
# - Break up the main loop into a few functions to make it easier to read.
# - Replace the tuple returned by the parser with something a bit more
#   sensible.  This bot's grown a lot and something like a hash table (with a
#   couple of key checks) seems like it'd be a better solution.

# Load modules.
from email.message import Message
from email.header import Header
from email.mime.text import MIMEText

import argparse
import configparser
import json
import logging
import os
import pyparsing as pp
import requests
import smtplib
import sys
import time

import globals
import parser

# Constants.

# Global variables.
# Base URL to a Searx instance.
searx = ""

# Handle to a logging object.
logger = ""

# Path to and name of the configuration file.
config_file = ""

# Loglevel for the bot.
loglevel = logging.INFO

# URL to the message queue to take marching orders from.
message_queue = ""

# Default e-mail address to send search results to.
default_email = ""

# How often to poll the message queues for orders.
polling_time = 10

# Search request sent from the user.
search_request = ""

# The e-mail address to send search results to (if applicable).
destination_email_address = ""

# SMTP server to transmit mail through.  Defaults to localhost.
smtp_server = "localhost"

# The e-mail address that search results are sent from.  There is no default
# for this so it has to be set in the config file.
origin_email_address = ""

# E-mail message containing search results.
message = ""

# Optional user-defined text strings for the online help and user interaction.
user_text = None
user_acknowledged = None

# Functions.
# set_loglevel(): Turn a string into a numerical value which Python's logging
#   module can use because.
def set_loglevel(loglevel):
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

# online_help(): Function that sends online help to the user when asked.
def online_help():
    reply = ""
    reply = "My name is " + globals.bot_name + " and I am an instance of " + sys.argv[0] + ".\n"
    reply = reply + "I am an interface to the Searx meta-search engine with a limited conversational user interface.\n\n"
    if user_text:
        reply = reply + user_text + "\n\n"
    reply = reply + "At this time I can accept search requests and optionally e-mail the results to a destination address.  To execute a search request, send me a message that looks like this:\n\n"
    reply = reply + globals.bot_name + ", (send/e-mail/email/mail) (me/<e-mail address>) top <number> hits for <search request...>\n\n"
    reply = reply + "By default, I will e-mail results to the address " + default_email + ".\n\n"
    reply = reply + "I can return search results directly to this instant messager session.  Send me a request that looks like this:\n\n"
    reply = reply + globals.bot_name + ", (get) top <number> hits for <search request...>\n\n"
    reply = reply + "I can list the search engines I know about:\n\n"
    reply = reply + globals.bot_name + ", (list (search)) engines\n\n"
    reply = reply + "I can run searches using specific search engines:\n\n"
    reply = reply + globals.bot_name + ", (get) top <number> hits for !shortcode <search request...>\n\n"
    reply = reply + "Yes, an exclamation point goes in front of the shortcode, and otherwise the "
    reply = reply + "search request is the same.\n\n"
    globals.send_message_to_user(globals.server, reply)
    return

# get_search_results(): Function that does the heavy lifting of contacting the
#   search engines, getting the results, and parsing them.  Takes one argument,
#   a string containing the search term.  Returns a list of search results.
def get_search_results(search_term):
    logger.debug("Entered function get_search_results().")

    # URL which represents the search request.
    url = ""

    # This will hold the search results returned by Searx.
    search_results = {}

    # The array which holds the search result data we actually want.
    results = []

    # Assemble the search request URL.
    url = searx + search_term
    logger.debug("Got a search request for " + str(url) + ".")

    # Make the search request and extract the JSON of the results.
    try:
        request = requests.get(url)
        search_results = json.loads(request.content)
    except:
        globals.send_message_to_user(globals.server, "Uh-oh. Searx returned HTTP status code %s." % (request.status_code))
        return None

    # Extract only the stuff we want from the search results and pack it into
    # a separate hash table.
    for i in search_results['results']:
        temp = {}
        temp['title'] = i['title']
        temp['url'] = i['url']
        temp['score'] = i['score']
        results.append(temp)

    # Truncate the master list of search results down to the number of
    # hits the user requested.
    if len(results) > number_of_results:
        results = results[:(number_of_results - 1)]
    logger.debug("Returning " + str(len(results)) + " search results.")

    # Return the list of search results.
    return results

# Core code...
# Set up the command line argument parser.
argparser = argparse.ArgumentParser(description="A bot that polls a message queue for search requests, parses them, runs them as web searches, and e-mails the results to a destination.")

# Set the default config file and the option to set a new one.
argparser.add_argument("--config", action="store",
    default="./web_search_bot.conf")

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument("--loglevel", action="store",
    help="Valid log levels: critical, error, warning, info, debug, notset.  Defaults to info.")

# Time (in seconds) between polling the message queues.
argparser.add_argument("--polling", action="store", help="Default: 10 seconds")

# Parse the command line arguments.
args = argparser.parse_args()
if args.config:
    config_file = args.config

# Read the options in the configuration file before processing overrides on the
# command line.
config = configparser.ConfigParser()
if not os.path.exists(config_file):
    logging.error("Unable to find or open configuration file " +
        config_file + ".")
    sys.exit(1)
config.read(config_file)

# Get the URL of the Searx instance to contact.
searx = config.get("DEFAULT", "searx")

# Get the URL of the message queue to contact.
globals.server = config.get("DEFAULT", "queue")

# Get the names of the message queues to report to.
globals.bot_name = config.get("DEFAULT", "bot_name")

# Construct the full message queue URL.
message_queue = globals.server + globals.bot_name

# Get the default e-mail address.
default_email = config.get("DEFAULT", "default_email")

# Get the default loglevel of the bot.
config_log = config.get("DEFAULT", "loglevel").lower()
if config_log:
    loglevel = set_loglevel(config_log)

# Set the number of seconds to wait in between polling runs on the message
# queues.
try:
    polling_time = config.get("DEFAULT", "polling_time")
except:
    # Nothing to do here, it's an optional configuration setting.
    pass

# Get the SMTP server to send search results through from the config file if
# it's been set.
try:
    smtp_server = config.get("DEFAULT", "smtp_server")
except:
    # Nothing to do here, it's an optional configuration setting.
    pass

# Get the e-mail address that search results will be sent from.
origin_email_address = config.get("DEFAULT", "origin_email_address")

# Get user-defined doing-stuff text if defined in the config file.
try:
    user_text = config.get("DEFAULT", "user_text")
except:
    # Nothing to do here, it's an optional configuration setting.
    pass

# Get additional user text if defined in the config file.
try:
    user_acknowledged = config.get("DEFAULT", "user_acknowledged")
except:
    # Nothing to do here, it's an optional configuration setting.
    pass

# Set the loglevel from the override on the command line.
if args.loglevel:
    loglevel = set_loglevel(args.loglevel.lower())

# Configure the logger.
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Set the message queue polling time from override on the command line.
if args.polling:
    polling_time = args.polling

# Debugging output, if required.
logger.info("Everything is set up.")
logger.debug("Values of configuration variables as of right now:")
logger.debug("Configuration file: " + config_file)
logger.debug("Searx instance: " + searx)
logger.debug("Server to report to: " + globals.server)
logger.debug("Message queue to report to: " + message_queue)
logger.debug("Bot name to respond to search requests with: " + globals.bot_name)
logger.debug("Default e-mail address to send results to: " + default_email)
logger.debug("Time in seconds for polling the message queue: " +
    str(polling_time))
logger.debug("SMTP server to send search results through: " + smtp_server)
logger.debug("E-mail address that search results are sent from: " +
    origin_email_address)
logger.debug("Number of search engines enabled: " + str(len(globals.search_engines)))
if user_text:
    logger.debug("User-defined help text: " + user_text)
if user_acknowledged:
    logger.debug("User-defined command acknowledgement text: " + user_acknowledged)

# Try to contact the XMPP bridge.  Keep trying until you reach it or the
# system shuts down.
logger.info("Trying to contact XMPP message bridge...")
while True:
    try:
        globals.send_message_to_user(globals.server, globals.bot_name + " now online.")
        break
    except:
        logger.warning("Unable to reach message bus.  Going to try again in %s seconds." % polling_time)
        time.sleep(float(polling_time))

# Query the Searx instance and get its list of enabled search engines.
while True:
    try:
        temp_searx = "/".join(searx.split('/')[0:-1]) + "/config"
        request = requests.get(temp_searx)
        globals.search_engines = request.json()["engines"]
        break
    except:
        globals.send_message_to_user(globals.server, "Unable to contact Searx instance! Tried to contact configuration URL %s." % str(temp_searx))
        time.sleep(float(polling_time))

# Remove all of the disabled search engines from the list.
for i in globals.search_engines:
    if not bool(i["enabled"]):
        globals.search_engines.remove(i)
logging.debug("Enabled search engines: %s" % str(globals.search_engines))

# Go into a loop in which the bot polls the configured message queue with each
# of its configured names to see if it has any search requests waiting for it.
globals.send_message_to_user(globals.server, "I now have my Searx search configuration.  Let's do this.")
logger.debug("Entering main loop to handle requests.")
while True:

    # Reset the destination e-mail address and the outbound message.
    destination_email_address = ""
    message = ""

    # Check the message queue for search requests.
    try:
        logger.debug("Contacting message queue: " + message_queue)
        request = requests.get(message_queue)
        logger.debug("Response from server: " + request.text)
    except:
        logger.warn("Connection attempt to message queue timed out or failed.  Going back to sleep to try again later.")
        time.sleep(float(polling_time))
        continue

    # Test the HTTP response code.
    # Success.
    if request.status_code == 200:
        logger.debug("Message queue " + globals.bot_name + " found.")

        # Extract the search request.
        search_request = json.loads(request.text)
        logger.debug("Value of search_request: " + str(search_request))
        search_request = search_request['command']
        if not search_request:
            reply = "That appears to be an empty search request."
            globals.send_message_to_user(globals.server, reply)
            time.sleep(float(polling_time))
            continue

        # Parse the search request.
        (number_of_results, search, destination_email_address) = parser.parse_search_request(search_request)
        logger.debug("Number of search results: " + str(number_of_results))
        logger.debug("Search request: " + str(search))
        if destination_email_address == "XMPP":
            logger.debug("Sending search results back via XMPP.")

        if destination_email_address == "default_email":
            destination_email_address = default_email
            logger.debug("Sending search results to the default e-mail address.")

        if destination_email_address:
            logger.debug("E-mail address to send search results to: " +
                str(destination_email_address))

        # Test to see if the user requested help.  If so, assemble a response,
        # send it back to the user, and restart the loop.
        if (str(number_of_results).lower() == "help"):
            online_help()
            continue

        # Test to see if the user requested a list of search engines.  If so,
        # assemble a response, send it back to the user, and restart the loop.
        if (str(number_of_results).lower() == "list"):
            reply = "These are the search engines I am configured to use:\n"
            reply = reply + "Shortcode\t\tSearch engine name\n"
            for i in globals.search_engines:
                reply = reply + "!" + i["shortcut"] + "\t\t" + i["name"].title() + "\n"
            globals.send_message_to_user(globals.server, reply)
            continue

        # If the number of search results is zero there was no search
        # request in the message queue, in which case we do nothing and
        # loop again.
        if (number_of_results == 0) and (len(search) == 0):
            search_request = ""
            time.sleep(float(polling_time))
            continue

        # Run the searches and get the results.
        if user_acknowledged:
            globals.send_message_to_user(globals.server, user_acknowledged)
        else:
            globals.send_message_to_user(globals.server, "Running web search.  Please stand by.")
        search_results = get_search_results(search)

        # Catch the case where Searx freaked out and returned something... I
        # don't know exactly what it returns if it throws a fatal exception,
        # but Web Search Bot sees an object of NoneType.
        if not search_results:
            message = "Searx freaked out and returned something I don't know how to parse.  "
            message = message + "I'm pretty sure that it threw an exception on its end, and "
            message = message + "probably crashed."
            globals.send_message_to_user(globals.server, message)
            time.sleep(float(polling_time))
            continue

        # If no search results were returned, put that message into the
        # (empty) list of search results.
        if len(search_results) == 0:
            temp = {}
            temp["title"] = "No search results found."
            temp["url"] = ""
            temp["score"] = 0.0
            search_results.append(temp)

        # Construct the message containing the search results.
        message = "Here are your search results:\n"
        for result in search_results:
            message = message + result["title"] + "\n"
            message = message + result["url"] + "\n"
            message = message + "Relevance: " + str(result["score"]) + "\n\n"
        message = message + "End of search results.\n"

        # If the response is supposed to go over XMPP, send it back and go
        # on with our lives.
        if destination_email_address == "XMPP":
            globals.send_message_to_user(globals.server, message)
            time.sleep(float(polling_time))
            continue

        # If the search results are to be e-mailed, complete the SMTP message.
        if destination_email_address == "":
            destination_email_address = default_email

        message = MIMEText(message, 'plain', 'utf-8')
        message['Subject'] = Header("Incoming search results!", 'utf-8')
        message['From'] = Header(origin_email_address, 'utf-8')
        message['To'] = Header(destination_email_address, 'utf-8')
        logger.debug("Created outbound e-mail message with search results.")
        logger.debug(str(message))

        # Set up the SMTP connection and transmit the message.
        logger.info("E-mailing search results to " + destination_email_address)
        smtp = smtplib.SMTP(smtp_server)
        smtp.sendmail(origin_email_address, destination_email_address,
            message.as_string())
        smtp.quit()
        globals.send_message_to_user(globals.server, "E-mailed search results to " + destination_email_address + ".")
        logger.info("Search results transmitted.  Deallocating SMTP server object.")

        # Deallocate resources we don't need now that the message is en route.
        smtp = ""
        destination_email_address = ""

    # Message queue not found.
    if request.status_code == 404:
        logger.info("Message queue " + globals.bot_name + " does not exist.")

    # Sleep for the configured amount of time.
    time.sleep(float(polling_time))

# Fin.
sys.exit(0)
