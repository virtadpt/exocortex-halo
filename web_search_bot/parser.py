#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# parser.py - Split the command parsing stuff of Web Search Bot out into this
#   file.
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# - Come up with a better way of passing data around.  Tuples are nice, but I
#   can do so much better.
# - .setResultsName() can and probably should be used at the very top when
#   the parsing primitives are set up.
# - There are some top-level search requests (like the "mail me the results"
#   one) that should be made smarter at long last.  I mean, sheesh... how long
#   have I been putting that one off?

# Load modules.
import logging
import pyparsing as pp

import globals

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

# Loglevel for the bot.
#loglevel = logging.INFO

# Default e-mail address to send search results to.
default_email = ""

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
    logging.debug("Entered function parse_help().")
    try:
        parsed_command = help_command.parseString(request)
        return ("help", None, None)
    except pp.ParseException as x:
        logging.info("No match: {0}".format(str(x)))
        return (None, None, None)

# parse_list(): Function that matches whenever it encounters the phrase
#   "(list) (search) engines" in an input string.  Returns "list" for the
#   number of search terms, one for the search string, and None for the
#   destination e-mail.
def parse_list(request):
    logging.debug("Entered function parse_list().")
    command = pp.Optional(list_command) + pp.Optional(search_command)
    command = command + engines_command
    try:
        parsed_command = command.parseString(request)
        return("list", None, None)
    except pp.ParseException as x:
        logging.info("No match: {0}".format(str(x)))
        return (None, None, None)

# parse_get_request(): Function that matches on commands of the form "get top
#   <foo> hits for <bar>" in an input string.  Returns an integer number of
#   search results (up to 50), a URL encoded search string, and the e-mail
#   address "XMPP", meaning that the results will be sent to the user via the
#   XMPP bridge.
def parse_get_request(request):
    logging.debug("Entered function parse_get_request().")
    command = get_command + top_command + results_count + hitsfor_command
    command = command + pp.Group(search_terms).setResultsName("searchterms")

    number_of_search_results = 0

    try:
        parsed_command = command.parseString(request)
        number_of_search_results = word_and_number(parsed_command["count"])

        # Grab the search term.
        search_term = make_search_term(parsed_command["searchterms"])

        return (number_of_search_results, search_term, "XMPP")
    except pp.ParseException as x:
        logging.info("No match: {0}".format(str(x)))
        return (None, None, None)

# parse_and_email_results(): Function that matches on commands of the form
#   "send/e-mail/email/mail top <foo> hits for <search terms>".  Returns an
#   integer number of search results (up to 50), a URL encoded search string,
#   and an e-mail address.
def parse_and_email_results(request):
    logging.debug("Entered function parse_and_email_results().")
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
        logging.info("No match: {0}".format(str(x)))
        return (None, None, None)

# parse_specific_search(): Function that matches on commands of the form
#   "search <shortcode> for <search terms>".  Returns a default number of
#   search results (10) until I can make the parser more sophisticated, a URL
#   encoded search string which includes the shortcode for the search engine
#   ("!foo"), and "XMPP", because this is really only useful for mobile
#   requests.
def parse_specific_search(request):
    logging.debug("Entered function parse_specific_search().")
    command = search_command + shortcut_command + for_command
    command = command + pp.Group(search_terms).setResultsName("searchterms")

    number_of_search_results = 10
    engine = ""
    searchterms = []

    try:
        parsed_command = command.parseString(request)
        engine = parsed_command["shortcode"]
        searchterms = parsed_command["searchterms"]
        logging.debug("Value of engine: %s" % engine)
        logging.debug("Value of searchterms: %s" % searchterms)

        # Check to see if the search engine is enabled.  We do this in a
        # circuitous fashion because we want either the shortcode or a failure,
        # while at the same time making it possible for the user to use the
        # name of the search engine.
        engine = is_enabled_engine(engine)
        if not engine:
            logging.debug("Engine %s matches but is not enabled." % engine)
            return(0, "", "")

        # Create a search term that includes the shortcode for the search
        # engine.
        searchterms.insert(0, engine)
        searchterms = make_search_term(searchterms)

    except pp.ParseException as x:
        logging.info("No match: {0}".format(str(x)))
        return (None, None, None)

    logging.debug("Returning number_of_search_results==%d, searchterms==%s, and XMPP." % (number_of_search_results, searchterms))
    return (number_of_search_results, searchterms, "XMPP")

# is_enabled_engine(): Utility function that scans the list of enabled search
#   engines and returns the shortcode for the search engine ("!foo") or None.
def is_enabled_engine(engine):
    # Test to see if the shortcode given (which could be either the name of the
    # search engine or the actual shortcode) are in the list.  We append a bang
    # (!) to the shortcode so that Searx knows to use it as a specific search.
    for i in globals.search_engines:
        if i["name"] == engine.lower():
            logging.debug("Search engine " + str(engine) + " enabled.")
            return "!" + i["shortcut"]
        if i["shortcut"] == engine.lower():
            logging.debug("Search engine " + str(engine) + " enabled.")
            return "!" + i["shortcut"]
    return None

# parse_search_request(): Takes a string and figures out what kind of search
#   request the user wants.  Requests are something along the form of "top ten
#   hits for foo" or "search Tor for bar".  Returns the number of results to
#   send the user,bthe URI for the search terms, and the address to send the
#   results to ("XMPP" if it's supposed to go back to the user via the XMPP
#   bridge).
def parse_search_request(search_request):
    logging.debug("Entered function parse_search_request().")
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
        logging.debug("Got empty search request.")
        return (number_of_search_results, search_term, email_address)

    # Attempt to parse a request for online help.
    (number_of_search_results, search_term, email_address) = parse_help(search_request)
    if number_of_search_results == "help":
        logging.info("The user is asking for online help.")
        return ("help", None, None)

    # Attempt to parse a "list search engines" request.
    (number_of_search_results, search_term, email_address) = parse_list(search_request)
    if number_of_search_results == "list":
        logging.info("The user has requested a list of search engines.")
        return ("list", None, None)

    # Attempt to parse a "get" request.
    (number_of_search_results, search_term, email_address) = parse_get_request(search_request)
    if number_of_search_results and (email_address == "XMPP"):
        logging.info("The user has sent the search term " + str(search_term))
        return (number_of_search_results, search_term, "XMPP")

    # Attempt to parse an "email results" request.
    (number_of_search_results, search_term, email_address) = parse_and_email_results(search_request)
    if number_of_search_results and ("@" in email_address):
        logging.info("The user has requested that search results for " + str(search_term) + " be e-mailed to " + email_address + ".")
        return (number_of_search_results, search_term, email_address)

    # Attempt to parse a search for a specific engine.  If it works, prepend
    # the string "!<search shortcode>" so that Searx knows to search on one
    # search engine only.
    (number_of_search_results, search_term, email_address) = parse_specific_search(search_request)
    if number_of_search_results and (email_address == "XMPP"):
        logging.info("The user has requested a specific search: " + str(search_term))
        return (number_of_search_results, search_term, "XMPP")

    # Fall-through - this should happen only if nothing at all matches.
    logging.info("Fell all the way through in parse_search_request().  Telling the user I didn't understand what they said.")
    globals.send_message_to_user(globals.server, "I didn't understand your command.  Try again, please.")
    return (0, "", None)
