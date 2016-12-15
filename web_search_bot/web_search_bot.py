#!/usr/bin/env python2
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
# - Holy crap my command parser is bobbins.  I don't need a full NLP toolkit
#   just yet, though.
# - Add an error handler to parse_search_requests() that returns something to
#   the effect of "I don't know what you just said."
# - Break out the "handle HTTP result code" handler into a function.
# - Make it possible to send search results back through the /replies API rail
#   instead of e-mail.
# - Refactor repeated code into helper methods, ala my other bots.
# - Rework parse_search_request() because there's a corner case in which the
#   word 'get' could accidentally be used and interpreted after an "<email>
#   <foo>" command.  In other words, fat-fingering a command could mess things
#   up in indeterminant ways.

# Load modules.
from email.message import Message
from email.header import Header
from email.mime.text import MIMEText

import argparse
import ConfigParser
import json
import logging
import os
import re
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
custom_headers = {'Content-Type': 'application/json'}

# The precompiled regular expression for detecting e-mail addresses.
email_regex = "[^@]+@[^@]+\.[^@]+"
email_matcher = re.compile(email_regex)

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

# The name the search bot will respond to.  The idea is, this bot can be
# instantiated any number of times with different config files to use
# different search engines on different networks.
bot_name = ""

# How often to poll the message queues for orders.
polling_time = 0

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

# parse_search_request(): Takes a string and figures out what kind of search
#   request the user wants.  Requests are something along the form of "top ten
#   hits for foo" or "search Tor for bar".  Returns a set of URLs for search
#   engines and search terms.
def parse_search_request(search_request):
    logger.debug("Entered function parse_search_request().")
    number_of_search_results = 0
    search_term = ""
    email_address = ""
    words = []

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

    # Tokenize the search request.
    words = search_request.split()
    logger.debug("Tokenized search request: " + str(words))

    # User asked for help.
    if words[0].lower() == "help":
        return (words[0], None, None)

    # "send/e-mail/email/mail <foo> top <number> hits for <search request...>"
    if (words[0] == "send") or (words[0] == "e-mail") or \
            (words[0] == "email") or (words[0] == "mail"):
        logger.info("Got a token suggesting that search results should be e-mailed to someone.")

        # See if the next token is "me", which means use the default address.
        if words[1].lower() == "me":
            email_address = default_email
            del words[0]
            del words[0]
            break

        # See if the next token fits the general pattern of an e-mail address.
        # It doesn't need to be perfect, it just needs to vaguely fit the
        # pattern.
        if email_matcher.match(words[1]):
            email_address = words[1]
            del words[0]
            del words[0]
            logger.info("The e-mail address to send search results to: " +
                email_address)
        else:
            logger.warn("The e-mail address " + words[1] + " didn't match the general format of an SMTP address.  Using default e-mail address.")
            send_message_to_user("The e-mail address given didn't match.  Using the default e-mail address of " + default_email + ".")
            email_address = default_email
            del words[0]

    # "get top <number> hits for <search request...>"
    if (words[0] == "get"):
        logger.info("Got a token suggesting that search results should be sent over XMPP.")
        del words[0]
        email_address = "XMPP"

    # "top <foo> hits for <search request...>
    logger.debug("Figuring out how many results to return for the search request.")
    if words[0] == "top":
        if not words[1]:
            logger.error("Got a truncated search request.")
            send_message_to_user("Got a truncated search request - something weird happened.")
            return (number_of_search_results, search_term, email_address)

        if isinstance(words[1], (int)):
            number_of_search_results = words[1]

        if words[1] in numbers.keys():
            number_of_search_results = numbers[words[1]]
        else:
            # Return a default of 10 search results.
            number_of_search_results = 10
    del words[0]
    del words[1]

    # Remove words that make commands a little easier to phrase - "hits for"
    del words[0]
    del words[0]

    # If the parsed search term is now empty, return an error.
    if not len(words):
        logger.error("The search term appears to be empty: " + str(words))
        send_message_to_user("Your search term is prematurely terminated.  Something weird happened.")
        return (number_of_search_results, search_term, email_address)

    # Convert the remainder of the list into a URI-encoded string.
    search_term = "+".join(unicode(word) for word in words)
    logger.debug("Search term: " + search_term)
    return (number_of_search_results, search_term, email_address)

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
    headers = {'Content-type': 'application/json'}

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
argparser = argparse.ArgumentParser(description='A bot that polls a message queue for search requests, parses them, runs them as web searches, and e-mails the results to a destination.')

# Set the default config file and the option to set a new one.
argparser.add_argument('--config', action='store', 
    default='./web_search_bot.conf')

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument('--loglevel', action='store',
    help='Valid log levels: critical, error, warning, info, debug, notset.  Defaults to info.')

# Time (in seconds) between polling the message queues.
argparser.add_argument('--polling', action='store', default=60,
    help='Default: 60 seconds')

# Parse the command line arguments.
args = argparser.parse_args()
if args.config:
    config_file = args.config

# Read the options in the configuration file before processing overrides on the
# command line.
config = ConfigParser.ConfigParser()
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

        # Parse the search request.
        (number_of_results, search, destination_email_address) = parse_search_request(search_request)
        logger.debug("Number of search results: " + str(number_of_results))
        logger.debug("Search request: " + str(search))
        if destination_email_address == "XMPP":
            logger.debug("Sending search results back via XMPP.")

        # MOOF MOOF MOOF
        if destination_email_address != "":
            logger.debug("E-mail address to send search results to: " +
                str(destination_email_address))

        # Test to see if the user requested help.  If so, assemble a response,
        # send it back to the user, and restart the loop.
        if (str(number_of_results).lower() == "help"):
            reply = "My name is " + bot_name + " and I am an instance of " + sys.argv[0] + ".\n"
            reply = reply + "I am an interface to the Searx meta-search engine with very limited conversational capability.  At this time I can accept search requests and e-mail the results to a destination address.  To execute a search request, send me a message that looks like this:\n\n"
            reply = reply + bot_name + ", (send/e-mail/email/mail) <e-mail address> top <number> hits for <search request...>\n\n"
            reply = reply + "By default, I will e-mail results to the address " + default_email + ".\n\n"
            reply = reply + "I can also return search results directly to this instant messager session.  Send me a request that looks like this:\n\n"
            reply = reply + bot_name + ", get top <number> hits for <search request...>\n\n"
            send_message_to_user(reply)
            continue

        # If the number of search results is zero there was no search
        # request in the message queue, in which case we do nothing and
        # loop again later.
        if (number_of_results == 0) and (len(search) == 0):
            search_request = ""
            time.sleep(float(polling_time))
            continue

        # Run the web searches and get the results.
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

