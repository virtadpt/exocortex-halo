#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# web_search_bot.py - Bot written in Python that polls a RESTful message queue
#   for search commands of the form "<botname>, get me <number of hits> hits
#   for <search terms>", runs the searches on a number of search engines,
#   collates them, and POSTs them to a Huginn
#   (https://github.com/cantino/huginn) instances webhook so something can be
#   done with them.
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

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

# Load modules.
from bs4 import BeautifulSoup
from bs4 import SoupStrainer
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
numbers = {"zero":0, "one":1, "two":2, "three":3, "four":4, "five":5, "six":6,
    "seven":7, "eight":8, "nine":9, "ten":10, "eleven":11, "twelve":12,
    "thirteen":13, "fourteen":14, "fifteen":15, "sixteen":16, "seventeen":17,
    "eighteen":18, "nineteen":19, "twenty":20, "twenty-one":21, "twenty-two":22,
    "twenty-two":22, "twenty-three":23, "twenty-four":24, "twenty-five":25,
    "twenty-six":26, "twenty-seven":27, "twenty-eight":28, "twenty-nine":29,
    "thirty":30}

# Every HTML page returned from a search engine will have two kinds of links:
# Links to search results, and links to other stuff we don't care about.  This
# is a list of the stuff we don't care about.
hyperlinks_we_dont_want = []

# When POSTing something to a service, the correct Content-Type value has to
# be set in the request.
custom_headers = {'Content-Type': 'application/json'}

# The precompiled regular expression for detecting e-mail addresses.
email_regex = "[^@]+@[^@]+\.[^@]+"
email_matcher = re.compile(email_regex)

# Global variables.
# Handle to a logging object.
logger = ""

# Path to and name of the configuration file.
config_file = ""

# Loglevel for the bot.
loglevel = logging.INFO

# URL to the message queue to take marching orders from.
message_queue = ""

# Because this bot will have two possible modes, clearnet and darknet, it will
# report to two different message queues, one for each name.  At the very least,
# it needs a clearnet name but variables for both will be declared.
clearnet_name = ""
darknet_name = ""

# The webhook service the bot reports search results to requires an API key to
# authenticate with.
api_key = ""

# URL of the webhook service to send search results to.
webhook = ""

# How often to poll the message queues for orders.
polling_time = 60

# This variable will hold a manually supplied search request.  It's here for
# the purposes of debugging, in case you don't have a message queue handy.
search_request = ""

# The list of search engines to run search requests against.
search_engines = []

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

    # "Send <foo> top <number> hits for <search request...>"
    if words[0] == "send":
        logger.info("Got a token suggesting that search results should be e-mailed to someone.")
        # See if the next token fits the general pattern of an e-mail address.
        # It doesn't need to be perfect, it just needs to vaguely fit the
        # pattern.
        if email_matcher.match(words[1]):
            email_address = words[1]
            del words[1]
        else:
            logger.warn("The e-mail address " + words[1] + " didn't match the general format of an SMTP address.  Aborting.")
            return (number_of_search_results, search_term, email_address)
        words.remove('send')
        logger.info("The e-mail address to send search results to: " +
            email_address)

    # Start parsing the the search request to see what kind it is.  After
    # making the determination, remove the words we've sussed out to make the
    # rest of the query easier.
    # "top <foo> hits for <search request...>
    logger.debug("Starting to parse search request.")
    if words[0] == "top":
        if words[1] in numbers.keys():
            number_of_search_results = numbers[words[1]]
            del words[1]
        else:
            # Return a default of 10 search results.
            number_of_search_results = 10
    words.remove('top')

    # If the number of search results to return is zero, set it to ten.
    if number_of_search_results == 0:
        number_of_search_results = 10

    # Remove words that make commands a little easier to phrase.
    if "hits" in words:
        words.remove("hits")
    if "for" in words:
        words.remove("for")

    # If the search term is empty, return an error.
    if not len(words):
        logger.error("The search term appears to be empty: " + str(words))
        return (number_of_search_results, search_term, email_address)

    # Convert the remainder of the list into a URI-encoded string.
    search_term = " ".join(str(word) for word in words)
    search_term = search_term.replace(' ', '+')
    logger.debug("Search term: " + search_term)
    return (number_of_search_results, search_term, email_address)

# get_search_results(): Function that does the heavy lifting of contacting the
#   search engines, getting the results, and parsing them.  Takes one argument,
#   a string containing the search term.  Returns a list of search results.
def get_search_results(search_term):
    logger.debug("Entered function get_search_results().")

    # This list will hold all of the links to search results.
    search_results = []

    # Allocate a link extractor.  This optimizes both memory utilization and
    # parsing speed of each page.
    link_extractor = SoupStrainer('a')

    # Make the search request using each of the search engines in the
    # configuration file.
    logger.info("Got request to search for " + search_term + ".  Starting search now.")
    for search_engine in search_engines:
        logger.debug("Placing search request to: " + search_engine)
        html_page = ""
        results = ""
        hyperlinks = []

        # Place the search request.
        search_URL = search_engine + search
        logger.debug("Search request: " + search_URL)
        request = requests.get(search_URL)
        html_page = request.content

        # Feed the appropriate document to the parser to extract all
        # of the hyperlinks.
        logger.debug("Parsing the HTML page returned from the search engine.")
        if html_page:
            results = BeautifulSoup(html_page, 'html.parser',
            parse_only=link_extractor)
        else:
            logger.warning("The search engine returned an error.")

        # Extract all of the hyperlinks from this page.
        logger.debug("Extracting hyperlinks from search result page.")
        for link in results.find_all('a'):
            hyperlink = link.get('href')

            # Sometimes hyperlinks are null.  Catch those.
            if not hyperlink:
                logger.debug("Found and skipping a Null hyperlink.")
                continue

            # Sift out the links we don't want.
            reject_link = False
            for do_not_want in hyperlinks_we_dont_want:
                if do_not_want in hyperlink:
                    reject_link = True
                    break

            # Clean up and keep the links we do want.
            if not reject_link:
                hyperlink = hyperlink.strip()
                hyperlinks.append(hyperlink)

            # Add the results from this search engine to the master list
            # of search results.
            search_results = search_results + hyperlinks

    # Deduplicate search results in the master list.
    logger.debug("Deduplicating and sorting the master list of search results.")
    search_results = list(set(search_results))
    search_results.sort()
    logger.debug("Master list of search results: " + str(search_results))

    # Truncate the master list of search results down to the number of
    # hits the user requested.
    if len(search_results) > number_of_results:
        search_results = search_results[:(number_of_results - 1)]
    logger.debug("Returning " + str(len(search_results)) + " search results.")
    logger.debug("Final list of search results: " + str(search_results))

    # Return the list of search results.
    return search_results

# Core code...

# Set up the command line argument parser.
argparser = argparse.ArgumentParser(description='A bot that polls one or more message queues for commands, parses them, runs web searches in response, and sends the results to a destination.')

# Set the default config file and the option to set a new one.
argparser.add_argument('--config', action='store', 
    default='./web_search_bot.conf')

# Loglevels: critical, error, warning, info, debug, notset.
argparser.add_argument('--loglevel', action='store',
    help='Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.')

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

# Get the message queue to contact.
message_queue = config.get("DEFAULT", "queue")

# Read in the list of hyperlinks to ignore when parsing HTML from the search
# engine results.
# This is a string.
hyperlinks_to_strip = config.get("DEFAULT", "hyperlinks_we_dont_want")
for hyperlink in hyperlinks_to_strip.split(','):
    hyperlink = hyperlink.strip()
    hyperlink = hyperlink.strip('"')
    hyperlinks_we_dont_want.append(hyperlink)

# Get the names of the message queues to report to.
clearnet_name = config.get("DEFAULT", "clearnet_name")
try:
    darknet_name = config.get("DEFAULT", "darknet_name")
except:
    # Nothing to do here, it's an optional configuration setting.
    pass

# Get the API key used to authenticate to the webhook service.
api_key = config.get("DEFAULT", "api_key")

# Get the URL of the webhook to report to.
webhook = config.get("DEFAULT", "webhook")

# Build the webhook URL to hit.
webhook = webhook + api_key

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

# Get the search engines from the config file and load them into a list.
engines = config.items("search engines")
for config_option, option in engines:
    if 'engine' in config_option:
        search_engines.append(option)

# Debugging output, if required.
logger.info("Everything is set up now.")
logger.debug("Values of configuration variables as of right now:")
logger.debug("Configuration file: " + config_file)
logger.debug("Message queue to report to: " + message_queue)
logger.debug("Hyperlinks to filter out of returned HTML: " + 
    str(hyperlinks_we_dont_want))
logger.debug("Bot name to respond to clearnet requests with: " + clearnet_name)
if darknet_name:
    logger.debug("Bot name to respond to Tor network requests with: " +
        darknet_name)
else:
    logger.debug("Bot will not search the Tor network.")
logger.debug("API key to use with the webhook: " + api_key)
logger.debug("URL of the webhook: " + webhook)
logger.debug("Time in seconds for polling the message queue: " +
    str(polling_time))
logger.debug("SMTP server to send search results through: " + smtp_server)
logger.debug("E-mail address that search results are sent from: " +
    origin_email_address)
logger.debug("Search term manually passed to the bot: " + search_request)
logging.debug("Search engines that will be queried: " + str(search_engines))

# Allocate a link extractor.  This optimizes both memory utilization and
# parsing speed of each page.
link_extractor = SoupStrainer('a')

# Go into a loop in which the bot polls the configured message queue with each
# of its configured names to see if it has any search requests waiting for it.
logger.debug("Entering main loop to handle requests.")
while True:
    for name in (clearnet_name, darknet_name):
        # If darknet searching is not enabled, skip the empty value.
        if name == "":
            break

        # Reset the destination e-mail address and the outbound message.
        destination_email_address = ""
        message = ""

        # Check the message queue for search requests.
        try:
            logger.debug("Contacting message queue: " + str(message_queue + name))
            request = requests.get(message_queue + name)
            logger.debug("Response from server: " + request.text)
        except:
            logger.warn("Connection attempt to message queue timed out or failed.  Going back to sleep to try again later.")
            time.sleep(float(polling_time))
            continue

        # Test the HTTP response code.
        # Success.
        if request.status_code == 200:
            logger.debug("Message queue " + name + " found.")

            # Extract the search request.
            search_request = json.loads(request.text)
            logger.debug("Value of search_request: " + str(search_request))
            search_request = search_request['command']

            # Parse the search request.
            (number_of_results, search, destination_email_address) = parse_search_request(search_request)
            logger.debug("Number of search results: " + str(number_of_results))
            logger.debug("Search request: " + search)
            if destination_email_address != "":
                logger.debug("E-mail address to send search results to: " +
                    destination_email_address)

            # If the number of search results is zero, there was no search
            # request in the message queue, in which case we do nothing and
            # loop again later.
            if (number_of_results == 0) and (len(search) == 0):
                search_request = ""
                time.sleep(float(polling_time))
                continue

            # Run the web searches and get the results.
            search_results = get_search_results(search)

            # Deduplicate search results in the master list.
            logger.debug("Deduplicating and sorting the master list of search results.")
            search_results = list(set(search_results))
            logger.debug("Master list of search results: " + str(search_results))

            # Truncate the master list of search results down to the number of
            # hits the user requested.
            if len(search_results) > number_of_results:
                search_results = search_results[:(number_of_results - 1)]
            logger.debug("Returning " + str(len(search_results)) + " search results.")
            logger.debug("Final list of search results: " + str(json.dumps(search_results)))

            # If no search results were returned, put that message into the
            # (empty) list of search results.
            if len(search_results) == 0:
                search_results = ["No search results found."]

            # If the search results are to be e-mailed, transmit them and then
            # bounce to the next iteration of the loop.
            if destination_email_address:
                # Construct the message containing the search results.
                message = "Here are your search results:\n"
                message = message + "\n"
                for url in search_results:
                    message = message + url + "\n"
                message = message + "\nEnd of search results"
                message = MIMEText(message)
                message['Subject'] = "Incoming search results!"
                message['From'] = origin_email_address
                message['To'] = destination_email_address
                logger.debug("Created outbound e-mail message with search results.")
                logger.debug(str(message))

                # Set up the SMTP connection and transmit the message.
                logger.info("E-mailing search results to " +
                    destination_email_address)
                smtp = smtplib.SMTP(smtp_server)
                smtp.sendmail(origin_email_address, destination_email_address,
                    message.as_string())
                smtp.quit()
                logger.info("Search results transmitted.  Deallocating SMTP server object.")
                smtp = ""

                # Go back to sleep and then loop again.
                time.sleep(float(polling_time))
                break

            # Post the results to the webhook agent.
            results = {'results': search_results}
            request = requests.post(webhook, data=json.dumps(results),
                headers=custom_headers)

            # Figure out what happened with the HTTP request.
            if request.status_code == 200:
                logger.info("Successfully POSTed search results to webhook.")
            if request.status_code == 400:
                logger.info("HTTP error 400 - bad request made.")
            if request.status_code == 404:
                logger.info("HTTP error 404 - webhook not found.")

        # Message queue not found.
        if request.status_code == 404:
            logger.info("Message queue " + name + " does not exist.")

    # Sleep for the configured amount of time.
    time.sleep(float(polling_time))

# Fin.

