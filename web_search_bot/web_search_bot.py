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

# v1.0 - Initial release.

# TO-DO:
# - Pull the argument vector and config file parsing stuff into their own
#   functions to neaten up the core code.
# - Holy crap my command parser is bobbins.  I don't need a full NLP toolkit
#   just yet, though.
# - Add the "send <e-mail address> top <number> hits for <foo>" bit.
# - Add a function where the bot can semi-permanently remember an alias for an
#   e-mail address ("remember <e-mail address> as <name>").  Forget them, too.
#   For that matter, internally substitute <e-mail address> for <name> before
#   e-mailing the results.
# - Add an error handler to parse_search_requests() that returns something to
#   the effect of "I don't know what you just said."
# - Move hyperlinks_we_dont_want[] into the config file, and read it in on
#   startup.  This'll make it easier to manage.

# Load modules.
from bs4 import BeautifulSoup
from bs4 import SoupStrainer

import argparse
import ConfigParser
import logging
import os
import requests
import sys
import time

# Constants.
# Hash table that maps numbers-as-words ("ten") into numbers (10).
numbers = {"zero":0, "one":1, "two":2, "three":3, "four":4, "five":5, "six":6,
    "seven":7, "eight":8, "nine":9, "ten":10, "eleven":11, "twelve":12,
    "thirteen":13, "fourteen":14, "fifteen":15, "sixteen":16, "seventeen":17,
    "eighteen":18, "nineteen":19, "twenty":20}

# Every HTML page returned from a search engine will have two kinds of links:
# Links to search results, and links to other stuff we don't care about.  This
# is the stuff we don't care about.
hyperlinks_we_dont_want = ["javascript:", "https://ixquick-proxy.com/do",
    "startpage.com", "startpagesearch", "#", "startmail.com", "ixquick",
    "yacy.net", "yacy.de", ".html", "yacysearch", "/solr/", "/gsa/",
    "github.com/yacy/yacy_search_server/", "opensearch.org", "www.google.com"]

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
polling_time = 0

# This variable will hold a manually supplied search request.  It's here for
# the purposes of debugging, in case you don't have a message queue handy.
search_request = ""

# The list of search engines to run search requests against.
search_engines = []

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
    number_of_search_results = 0
    search_term = ""

    # Clean up the search request.
    search_request = search_request.strip()
    search_request = search_request.strip(",")
    search_request = search_request.strip(".")
    search_request = search_request.strip("'")
    search_request = search_request.lower()
    logger.debug("Cleaned up search request: " + search_request)

    # Tokenize the search request.
    words = search_request.split()
    logger.debug("Tokenized search request: " + str(words))

    # MOOF MOOF MOOF - "Send <foo> top <number> hits for <search request...>"

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
        return (None, None)

    # Convert the remainder of the list into a URI-encoded string.
    search_term = " ".join(str(word) for word in words)
    search_term = search_term.replace(' ', '+')
    logger.debug("Search term: " + search_term)
    return (number_of_search_results, search_term)

# get_search_results(): Function that does the heavy lifting of contacting the
#   search engines, getting the results, and parsing them.  Takes one argument,
#   a string containing the search term.  Returns an array of search results.
def get_search_results(search_term):
    # This list will hold all of the links to search results.
    search_results = []

    # Allocate a link extractor.  This optimizes both memory utilization and
    # parsing speed of each page.
    link_extractor = SoupStrainer('a')

    # Make the search request using each of the search engines in the
    # configuration file.
    for search_engine in search_engines:
        logger.debug("Placing search request to: " + search_engine)
        html_page = ""
        results = ""
        hyperlinks = []

        # Place the search request.
        search_URL = search_engine + search
        logger.debug("Search request: " + search_URL)
        logger.debug("Value of search_URL: " + search_URL)
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

            # Keep the links we do want.
            if not reject_link:
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

# Add a debugging option which lets you manually inject a search request into
# the bot.
argparser.add_argument('--search', action='store', dest='search_request',
    help="An optional command line argument which allows you to pass a search request to the bot of the form 'top ten hits for foo'.")

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

# Pull the manual search request from the argument vector if it exists.
if args.search_request:
    search_request = args.search_request

# Debugging output, if required.
logger.info("Everything is set up now.")
logger.debug("Values of configuration variables as of right now:")
logger.debug("Configuration file: " + config_file)
logger.debug("Message queue to report to: " + message_queue)
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
logger.debug("Search term manually passed to the bot: " + search_request)
logging.debug("Search engines that will be queried: " + str(search_engines))

# Allocate a link extractor.  This optimizes both memory utilization and
# parsing speed of each page.
link_extractor = SoupStrainer('a')

# Go into a loop in which the bot polls the configured message queue with each
# of its configured names to see if it has any search requests waiting for it.
while True:
    for name in (clearnet_name, darknet_name):
        # Process a manually passed search term first.
        if search_request:
            # The number of search results and search term from the user.
            number_of_results = 0
            search = ""

            # This list will hold all of the links to search results.
            search_results = []

            # Parse the search request.
            (number_of_results, search) = parse_search_request(search_request)
            logger.debug("Number of search results: " + str(number_of_results))
            logger.debug("Search request: " + search)

            # Run the required web searches and get the results.
            search_results = get_search_results(search)

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

            # This code path exists solely for the purposes of debugging, so
            # there is no sense in keeping the bot running.
            sys.exit(2)

        # Check the message queue for search requests.
        request = requests.get(message_queue + name)

        # Test the HTTP response code.
        # Success.
        if request.status_code == 200:
            logger.debug("Message queue " + name + " found.")

            # Parse the search request.
            (number_of_results, search) = parse_search_request(search_request)
            logger.debug("Number of search results: " + str(number_of_results))
            logger.debug("Search request: " + search)

            # Run the required web searches and get the results.
            search_results = get_search_results(search)

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

            # MOOF MOOF MOOF - Hit the webhook and send the search results to
            # Huginn.

        # Bad HTTP request.
        if request.status_code == 400:
            logger.info("HTTP error 400 - bad request made.")

        # Message queue not found.
        if request.status_code == 404:
            logger.info("Message queue " + name + " does not exist.  No requests have come in yet for this agent.")

    # Sleep for the configured amount of time.
    time.sleep(float(polling_time))

# Fin.
sys.exit(0)

