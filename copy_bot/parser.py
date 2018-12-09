#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# parser.py - Module for copy_bot.py that implements all of the parsing related
#   functions.

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
help_command = pp.CaselessLiteral("help")

# File paths are of the form ((/)*a?)?
# * Zero or more slashes.
# * One or more alphanumeric characters or punctuation marks.
# * One or more of the above combinations.
pathname_match = pp.Word(pp.printables)

copy_command = pp.CaselessLiteral("copy")
from_command = pp.CaselessLiteral("from")
to_command = pp.CaselessLiteral("to")
into_command = pp.CaselessLiteral("into")
everything_command = pp.CaselessLiteral("everything")
in_command = pp.CaselessLiteral("in")
asterisk_command = pp.CaselessLiteral("*")
all_command = pp.CaselessLiteral("all")
files_command = pp.CaselessLiteral("files")

# Command parsers
# copy <file> <dir><optional filename>
copy_foo_bar_command = copy_command + pathname_match + pathname_match

# copy <file> to <dir><optional filename>
copy_to_command = copy_command + pathname_match + to_command + pathname_match

# copy <file> into <dir><optional filename>
copy_into_command = copy_command + pathname_match + into_command + pathname_match

# copy from <file> to <dir><optional filename>
copy_from_command = copy_command + from_command + pathname_match + to_command + pathname_match

# copy from <file> into <dir><optional filename>
copy_from_into_command = copy_command + from_command + pathname_match + into_command + pathname_match

# copy <dir> to <dir>
copy_dir_to_dir_command = copy_command + pathname_match + to_command + pathname_match

# copy <dir> into <dir>
copy_dir_into_dir_command = copy_command + pathname_match + into_command + pathname_match

# copy everything in <dir> to <dir>
copy_everything_in_dir_command = copy_command + everything_command + in_command + pathname_match + to_command + pathname_match

# copy everything in <dir> into <dir>
copy_everything_into_dir_command = copy_command + everything_command + in_command + pathname_match + into_command + pathname_match

# copy all files in <dir> to <dir>
copy_all_command = copy_command + all_command + files_command + in_command + pathname_match + to_command + pathname_match

# copy all files in <dir> into <dir>
copy_all_into_command = copy_command + all_command + files_command + in_command + pathname_match + into_command + pathname_match

# copy * in <dir> to <dir>
copy_asterisk_to_dir = copy_command + asterisk_command + in_command + pathname_match + to_command + pathname_match

# copy * in <dir> into <dir>
copy_asterisk_into_dir = copy_command + asterisk_command + in_command + pathname_match + into_command + pathname_match

# copy all files in <dir> to <dir>
copy_all_files_to_dir = copy_command + all_command + files_command + in_command + pathname_match + to_command + pathname_match

# copy all files in <dir> into <dir>
copy_all_files_into_dir = copy_command + all_command + files_command + in_command + pathname_match + into_command + pathname_match

# Functions
# parse_help(): Function that matches the word "help" all by itself in an input
#   string.  Returns the string "help" on a match and None if not.
def parse_help(command):
    try:
        parsed_command = help_command.parseString(command)
        return "help"
    except:
        return None

# parse_single_file_copy(): Function that matches one-to-one copy requests.
def parse_single_file_copy(command):
    logging.debug("Entered function parser.parse_single_file_copy().")
    logging.debug("Value of command: " + str(command))

    # Handle that holds the output from each parser.
    parsed_command = None

    # Hash that holds the filespecs.
    filespecs = {}

    # "copy foo bar"
    try:
        parsed_command = copy_foo_bar_command.parseString(command)
        filespecs['from'] = parsed_command[1]
        filespecs['to'] = parsed_command[2]
        filespecs['type'] = "copy"
        logger.debug("Copy " + str(filespecs['from']) + " to " + str(filespecs['to']) + " detected.")
    except:
        pass

    # "copy foo to bar"
    try:
        parsed_command = copy_to_command.parseString(command)
        filespecs['from'] = parsed_command[1]
        filespecs['to'] = parsed_command[3]
        filespecs['type'] = "copy"
        logger.debug("Copy " + str(filespecs['from']) + " to " + str(filespecs['to']) + " detected.")
    except:
        pass

    # "copy from foo to bar"
    try:
        parsed_command = copy_from_command.parseString(command)
        filespecs['from'] = parsed_command[2]
        filespecs['to'] = parsed_command[4]
        filespecs['type'] = "copy"
        logger.debug("Copy from " + str(filespecs['from']) + " to " + str(filespecs['to']) + " detected.")
    except:
        pass

    # "copy foo into bar"
    try:
        parsed_command = copy_into_command.parseString(command)
        filespecs['from'] = parsed_command[1]
        filespecs['to'] = parsed_command[3]
        filespecs['type'] = "copy"
        logger.debug("Copy " + str(filespecs['from']) + " into " + str(filespecs['to']) + " detected.")
    except:
        pass

    # "copy from foo into bar"
    try:
        parsed_command = copy_from_into_command.parseString(command)
        filespecs['from'] = parsed_command[2]
        filespecs['to'] = parsed_command[4]
        filespecs['type'] = "copy"
        logger.debug("Copy from " + str(filespecs['from']) + " into " + str(filespecs['to']) + " detected.")
    except:
        pass

    # Return the filespecs hash table.
    logging.debug("Value of parsed_command: " + str(parsed_command))
    logging.debug("Value of filespecs: " + str(filespecs))
    return filespecs

# parse_multiple_file_copy(): Function that matches multiple file copy requests.
#   This pretty much means everything in a directory into another directory.
def parse_multiple_file_copy(command):
    logging.debug("Entered function parser.parse_multiple_file_copy().")
    logging.debug("Value of command: " + str(command))

    # Handle that holds the output from each parser.
    parsed_command = None

    # Hash that holds the filespecs.
    filespecs = {}

    # "copy /path/to to /another/path"
    # (The * is implied.)
    try:
        parsed_command = copy_dir_to_dir_command.parseString(command)
        filespecs['from'] = parsed_command[1]
        filespecs['to'] = parsed_command[3]
        filespecs['type'] = "copy"
        logger.debug("Copy " + str(filespecs['from']) + " to " + str(filespecs['to']) + " detected.")
    except:
        pass

    # "copy /path/to into /another/path"
    # (The * is implied.)
    try:
        parsed_command = copy_dir_to_dir_command.parseString(command)
        filespecs['from'] = parsed_command[1]
        filespecs['to'] = parsed_command[3]
        filespecs['type'] = "copy"
        logger.debug("Copy " + str(filespecs['from']) + " into " + str(filespecs['to']) + " detected.")
    except:
        pass

    # "copy everything in /path/to to /another/path"
    # (The * is implied.)
    try:
        parsed_command = copy_everything_in_dir_command.parseString(command)
        filespecs['from'] = parsed_command[3]
        filespecs['to'] = parsed_command[5]
        filespecs['type'] = "copy"
        logger.debug("Copy everything in " + str(filespecs['from']) + " to " + str(filespecs['to']) + " detected.")
    except:
        pass

    # "copy everything in /path/to into /another/path"
    # (The * is implied.)
    try:
        parsed_command = copy_everything_into_dir_command.parseString(command)
        filespecs['from'] = parsed_command[3]
        filespecs['to'] = parsed_command[5]
        filespecs['type'] = "copy"
        logger.debug("Copy everything in " + str(filespecs['from']) + " into " + str(filespecs['to']) + " detected.")
    except:
        pass

    # "copy * in /path/to to /another/path"
    try:
        parsed_command = copy_asterisk_to_dir.parseString(command)
        filespecs['from'] = parsed_command[3]
        filespecs['to'] = parsed_command[5]
        filespecs['type'] = "copy"
        logger.debug("Copy * in " + str(filespecs['from']) + " to " + str(filespecs['to']) + " detected.")
    except:
        pass

    # "copy * in /path/to into /another/path"
    try:
        parsed_command = copy_asterisk_into_dir.parseString(command)
        filespecs['from'] = parsed_command[3]
        filespecs['to'] = parsed_command[5]
        filespecs['type'] = "copy"
        logger.debug("Copy * in " + str(filespecs['from']) + " into " + str(filespecs['to']) + " detected.")
    except:
        pass

    # "copy all files in /path/to to /another/path"
    try:
        parsed_command = copy_all_files_to_dir.parseString(command)
        filespecs['from'] = parsed_command[4]
        filespecs['to'] = parsed_command[6]
        filespecs['type'] = "copy"
        logger.debug("Copy all files in " + str(filespecs['from']) + " to " + str(filespecs['to']) + " detected.")
    except:
        pass

    # "copy all files in /path/to into /another/path"
    try:
        parsed_command = copy_all_files_into_dir.parseString(command)
        filespecs['from'] = parsed_command[4]
        filespecs['to'] = parsed_command[6]
        filespecs['type'] = "copy"
        logger.debug("Copy all files in " + str(filespecs['from']) + " into " + str(filespecs['to']) + " detected.")
    except:
        pass

    # Return the filespecs hash table.
    logging.debug("Value of parsed_command: " + str(parsed_command))
    logging.debug("Value of filespecs: " + str(filespecs))
    return filespecs

# parse_command(): Function that parses commands from the message bus.
#   Commands come as strings and are run through PyParsing to figure out what
#   they are.  A single-word string is returned as a match or None on no match.
#   Conditionals are short-circuited to speed up execution.
def parse_command(command):
    logging.debug("Entered function parser.parse_command().")
    logging.debug("Value of command: " + str(command))

    # Handle to the post-parsing command.
    parsed_command = None

    # Clean up the incoming command.
    command = command.strip()
    command = command.strip('.')
    command = command.strip(',')

    # If the get request is empty (i.e., nothing in the queue), bounce.
    if "no commands" in command:
        return None

    # Online help?
    parsed_command = parse_help(command)
    if parsed_command == "help":
        return parsed_command

    # Multiple file copy?
    parsed_command = parse_multiple_file_copy(command)
    if parsed_command:
        return parsed_command

    # Single file copy?
    parsed_command = parse_single_file_copy(command)
    if parsed_command:
        return parsed_command

    # Fall-through: Nothing matched.
    return "unknown"

if "__name__" == "__main__":
    pass

