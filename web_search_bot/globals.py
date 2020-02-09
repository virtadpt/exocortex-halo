#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# globals.py - A Web Search Bot module that implements a couple of global
#   variables.
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# v1.0 - Initial release.
#       - Broke a bunch of stuff out into this module because they get used
#       everywhere and using them as parameters was making it hard to keep
#       things tidy.

# TODO:
# -

# By: The Doctor <drwho at virtadpt dot net>
#     0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# Import modules.
import json
import logging
import requests

# Constants.
# When POSTing something to a service, the correct Content-Type value has to
# be set in the request.
headers = {
    "Content-type": "application/json"
    }

# The "http://system:port/" part of the message queue URL.
server = ""

# The name the search bot will respond to.  The idea is that this bot can be
# instantiated any number of times with different config files for different
# purposes.
bot_name = ""

# Search engines Searx is configured for.
search_engines = []

# Search categories.
search_categories = []

# Functions.
# send_message_to_user(): Function that does the work of sending messages back
# to the user by way of the XMPP bridge.  Takes two arguments, the server to
# send the message to and the message.  Returns a True or False which
# determines whether or not it worked.
def send_message_to_user(server, message):
    logging.debug("Entered function send_message_to_user().")
    logging.debug("Value of server: %s" % server)

    # Set up a hash table of stuff that is used to build the HTTP request to
    # the XMPP bridge.
    reply = {}
    reply["name"] = bot_name
    reply["reply"] = message

    # Send an HTTP request to the XMPP bridge containing the message for the
    # user.
    request = requests.put(server + "replies", headers=headers,
        data=json.dumps(reply))

if "__name__" == "__main__":
    print("No self tests yet.")
    sys.exit(0)
