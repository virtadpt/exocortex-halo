#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# exocortex_web_to_speech.py - Sets up a simple API that listens on the
#   loopback interface waiting for Exocortex to contact it.  Exocortex sends it
#   an API key, a phone number, and some text.  This daemon writes the text to
#   a file and calls the text2wave utility of Festival
#   (http://www.cstr.ed.ac.uk/projects/festival/) to convert it into a .wav
#   file.  It then calls exocortex_sip_client to place a telephone call using
#   the .wav as the voice channel.  This server is actually never supposed to
#   terminate.

# The API key is passed in the HTTP request header 'X-API-Key'.
# A cute way of playing with this is with the command
#  `curl -H 'X-API-Key: <blah> http://localhost:<port>/?var=...'`

# By: The Doctor [412/724/301/703/415][ZS] <drwho at virtadpt dot net>

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:

# Load modules.
import os
import subprocess
import tempfile
import web

# Constants.
# Only one URL to handle, and that's /.
urls = (
    '/', 'http_request_parser'
    )

# API key to minimize monkey business from outside.
API_KEY = '<put a bunch of junk here>'

# Path to the speech synthesis utility.
GENERATE = '/usr/bin/text2wave'

# Global variables.
# Phone number to dial.
phone_number = 0

# Message to eventually convert into speech.
message = ''

# Command to use to place the phone call.
exocortex_sip_client = '/path/to/exocortex_sip_client/call.sh'

# Classes.
# http_request_parser: Class that does all the heavy HTTP lifting, like picking
#   through the HTTP headers.  More specific utility functions are carried out
#   elsewhere.
# Arguments: ?number=NPANXXXXXX&message=URI+encoded+text+goes+here.
class http_request_parser:
    def GET(self):
        # Reference the few global variables required in this app.
        global phone_number
        global message

        # Generate tempfiles we're going to need for the text and generated
        # speech.
        temp_text_file = tempfile.NamedTemporaryFile(suffix='.txt', dir='/tmp/',
            delete=False)
        temp_text_filename = temp_text_file.name

        # Parse the HTTP request headers for the bits we care about.
        api_key_header = web.ctx.env.get('HTTP_X_API_KEY')
        remote_addr = web.ctx.env.get('REMOTE_ADDR')

        # If there is no API key, bounce.
        if not 'HTTP_X_API_KEY' in web.ctx.env.keys():
            web.ctx.status = '401 Unauthorized'
            return

        # If the API key isn't correct, reject.
        if api_key_header != API_KEY:
            web.ctx.status = '403 Forbidden'
            return

        # If the remote host wasn't 127.0.0.1, bounce.  This is an in-house
        # only kind of job.
        if remote_addr != '127.0.0.1':
            web.ctx.status = '401 Unauthorized'
            return

        # Extract the URI encoded arguments passed to the server.
        uri_args = web.input()
        phone_number = uri_args.number
        message = uri_args.message

        # Write the text into the tempfile.
        temp_text_file.write(message)
        temp_text_file.close()

        # Build the command to generate speech.
        synthesis_command = GENERATE + ' ' + temp_text_filename + ' -o ' + temp_text_filename + '.wav'

        # Generate the outgoing voice message.
        subprocess.call(synthesis_command, shell=True)

        # Call exocortex_sip_client to place the phone call.  Yes, this is
        # kind of ugly but to make the SIP software work on Ubuntu I had to
        # put everything into a virtualenv, which means wrapper scripts.  Yay.
        call_command = exocortex_sip_client + ' --production '
        call_command = call_command + '--phone-number ' + phone_number
        call_command = call_command + ' --message ' + temp_text_filename
        call_command = call_command + '.wav'
        subprocess.call(call_command, shell=True)

        # Clean up after ourselves.  Specifically cast to str() because Unicode
        # is always messin' with my Zen thing.
        os.unlink(str(temp_text_filename))
        os.unlink(str(temp_text_filename + '.wav'))

# Core code...
# Stand up the web application server.
app = web.application(urls, globals())
if __name__ == "__main__":
    app.run()

# Fin.
