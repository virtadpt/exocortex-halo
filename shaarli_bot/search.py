#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# search.py - Module for shaarli_bot.py that implements all of the search
#   related functions.

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# - I think I can refactor the search functions so that there's only one, and
#   the type-of-search argument is passed as a parameter.  This'll do for a
#   start, though.
# -

# Load modules.
import jwt
import json
import logging
import requests
import sys
import time

# Constants.
# Standard JSON Web Token header.
jwt_headers = {}
jwt_headers["alg"] = "HS512"
jwt_headers["typ"] = "JWT"

# Global variables
http_headers = {}
http_headers["Content-Type"] = "application/json"

# Payload to send to the Shaarli API.
payload = {}
payload["iat"] = 0

# Handle to a freshly generated JWT.
jwt_token = ""

# Functions
# search_text(): Function that runs a full-text search on the Shaarli instance
#   (but not the tags!).  Takes as its arguments a string to search for, a
#   URL to a Shaarli instance, and a Shaarli API secret.  Returns the JSON
#   from Shaarli.
def search_text(search_term, url, secret):
    logging.debug("Entered search.search_text().")

    request = None
    parameters = {}
    results = []

    # Build the JWT payload.  The IAT time must be in UTC!
    payload["iat"] = int(time.mktime(time.localtime()))
    logging.debug("Value of payload: " + str(payload))

    # Build a JWT token.
    jwt_token = jwt.encode(payload, secret, algorithm="HS512",
        headers=jwt_headers)
    logging.debug("Value of jwt_token: " + jwt_token)
    http_headers["Authorization"] = "Bearer " + jwt_token

    # Build request parameters.
    parameters["searchterm"] = search_term

    # Send the search request to Shaarli.
    request = requests.get(url + "/api/v1/links", params=parameters,
        headers=http_headers)
    results = request.json()

# search_tags(): Function that runs a tag-based search on the Shaarli
#   instance.  Takes as its arguments a string to search for, a URL to a
#   Shaarli instance, and a Shaarli API secret.  Returns the JSON
#   from Shaarli.
def search_tags(search_term, url, secret):
    logging.debug("Entered search.search_tags().")

    request = None
    parameters = {}
    results = []

    # Build the JWT payload.  The IAT time must be in UTC!
    payload["iat"] = int(time.mktime(time.localtime()))
    logging.debug("Value of payload: " + str(payload))

    # Build a JWT token.
    jwt_token = jwt.encode(payload, secret, algorithm="HS512",
        headers=jwt_headers)
    logging.debug("Value of jwt_token: " + jwt_token)
    http_headers["Authorization"] = "Bearer " + jwt_token

    # Build request parameters.
    parameters["searchtags"] = search_term

    # Send the search request to Shaarli.
    request = requests.get(url + "/api/v1/links", params=parameters,
        headers=http_headers)
    results = request.json()

    return results