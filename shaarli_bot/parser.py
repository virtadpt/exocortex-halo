#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# parser.py - Module for shaarli_bot.py that implements all of the parsing
#   related functions.

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# -

# Load modules.
import logging
import pyparsing as pp

# Parser primitives
# We define them up here because they'll be re-used over and over.
help_pp = pp.CaselessLiteral("help")

search_pp = pp.CaselessLiteral("search")
for_pp = pp.CaselessLiteral("for")
tags_pp = pp.CaselessLiteral("tags")

# Command parsers
# help
help_command = help_pp

# search for <thing>
search_for_command = search_pp + for_pp

# search tags <tag>
search_tags_command = search_pp + tags_pp

# search tags for <tag>
search_tags_for_command = search_pp + tags_pp + for_pp

# Functions
# extract_search_term(): Function that takes a search term from the user and
#   the output of what the parser found in the string, and deletes the latter
#   from the former.  Returns just the search term.
def extract_search_term(search_term, command):
    logging.debug("Entered function parser.extract_search_term().")
    logging.debug("Value of search_term: " + str(search_term))
    logging.debug("Value of command: " + str(command))

    found_words = []
    search_term_list = []
    new_search_term_list = []

    # Extract the words that the parser found and tuck them into a list.
    # What the parser returned isn't actually an array but it can be treated
    # as one, which can be confusing.
    for i in command:
        found_words.append(i)

    # Convert the search term into an array of normalized words.
    search_term_list = search_term.lower().split()

    # Delete each word the parser found from the search term, leaving just the
    # string the user is searching on.
    for i in search_term_list:
        if i not in found_words:
            new_search_term_list.append(i)
    search_term = " ".join(new_search_term_list)

    logging.debug("Cleaned up search term: " + str(search_term))
    return search_term

# parse_help(): Function that matches the word "help" all by itself in an input
#   string.  Returns the string "help" on a match and None if not.
def parse_help(command):
    logging.debug("Entered function parser.parse_help().")
    try:
        parsed_command = help_command.parseString(command)
        return "help"
    except:
        return None

# parse_search(): Function that matches on variants of "search".  Returns a
#   hash table populated with two keys if successful, an empty hash table if
#   not.
def parse_search(command):
    logging.debug("Entered function parser.parse_search().")
    logging.debug("Value of command: " + str(command))

    # Handle that holds the output from each parser.
    parsed_command = None

    # Search term to query Shaarli for.
    search_term = None

    # Result of parsing.
    result = {}

    # "search for"
    try:
        parsed_command = search_for_command.parseString(command)
        search_term = extract_search_term(command, parsed_command)
        result["type"] = "search text"
        result["search term"] = search_term
        logging.debug("Value of result: " + str(result))
        return result
    except:
        logging.debug("Didn't match on 'search for'.")
        pass

    return None

# parse_search_tags(): Function that matches on variants of "search".  Returns a
#   hash table populated with two keys if successful, an empty hash table if
#   not.
def parse_search_tags(command):
    logging.debug("Entered function parser.parse_search_tags().")
    logging.debug("Value of command: " + str(command))

    # Handle that holds the output from each parser.
    parsed_command = None

    # Search term to query Shaarli for.
    search_term = None

    # Result of parsing.
    result = {}

    # "search tags for"
    try:
        parsed_command = search_tags_for_command.parseString(command)
        search_term = extract_search_term(command, parsed_command)
        result["type"] = "search tags"
        result["search term"] = search_term
        logging.debug("Value of result: " + str(result))
        return result
    except:
        logging.debug("Didn't match on 'search tags for'.")
        pass

    # "search tags"
    try:
        parsed_command = search_tags_command.parseString(command)
        search_term = extract_search_term(command, parsed_command)
        result["type"] = "search tags"
        result["search term"] = search_term
        logging.debug("Value of result: " + str(result))
        return result
    except:
        logging.debug("Didn't match on 'search tags'.")
        pass

    return None

# parse_command(): Function that parses commands from the message bus.
#   Commands come as strings and are run through PyParsing to figure out what
#   they are.  A single-word string is returned as a match or None on no match.
#   Conditionals are short-circuited to speed up execution.
def parse_command(command):
    logging.debug("Entered function parser.parse_command().")
    logging.debug("Value of command: " + str(command))

    # Handle to the post-parsing command.
    parsed_command = None

    # If the get request is empty (i.e., nothing in the queue), bounce.
    if "no commands" in command:
        return None

    # Online help?
    parsed_command = parse_help(command)
    if parsed_command == "help":
        return parsed_command

    # Search text...
    parsed_command = parse_search(command)
    if parsed_command:
        return parsed_command

    # Search tags...
    parsed_command = parse_search_tags(command)
    if parsed_command:
        return parsed_command

    # Fall-through: Nothing matched.
    return "unknown"

if "__name__" == "__main__":
    pass
