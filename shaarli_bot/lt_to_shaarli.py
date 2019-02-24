#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# lt_dump_to_shaarli.py - Takes a JSON dump from Librarything and pumps the
#   entries, one at a time, into a Shaarli instance so it can be used as a
#   searchable card catalogue (because LT doesn't have a search API).  LT's
#   JSON dumps have serious internal inconsistencies, so there are a lot of
#   key checks to see if some key or other exists.
#
#   I strongly suggest running this tool with --dryrun a few times because you
#   will probably have to clean up your data - adding a few JSON keys with
#   sane defaults (like: ["copies"]: 1 because you own one copy of something).
#   This is not a fire-and-forget kind of deal.

# By: The Doctor

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:

# Load modules.
import argparse
import HTMLParser
import json
import jwt
import logging
import os.path
import requests
import sys
import time

# Constants.
# Build the JWT headers.
jwt_headers = {}
jwt_headers["alg"] = "HS512"
jwt_headers["typ"] = "JWT"

# Global variables.
argparser = None
args = None
loglevel = None
jsonfile = None
parser = None
lt_books = {}
old_book = {}
new_book = {}
payload = {}
jwt_token = None
headers = {}
request = None

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

# Core code...
# Set up a command line argument parser.
argparser = argparse.ArgumentParser(description="A command line utility which takes a JSON dump from Librarything and pumps it into a Shaarli instance using the API.")
argparser.add_argument("--loglevel", action="store", default="info",
    help="Valid log levels: critical, error, warning, info, debug, notset.  Defaults to info.")

argparser.add_argument("--apikey", action="store", required=True,
    help="API key for a Shaarli instance.")

argparser.add_argument("--url", action="store", required=True,
    help="Full URL to a Shaarli instance.")

argparser.add_argument("--books", action="store", required=True,
    help="Full path to a JSON document containing a Librarything JSON dump.")

argparser.add_argument("--dryrun", action="store_true", default=False,
    help="If set, the utility will not try to write anything.")

argparser.add_argument("--delay", action="store", type=float, default=2.5,
    help="Number of seconds to wait in between requests.  Defaults to 2.5.")

# Parse the argument vector.
args = argparser.parse_args()

# Set up logging.
loglevel = process_loglevel(args.loglevel.lower())
logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Make sure the Librarything dumpfile exists.
if not os.path.exists(args.books):
    logger.error("Unable to open Librarything dump " + args.books + ".")
    sys.exit(1)

# Read in the Unmark JSON dump.
with open(args.books, "r") as jsonfile:
    lt_books = json.load(jsonfile)

# Set the content type header.
headers["Content-Type"] = "application/json"

# Allocate an HTML parser to unescape HTML entities.
parser = HTMLParser.HTMLParser()

# Roll through each book in the JSON document.
for book in lt_books:
    logger.debug("Now processing book " + str(book) + ".")

    # Set up the data structures to make life easier.
    old_book = lt_books[book]
    new_book = {}
    new_book["url"] = ""
    new_book["private"] = True
    new_book["description"] = ""
    new_book["tags"] = []

    # Title of the book.
    new_book["title"] = parser.unescape(old_book["title"])
    new_book["title"] = new_book["title"].strip().title()

    # Authors of the book.
    if "authors" in old_book.keys():
        # Case: authors is a populated list.
        if len(old_book["authors"]):
            new_book["description"] = new_book["description"] + "Author: " + parser.unescape(old_book["authors"][0]["fl"]) + "\n"
    # Case: primaryauthor exists in the JSON dump.
    elif "primaryauthor" in old_book.keys():
        tmp = old_book["primaryauthor"]
        tmp = tmp.split(",")
        tmp = tmp.reverse()
        tmp = " ".join(tmp)
        tmp = tmp.strip()
        tmp = parser.unescape(tmp)
        new_book["description"] = new_book["description"] + "Author: " + tmp + "\n"
    # Case: No authors credited for this book.
    else:
        new_book["description"] = new_book["description"] + "Author: unknown\n"

    # Tags
    if "tags" in old_book.keys():
        for i in old_book["tags"]:
            new_book["tags"].append(i.replace(" ", "_"))

    # ISBN
    if "isbn" in old_book.keys():
        if old_book["isbn"]["2"] is not None:
            new_book["description"] = new_book["description"] + "ISBN: " + old_book["isbn"]["2"] + "\n"
        elif old_book["isbn"]["0"] is not None:
            new_book["description"] = new_book["description"] + "ISBN: " + old_book["isbn"]["0"] + "\n"
    elif "originalisbn" in old_book.keys():
        new_book["description"] = new_book["description"] + "ISBN: " + old_book["originalisbn"] + "\n"
    else:
        new_book["description"] = new_book["description"] + "ISBN: unknown\n"

    # Publication data
    if "publication" in old_book.keys():
        new_book["description"] = new_book["description"] + "Publication: " + parser.unescape(old_book["publication"]) + "\n"
    else:
        new_book["description"] = new_book["description"] + "Publication: unknown\n"

    # Year of publication
    if "date" in old_book.keys():
        new_book["description"] = new_book["description"] + "Year: " + old_book["date"] + "\n"
    else:
        new_book["description"] = new_book["description"] + "Year: unknown\n"

    # Dewey decimal code
    if "ddc" in old_book.keys():
        new_book["description"] = new_book["description"] + "Dewey Decimal Code: " + old_book["ddc"]["code"][0] + "\n"
    else:
        new_book["description"] = new_book["description"] + "Dewey Decimal Code: unknown\n"

    # Library of Congress code
    if "lcc" in old_book.keys():
        if old_book["lcc"]:
            new_book["description"] = new_book["description"] + "Library of Congress: " + old_book["lcc"]["code"] + "\n"
    else:
        new_book["description"] = new_book["description"] + "Library of Congress: unknown\n"

    # Number of copies owned
    if "copies" in old_book.keys():
        new_book["description"] = new_book["description"] + "Number of copies owned: " + old_book["copies"] + "\n"
    else:
        new_book["description"] = new_book["description"] + "Number of copies owned: 1\n"

    # Number of pages
    if "pages" in old_book.keys():
        new_book["description"] = new_book["description"] + "Pages: " + old_book["pages"] + "\n"
    else:
        new_book["description"] = new_book["description"] + "Pages: unknown\n"

    # Build the JWT payload.  The IAT time must be in UTC!
    payload["iat"] = int(time.mktime(time.localtime()))
    logger.debug("Value of payload: " + str(payload))

    # Build a JWT token.
    jwt_token = jwt.encode(payload, args.apikey, algorithm="HS512",
        headers=jwt_headers)
    logger.debug("Value of jwt_token: " + jwt_token)

    # Set the authorization header.
    headers["Authorization"] = "Bearer " + jwt_token

    # build a new book entry here.

    # Send the new book to Shaarli if this isn't a dry run.
    if not args.dryrun:
        logger.info("Sending book" + str(new_book))
        response = requests.post(args.url+"/api/v1/links",
            data=json.dumps(new_book), headers=headers)
        logger.debug(json.dumps(response.json()))
    else:
        logger.info("Not sending book because this is a dry run.")
        print json.dumps(new_book)

    # Sleep or a couple of seconds so we don't overwhelm the server.
    if not args.dryrun:
        time.sleep(args.delay)

# Fin.
sys.exit(0)
