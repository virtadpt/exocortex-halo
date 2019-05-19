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

# v5.2 - Reworked the startup logic so that being unable to immediately
#       connect to either the message bus or the intended service is a
#       terminal state.  Instead, it loops and sleeps until it connects and
#       alerts the user appropriately.
# v5.1 - Made it possible to optionally define additional user text to add to
#        the bot's online help.  My use case for this is when you run multiple
#        instances of this bot and you want to keep them all straight by
#        customizing their personae a bit.
#       - Made it possible to optionally define the "I'm doing stuff" text the
#       bot sends when it's executing commands.
#       - Changed the default polling time to 10 seconds, because this bot
#        won't be run on a Commodore 64...
#       - Broke online help out into a separate function.
#       - Updated the comments for the function declarations to match other
#         bots in the suite.
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
# - Pull the argument vector and config file parsing stuff into their own
#   functions to neaten up the core code.
# - Add an error handler to parse_search_requests() that returns something to
#   the effect of "I don't know what you just said."
# - Break out the "handle HTTP result code" handler into a function.
# - Break up the main loop into a few functions to make it easier to read.

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

# Constants.
# Hash table that maps numbers-as-words ("ten") into numbers (10).
numbers = { "one":1, "two":2, "three":3, "four":4, "five":5, "six":6,
    "seven":7, "eight":8, "nine":9, "ten":10, "eleven":11, "twelve":12,
    "thirteen":13, "fourteen":14, "fifteen":15, "sixteen":16, "seventeen":17,
    "eighteen":18, "nineteen":19, "twenty":20, "twenty-one":21, "twenty-two":22,
    "twenty-two":22, "twenty-three":23, "twenty-four":24, "twenty-five":25,
    "twenty-six":26, "twenty-seven":27, "twenty-eight":28, "twenty-nine":29,
    "thirty":30 , "thirty-one":31, "thirty-two":32, "thirty-three":33,
    "thirty-four":34, "thirty-five":35, "thirty-six":36, "thirty-seven":37,
    "thirty-eight":38, "thirty-nine":39, "forty":50, "forty-one":41,
    "forty-two":42, "forty-three":43, "forty-four":44, "forty-five":45,
    "forty-six":46, "forty-seven":47, "forty-eight":48, "forty-nine":49,
    "fifty":50 }

# When POSTing something to a service, the correct Content-Type value has to
# be set in the request.
custom_headers = {"Content-Type": "application/json"}

# Global variables.
# Base URL to a Searx instance.
searx = ""

# Handle to a logging object.
logger = ""

# Path to and name of the configuration file.
config_file = ""

# Loglevel for the bot.
loglevel = logging.INFO

# The "http://system:port/" part of the message queue URL.
server = ""

# URL to the message queue to take marching orders from.
message_queue = ""

# Default e-mail address to send search results to.
default_email = ""

# The name the search bot will respond to.  The idea is that this bot can be
# instantiated any number of times with different config files for different
# purposes.
bot_name = ""

# How often to poll the message queues for orders.
polling_time = 10

# List of search engines the configured Searx instance has enabled.
search_engines = []

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

# Parser primitives.
# We define them up here because they'll be re-used over and over.
help_command = pp.CaselessLiteral("help")
get_command = pp.Optional(pp.CaselessLiteral("get"))
top_command = pp.CaselessLiteral("top")
results_count = (pp.Word(pp.nums) |
                 pp.Word(pp.alphas + "-")).setResultsName("count")
hitsfor_command = pp.CaselessLiteral("hits for")
search_term = pp.Word(pp.alphanums + "_,'-")
search_terms = pp.OneOrMore(search_term)
send_command = (pp.CaselessLiteral("send") | pp.CaselessLiteral("e-mail") |
                pp.CaselessLiteral("email") | pp.CaselessLiteral("mail"))
me = pp.CaselessLiteral("me")
email = pp.Regex(r"(?P<user>[A-Za-z0-9._%+-]+)@(?P<hostname>[A-Za-z0-9.-]+)\.(?P<domain>[A-Za-z]{2,4})")
destination = pp.Optional(me) + pp.Optional(email).setResultsName("dest")

# search <engine or shortcut> (for) <search terms>
search_command = pp.CaselessLiteral("search")
shortcut_command = pp.Word(pp.alphanums).setResultsName("shortcode")
for_command = pp.Optional(pp.CaselessLiteral("for"))

# (list) (search) engines
list_command = pp.CaselessLiteral("list")
engines_command = pp.CaselessLiteral("engines")

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
    reply = "My name is " + bot_name + " and I am an instance of " + sys.argv[0] + ".\n\n"
    reply = reply + "I am an interface to the Searx meta-search engine with a limited conversational user interface.\n\n"
    if user_text:
        reply = reply + user_text + "\n\n"
    reply = reply + "At this time I can accept search requests and optionally e-mail the results to a destination address.  To execute a search request, send me a message that looks like this:\n\n"
    reply = reply + bot_name + ", (send/e-mail/email/mail) (me/<e-mail address>) top <number> hits for <search request...>\n\n"
    reply = reply + "By default, I will e-mail results to the address " + default_email + ".\n\n"
    reply = reply + "I can return search results directly to this instant messager session.  Send me a request that looks like this:\n\n"
    reply = reply + bot_name + ", (get) top <number> hits for <search request...>\n\n"
    reply = reply + "I can list the search engines I'm configured to contact:\n\n"
    reply = reply + bot_name + ", (list (search)) engines\n\n"
    reply = reply + "I can run searches using specific search engines I'm configured for:\n\n"
    reply = reply + bot_name + ", search <search engine shortcode> for <search request...>\n\n"
    send_message_to_user(reply)
    return

# make_search_term(): Function that takes a string of the form "foo bar baz"
#   and turns it into a URL encoded string "foo+bar+baz", which is then
#   returned to the calling method.
def make_search_term(search_terms):
    return "+".join(term for term in search_terms)

# word_and_number(): Function that takes a number represented as a word
#   ("twenty") or a number ("20") and turns it into a number (20) if it's the
#   former.  Returns an integer.
def word_and_number(value):
    # Numbers as actual digits are stored inside the parser as strings.
    # This fucks with us.  So, detect if they're digits, and if so turn
    # them back into integers.
    if value.isdigit():
        return int(value)

    # If the number of search results is a word ("twenty"), look it up in
    # the global hash table numbers{} and use the corresponding numerical
    # value as the number of search results to pick up.
    if value in list(numbers.keys()):
        return numbers[value]
    else:
        # Set a default number of search terms.
        return 10

# parse_help(): Function that matches the word "help" all by itself in an
#   input string.  Returns "help" for the number of search terms, None for the
#   search string, and None for the destination e-mail.
def parse_help(request):
    try:
        parsed_command = help_command.parseString(request)
        return ("help", None, None)
    except pp.ParseException as x:
        logger.info("No match: {0}".format(str(x)))
        return (None, None, None)

# parse_list(): Function that matches whenever it encounters the phrase
#   "(list) (search) engines" in an input string.  Returns "list" for the
#   number of search terms, one for the search string, and None for the
#   destination e-mail.
def parse_list(request):
    # Build the parser out of predeclared primitives.
    command = pp.Optional(list_command) + pp.Optional(search_command)
    command = command + engines_command

    try:
        parsed_command = command.parseString(request)
        return("list", None, None)
    except pp.ParseException as x:
        logger.info("No match: {0}".format(str(x)))
        return (None, None, None)

# parse_get_request(): Function that matches on commands of the form "get top
#   <foo> hits for <bar>" in an input string.  Returns an integer number of
#   search results (up to 50), a URL encoded search string, and the e-mail
#   address "XMPP", meaning that the results will be sent to the user via the
#   XMPP bridge.
def parse_get_request(request):
    # Build the parser out of predeclared primitives.
    command = get_command + top_command + results_count + hitsfor_command
    command = command + pp.Group(search_terms).setResultsName("searchterms")

    number_of_search_results = 0

    # Try to parse the command.
    try:
        parsed_command = command.parseString(request)
        number_of_search_results = word_and_number(parsed_command["count"])

        # Grab the search term.
        search_term = make_search_term(parsed_command["searchterms"])

        return (number_of_search_results, search_term, "XMPP")
    except pp.ParseException as x:
        logger.info("No match: {0}".format(str(x)))
        return (None, None, None)

# parse_and_email_results(): Function that matches on commands of the form
#   "send/e-mail/email/mail top <foo> hits for <search terms>".  Returns an
#   integer number of search results (up to 50), a URL encoded search string,
#   and an e-mail address.
def parse_and_email_results(request):
    # Build the parser out of predeclared primitives.
    command = send_command + destination + top_command + results_count
    command = command + hitsfor_command
    command = command + pp.Group(search_terms).setResultsName("searchterms")

    number_of_search_results = 0
    destination_address = ""

    try:
        parsed_command = command.parseString(request)
        number_of_search_results = word_and_number(parsed_command["count"])

        # Grab the search term.
        search_term = make_search_term(parsed_command["searchterms"])

        # Figure out which e-mail address to use - the default or the supplied
        # one.  On error, use the default address.
        if "dest" in list(parsed_command.keys()):
            destination_address = parsed_command["dest"]
        else:
            destination_address = default_email
        return (number_of_search_results, search_term, destination_address)
    except pp.ParseException as x:
        logger.info("No match: {0}".format(str(x)))
        return (None, None, None)

# parse_specific_search(): Function that matches on commands of the form
#   "search <shortcode> for <search terms>".  Returns a default number of
#   search results (10) until I can make the parser more sophisticated, a URL
#   encoded search string which includes the shortcode for the search engine
#   ("!foo"), and "XMPP", because this is really only useful for mobile
#   requests.
def parse_specific_search(request):
    # Build the parser out of predeclared primitives.
    command = search_command + shortcut_command + for_command
    command = command + pp.Group(search_terms).setResultsName("searchterms")

    number_of_search_results = 10
    engine = ""
    searchterms = []

    try:
        parsed_command = command.parseString(request)
        engine = parsed_command["shortcode"]
        searchterms = parsed_command["searchterms"]

        # Check to see if the search engine is enabled.  We do this in a
        # circuitous fashion because we want either the shortcode or a failure,
        # while at the same time making it possible for the user to use the
        # name of the search engine.
        engine = is_enabled_engine(engine)
        if not engine:
            return(0, "", "")

        # Create a search term that includes the shortcode for the search
        # engine.
        searchterms.insert(0, engine)
        searchterms = make_search_term(searchterms)

    except pp.ParseException as x:
        logger.info("No match: {0}".format(str(x)))
        return (None, None, None)

    return (number_of_search_results, searchterms, "XMPP")

# is_enabled_engine(): Utility function that scans the list of enabled search
#   engines and returns the shortcode for the search engine ("!foo") or None.
def is_enabled_engine(engine):
    # Test to see if the shortcode given (which could be either the name of the
    # search engine or the actual shortcode) are in the list.  We append a bang
    # (!) to the shortcode so that Searx knows to use it as a specific search.
    for i in search_engines:
        if i["name"] == engine.lower():
            logger.debug("Search engine " + str(engine) + " enabled.")
            return "!" + i["shortcut"]
        if i["shortcut"] == engine.lower():
            logger.debug("Search engine " + str(engine) + " enabled.")
            return "!" + i["shortcut"]
    return None

# parse_search_request(): Takes a string and figures out what kind of search
#   request the user wants.  Requests are something along the form of "top ten
#   hits for foo" or "search Tor for bar".  Returns the number of results to
#   send the user, the URI for the search terms, and the address to send the
#   results to ("XMPP" if it's supposed to go back to the user via the XMPP
#   bridge.
def parse_search_request(search_request):
    logger.debug("Entered function parse_search_request().")
    number_of_search_results = 0
    search_term = ""
    email_address = ""
    engine = ""

    # Clean up the search request.
    search_request = search_request.strip()
    search_request = search_request.strip(",")
    search_request = search_request.strip(".")
    search_request = search_request.strip("'")
    search_request = search_request.lower()

    # If the search request is empty (i.e., nothing in the queue) return 0 and
    # "".
    if "no commands" in search_request:
        logger.debug("Got empty search request.")
        return (number_of_search_results, search_term, email_address)

    # Attempt to parse a request for online help.
    (number_of_search_results, search_term, email_address) = parse_help(search_request)
    if number_of_search_results == "help":
        logger.info("The user is asking for online help.")
        return ("help", None, None)

    # Attempt to parse a "list search engines" request.
    (number_of_search_results, search_term, email_address) = parse_list(search_request)
    if number_of_search_results == "list":
        logger.info("The user has requested a list of search engines.")
        return ("list", None, None)

    # Attempt to parse a "get" request.
    (number_of_search_results, search_term, email_address) = parse_get_request(search_request)
    if number_of_search_results and (email_address == "XMPP"):
        logger.info("The user has sent the search term " + str(search_term))
        return (number_of_search_results, search_term, "XMPP")

    # Attempt to parse an "email results" request.
    (number_of_search_results, search_term, email_address) = parse_and_email_results(search_request)
    if number_of_search_results and ("@" in email_address):
        logger.info("The user has requested that search results for " + str(search_term) + " be e-mailed to " + email_address + ".")
        return (number_of_search_results, search_term, email_address)

    # Attempt to parse a search for a specific engine.  If it works, prepend
    # the string "!<search shortcode>" so that Searx knows to search on one
    # search engine only.
    (number_of_search_results, search_term, email_address) = parse_specific_search(search_request)
    if number_of_search_results and (email_address == "XMPP"):
        logger.info("The user has requested a specific search: " + str(search_term))
        return (number_of_search_results, search_term, "XMPP")

    # Fall-through - this should happen only if nothing at all matches.
    logger.info("Fell all the way through in parse_search_request().  Telling the user I didn't understand what they said.")
    send_message_to_user("I didn't understand your command.  Try again, please.")
    return (0, "", None)

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
    request = requests.get(url)
    search_results = json.loads(request.content)

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

# send_message_to_user(): Function that does the work of sending messages back
# to the user by way of the XMPP bridge.  Takes one argument, the message to
#   send to the user.  Returns a True or False which delineates whether or not
#   it worked.
def send_message_to_user(message):
    logger.debug("Entered function send_message_to_user().")

    # Headers the XMPP bridge looks for for the message to be valid.
    headers = {"Content-type": "application/json"}

    # Set up a hash table of stuff that is used to build the HTTP request to
    # the XMPP bridge.
    reply = {}
    reply['name'] = bot_name
    reply['reply'] = message

    # Send an HTTP request to the XMPP bridge containing the message for the
    # user.
    request = requests.put(server + "replies", headers=headers,
        data=json.dumps(reply))

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
server = config.get("DEFAULT", "queue")

# Get the names of the message queues to report to.
bot_name = config.get("DEFAULT", "bot_name")

# Construct the full message queue URL.
message_queue = server + bot_name

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
logger.debug("Server to report to: " + server)
logger.debug("Message queue to report to: " + message_queue)
logger.debug("Bot name to respond to search requests with: " + bot_name)
logger.debug("Default e-mail address to send results to: " + default_email)
logger.debug("Time in seconds for polling the message queue: " +
    str(polling_time))
logger.debug("SMTP server to send search results through: " + smtp_server)
logger.debug("E-mail address that search results are sent from: " +
    origin_email_address)
logger.debug("Number of search engines enabled: " + str(len(search_engines)))
if user_text:
    logger.debug("User-defined help text: " + user_text)
if user_acknowledged:
    logger.debug("User-defined command acknowledgement text: " + user_acknowledged)

# Try to contact the XMPP bridge.  Keep trying until you reach it or the
# system shuts down.
logger.info("Trying to contact XMPP message bridge...")
while True:
    try:
        send_message_to_user(bot_name + " now online.")
        break
    except:
        logger.warning("Unable to reach message bus.  Going to try again in %s seconds." % polling_time)
        time.sleep(float(polling_time))

# Query the Searx instance and get its list of enabled search engines.  I don't
# particularly like this kind of jiggery-pokery but I also have the JSON API
# URI in the default configuration file to make life easier for people.  This
# is probably the least bad of all possible worlds.
while True:
    try:
        temp_searx = "/".join(searx.split('/')[0:-1]) + "/config"
        request = requests.get(temp_searx)
        search_engines = request.json()["engines"]
        break
    except:
        send_message_to_user("Unable to contact Searx instance! Tried to contact configuration URL %s." % str(temp_searx))
        time.sleep(float(polling_time))

# Remove all of the disabled search engines from the list.
for i in search_engines:
    if not bool(i["enabled"]):
        search_engines.remove(i)

# Go into a loop in which the bot polls the configured message queue with each
# of its configured names to see if it has any search requests waiting for it.
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
        logger.debug("Message queue " + bot_name + " found.")

        # Extract the search request.
        search_request = json.loads(request.text)
        logger.debug("Value of search_request: " + str(search_request))
        search_request = search_request['command']
        if not search_request:
            reply = "That appears to be an empty search request."
            send_message_to_user(reply)
            time.sleep(float(polling_time))
            continue

        # Parse the search request.
        (number_of_results, search, destination_email_address) = parse_search_request(search_request)
        logger.debug("Number of search results: " + str(number_of_results))
        logger.debug("Search request: " + str(search))
        if destination_email_address == "XMPP":
            logger.debug("Sending search results back via XMPP.")

        # MOOF MOOF MOOF
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
            for i in search_engines:
                reply = reply + i["shortcut"] + "\t\t" + i["name"].title() + "\n"
            send_message_to_user(reply)
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
            send_message_to_user(user_acknowledged)
        else:
            send_message_to_user("Running web search.  Please stand by.")
        search_results = get_search_results(search)

        # If no search results were returned, put that message into the
        # (empty) list of search results.
        if len(search_results) == 0:
            temp = {}
            temp['title'] = "No search results found."
            temp['url'] = ""
            temp['score'] = 0.0
            search_results.append(temp)

        # Construct the message containing the search results.
        message = "Here are your search results:\n"
        for result in search_results:
            message = message + result['title'] + "\n"
            message = message + result['url'] + "\n"
            message = message + "Relevance: " + str(result['score']) + "\n\n"
        message = message + "End of search results.\n"

        # If the response is supposed to go over XMPP, send it back and go
        # on with our lives.
        if destination_email_address == "XMPP":
            send_message_to_user(message)
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
        send_message_to_user("E-mailed search results to " + destination_email_address + ".")
        logger.info("Search results transmitted.  Deallocating SMTP server object.")

        # Deallocate resources we don't need now that the message is en route.
        smtp = ""
        destination_email_address = ""

    # Message queue not found.
    if request.status_code == 404:
        logger.info("Message queue " + bot_name + " does not exist.")

    # Sleep for the configured amount of time.
    time.sleep(float(polling_time))

# Fin.
sys.exit(0)
