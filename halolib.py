#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

""" This is a module which collects all of the common functions and methods in
the Exocortex Halo into one place.  This'll make future maintenance and
adding new bots later somewhat easier. """

# By: The Doctor <drwho at virtadpt dot net>
#     0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv2
# Pre-requisite modules have their own licenses.

# v1.0 - Initial release.

# TO-DO:

# Load modules.
from email.mime.text import MIMEText

import json
import requests
import smtplib
import sys

# Classes.

# Functions.
""" email_response(): Function that e-mails something to the bot's user.  Takes
four arguments, strings containing a subject line, a message, an e-mail
address the message appears to be from, the destination e-mail address,
and the hostname of an SMTP server to send the message through.  Uses the
configured SMTP server to send the message.  Returns True (it worked) or
False (it didn't go through). """
def email_response(subject_line, message, origin_address, destination_address,
    smtp_server):
    smtp = None

    # Due diligence.
    if not subject_line:
        return False
    if not message:
        return False
    if not origin_address:
        return False
    if not destination_address:
        return False
    if not smtp_server:
        return False

    # Set up the outbound message.
    message = MIMEText(message)
    message['Subject'] = subject_line
    message['From'] = origin_address
    message['To'] = destination_address

    # Set up the SMTP connection and transmit the message.
    smtp = smtplib.SMTP(smtp_server)
    smtp.sendmail(origin_address, destination_address, message.as_string())
    smtp.quit()
    smtp = None
    return True

""" send_message_to_user(): Function that does the work of sending messages back
to the user by way of the XMPP bridge.  Takes three arguments, a string
containing the base URL of the message bus to contact, a string containing
the name of the bot that is sending the message, and the message to send
to the user. """
def send_message_to_user(server, bot_name, message):
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

""" set_loglevel(): Turn a string into a numerical value which Python's logging
module can use. """
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
if __name__ == '__main__':
    # Unit tests go here...
    sys.exit(0)

# Fin.

