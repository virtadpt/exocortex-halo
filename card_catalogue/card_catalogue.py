#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# card_catalogue.py - A relatively simple REST API that takes JSON backups of
#   LibraryThing (https://www.librarything.com/) accounts and makes it possible
#   to search your library.  Note that this code does NOT interface with LT,
#   you have to already be a use and download a backup copy of your data
#   (https://www.librarything.com/more/import) as a JSON document.
#
#   To be fair, even if you aren't an LT user I don't see why you couldn't use
#   this server as the back-end of a personal card catalogue.  I'll document
#   the JSON schema I use internally.
#
#   Uses SQLite as its back-end.

# LibraryThing JSON dump schema.  Edited to expose only the useful stuff.
# For each book...
#  "100681250": {
#    "books_id": "100681250",
#    "ddc": {
#      "code": [
#        "741.5"
#      ],
#    },
#    "entrydate": "2013-08-05",
#    "genre": [
#      "Graphic Novels"
#    ],
#    "isbn": [
#      "978-0-9926189-0"
#    ],
#    "primaryauthor": "Lackey, Chris",
#    "publication": "Witch House Media",
#    "rating": 4,
#    "secondaryauthor": "Fifer, Chad",
#    "tags": [
#      "graphic novel",
#      "science fiction",
#      "transhumanism",
#      "resurrection",
#      "simulation",
#      "autographed",
#      "198 of 500",
#      "deception",
#      "livin la vida posthumanity",
#      "uplifts",
#      "corporations"
#    ],
#    "title": "Transreality",
#  },

# By: The Doctor [412/724/301/703/415/510] <drwho at virtadpt dot net>

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# - Refactor into separate files once I have a PoC.
# - PoC test queries from the command line.
# - HTTP server.
# - Online documentation. (ongoing)
# - Process REST queries.
# - Update the database with a new LT dump.

# Load modules.
import argparse
import json
import logging
import os
import sqlite3
import sys

# Constants.

# Global variables.
# Handles for the CLI argument parser handler.
argparser = None
args = None

# Default loglevel.
loglevel = "INFO"

# Handle to a SQLite database.
database = None

# If this is a class or module, say what it is and what it does.

# Classes.

# Functions.
# build_new_database(): Function that builds a new database using a JSON dump
#   from LibraryThing and a path to a SQLite database file to use.  If the
#   database file already exists, 'force' must be set to True so it'll clobber
#   the existing DB.
def build_new_database(input_file, database, force):
    logger.debug("Entered function build_new_database().")

    librarything_datafile = None
    librarything_data = {}
    db = None
    cursor = None
    template = None

    # See if the database already exists.  ABEND if it does and the user isn't
    # forcing a rewrite.
    if os.path.exists(database):
        if not force:
            logger.info("Database file " + database + " already exists.  Re-run with --force to load in the new data file.")
            sys.exit(2)

    # Read in the Librarything export.
    try:
        librarything_datafile = open(input_file, "r")
        librarything_data = json.loads(librarything_datafile.read())
        librarything_datafile.close()
    except:
        logger.error("Unable to open LibraryThing data export " + str(input_file))
        sys.exit(1)

    # Create a new database.
    db = sqlite3.connect(database)
    cursor = db.cursor()

    # Create the data table.
    try:
        cursor.execute("CREATE TABLE books (book_id integer, dewey_decimal real, added_date text, genre text, isbn text, author text, publication text, rating integer, tags text, title text)")
    except:
        logger.info("Table already exists.  Loading data.")

    # Loop through the LibraryThing data dump and insert the salient data, line
    # by line.
    for book in librarything_data:
        # Start building the template to insert into the database.  We start
        # with an empty tuple.  When appending, we leave an open comma at the
        # end.
        template = ()

        # Librarything book ID.
        if "books_id" not in librarything_data[book].keys():
            template = template + (0, )
            logger.debug("No book ID found.  That was strange.  Using 0.")
        else:
            template = template + (librarything_data[book]["books_id"], )

        # Dewey decimal code.
        if "ddc" not in librarything_data[book].keys():
            template = template + (0.0, )
            logger.debug("Didn't find a Dewey decimal code - gave it one of 0.0.")
        else:
            template = template + (librarything_data[book]["ddc"]["code"][0], )

        # Date I entered the book into my card catalogue.
        if "entrydate" not in librarything_data[book].keys():
            template = template + ("2000-01-01", )
            logger.debug("No entrydate found.  Defaulted to 2000-01-01.")
        else:
            template = template + (librarything_data[book]["entrydate"], )

        # Genres the book falls into.
        if "genre" not in librarything_data[book].keys():
            template = template + ("Unknown", )
            logger.debug("Didn't find a genre - gave it one of 'unknown'.")
        else:
            template = template + (", ".join(librarything_data[book]["genre"]), )

        # Try to find an ISBN for the book.  This can be hit or miss because
        # LT seems to do this inconsistently so it's way more fiddly than it
        # has any right to be.  Start by determining if the isbn field doesn't
        # exist, and if this is the case see if we can use the originalisbn
        # field, and if that doesn't work use a default.
        if "isbn" not in librarything_data[book].keys():
            if "originalisbn" not in librarything_data[book].keys():
                template = template + ("No ISBN recorded.", )
                logger.debug("No ISBN found.  Used default.")
            else:
                template = template + (librarything_data[book]["originalisbn"], )
                logger.debug("Used 'originalisbn'.")
        else:
            # Sometimes this is a list.  Sometimes this is a hash.  I don't
            # know why this is so damned inconsistent but it has to be taken
            # into account.
            if type(librarything_data[book]["isbn"]) is list:
                template = template + (librarything_data[book]["isbn"][0], )
            if type(librarything_data[book]["isbn"]) is dict:
                template = template + (librarything_data[book]["isbn"]["2"], )

        # Recorded author(s) of the book.  Try sussing out the 'authors' object
        # first, try the [prim,second]aryauthor fields next.
        temp = []
        if "authors" in librarything_data[book].keys():
            for i in librarything_data[book]["authors"]:
                if not i:
                    temp.append("Unknown")
                    logger.debug("Got an empty author list.  Using a deault of 'Unknown'.")
                    break
                else:
                    temp.append(i["fl"])
        elif "primaryauthor" in librarything_data[book].keys():
            temp.append(librarything_data[book]["primaryauthor"])
            if "secondaryauthor" in librarything_data[book].keys():
                temp.append(librarything_data[book]["secondaryauthor"])
        else:
            # No authorship information?  Really?
            temp.append("Unknown Author")
        template = template + (", ".join(temp), )

        # Publication data.
        if "publication" not in librarything_data[book].keys():
            template = template + ("No publication data.", )
            logger.debug("No publication data found.")
        else:
            template = template + (librarything_data[book]["publication"], )

        # My rating of the book.  Default to 0 (not read) if necessary.
        if "rating" not in librarything_data[book].keys():
            template = template + (0, )
            logger.debug("No rating found, defaulting to 0 stars.")
        else:
            template = template + (librarything_data[book]["rating"], )

        # Tags I gave the book.  Use an empty string if there aren't any tags.
        if "tags" in librarything_data[book].keys():
            template = template + (", ".join(librarything_data[book]["tags"]), )
        else:
            template = template + ("", )

        # Title of the book.  Why does this come last?  Because that's how I
        # was working with the LT backup and I wanted to be consistent.
        if "title" not in librarything_data[book].keys():
            template = template + ("No Title", )
        else:
            template = template + (librarything_data[book]["title"], )

        # Load the template into the database.
        logger.debug(str(template))
        cursor.execute("""INSERT INTO books VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", template)

    # Commit the database all at once for efficiency.
    db.commit()

    # Free up some memory.
    librarything_data = None

    # Return a handle to the new database.
    return db

# set_loglevel(): Turn a string into a numerical value which Python's logging
#   module can use.
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

# Core code...
# Set up the command line argument parser.
argparser = argparse.ArgumentParser(description="A small REST API service that takes a data dump from a Librarything account and presents the data through a REST API.  LT doesn't have a personal search API so this is does what LT doesn't.")
argparser.add_argument("--address", action="store", default="127.0.0.1",
    help="IP address to listen on.  Defaults to 127.0.0.1.")
argparser.add_argument("--port", action="store", default=5555,
    help="Port to listen on.  Defaults to 5555/tcp.")
argparser.add_argument("--database", action="store", default="./books.db",
    help="Full path to a database file.")
argparser.add_argument('--loglevel', action='store',
    help='Valid log levels: critical, error, warning, info, debug, notset.  Defaults to INFO.')
argparser.add_argument("--load", action="store",
    help="Full path to a LibraryThing data dump to import.")
argparser.add_argument("--force", action="store_true",
    help="If the database already exists, this flag is required to import a new data file.  It won't let you clobber an existing database without it.")

# Parse the command line args.
args = argparser.parse_args()

# Set the loglevel from the override on the command line if it exists.
if args.loglevel:
    loglevel = set_loglevel(args.loglevel.lower())

# Configure the logger.
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# See if the user wants to build a new database.
if args.load:
    logger.info("Building new database...")
    database = build_new_database(args.load, args.database, args.force)

# Test to see if the database exists, and if it doesn't ABEND.
if not os.path.exists(args.database):
    logger.error("Database file " + str(args.database) + " not found!")
    sys.exit(1)

# Open the database.
if not database:
    database = sqlite3.connect(args.database)

# Fire up the HTTP server.

# Fin.
database.close()
sys.exit(0)
