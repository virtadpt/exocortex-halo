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

# This server defaults to port 3030/tcp.  You can change that by passing the
# port on the command line to listen on, like this:
#   exocortex_web_to_speech.py 16212

# One way of playing with this is with the command
#  `curl -X POST -H 'Content-Type: application/json \
#   -d '{"message":"foo", "number":"bar", "api key":"baz"}' \
#   http://localhost:<port>/`

# By: The Doctor [412/724/301/703/415][ZS] <drwho at virtadpt dot net>

# License: GPLv3

# v1.1 - Change default listen-on IP to 127.0.0.1.
# - Make web.py accept a port number as a command line argument and listen on
#   that instead of 8080/tcp.  Just in case, to prevent conflict with other
#   web.py apps on the same host, it defaults to port 3030/tcp.
# - Change the default HTTP method to POST.
# - Restructured the POST method handler to do things a little more sanely.
# - Added some better error checking.
# - Moveed the API key into a field of the incoming JSON request instead of an
#   HTTP header.
# - return() some HTML or JSON at the end of the HTTP request handler so that
#   Huginn has something to go from.  Probably JSON so that the PostAgent can
#   do something with it.
# - Added a HTTP GET method handler that prints some documentation.  It'll be
#   nice to have some debugging assistance.

# TO-DO:

# Load modules.
import json
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
API_KEY = '<change this>'

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
class http_request_parser:
    # This is the default HTTP handler method, which users are likely to
    # trigger by starting up this agent and then plugging the URI into their
    # web browser.
    def GET(self):
        html = """
        <head>
        <title>exocortex_web_to_speech.py help documentation</title>
        </head>

        <body>
        <p>This agent was designed to interface with Andrew Cantino's <a href="https://github.com/cantino/huginn/">Huginn</a> by providing a bridge to a speech synthesis utility (like the one in my <a href="https://github.com/virtadpt/exocortex-halo">halo</a>).  By default it listens on <a href="http://localhost:3030/">http://localhost:3030/</a> but you can set it to whatever you want by passing a different port number on the command line, like this: <b>./exocortex_web_to_speech.py 16212</b></p>

        <p>The HTTP interface is designed to work with Huginn's PostAgent.  You'll find a sample one in the code repository.</p>

        <p>To interact with this agent you need to place a <b>POST</b> request to the server and pass in a JSON document that has three strings: The message, an API key, and the phone number to dial (no spaces).  The value of the Content-Type HTTP header has to be "application/json".  It might look something like this:</p>

        <pre>
        {
          "api key":"AllYourBaseAreBelongToUs",
          "number":"2064560649",
          "message":"I'm sorry, Dave, I can't let you do that."
        }
        </pre>

        <p>(Note: The phone number 206-456-0649 belongs to <a href="http://thetestcall.blogspot.com/">The Test Call</a>, a free and legal public service which implements some features useful for testing and debugging VoIP software.  I started using them when I got tired of rickrolling myself.  If you find their service useful, I highly recommend sending them some money!)</p>

        <p>Anyway, Huginn's PostAgent will do this for you, so all you have to do is set it up right and that's it.  What you do with this agent after that is your business.  The API key is a string that you define yourself by changing the value of the <i>API_KEY</i> in the code.  I use the command <b>pwgen 30</b> to generate mine.  I know, I know, why not put it in a config file or make it a command line option?  I'll get around to it.  Or better yet, file a pull request. ;)</p>

        <p>If you want to experiment with it or debug any changes made, use <a href="http://curl.haxx.se/">curl</a>.  Here's one way to go about it: <b>curl -X POST -H "Content-Type: application/json" -d '{ "message":"This is where my message goes", "api key":"AllYourBaseAreBelongToUs", "number":"2064560649" }' http://localhost:3030/</b></p>
        </body>

        """

        return html

    # This HTTP method handler does the work of figuring out what the user
    # wants to call with and hands it off to the speech synthesizer after
    # processing it a bit.
    def POST(self):
        # Reference the few global variables required in this app.
        global phone_number
        global message

        # Extract the data submitted by the agent.
        data = json.loads(web.data())

        # Parse the HTTP request headers for the bits we care about.
        remote_addr = web.ctx.env.get('REMOTE_ADDR')

        # If the remote host wasn't 127.0.0.1, bounce.  This is an in-house
        # only kind of job.
        if remote_addr != '127.0.0.1':
            web.ctx.status = '401 Unauthorized'
            return "Error 401: Ya ain't from around these parts, are ya'?"

        # If no API key was submitted at all, bounce.
        if not 'api key' in data.keys():
            web.ctx.status = '401 Unauthorized'
            return "Error 401 - Missing API Key"

        # If the API key isn't correct, reject.
        if data['api key'] != API_KEY:
            web.ctx.status = '403 Forbidden'
            return "Error 403 - Incorrect API Key"

        # If no message was supplied, reject.
        if not 'message' in data.keys():
            web.ctx.status = '400 Bad Request'
            return "Error 400 - Required Argument Missing (key: 'message')"

        # If no phone number was supplied, reject.
        if not 'number' in data.keys():
            web.ctx.status = '400 Bad Request'
            return "Error 400 - Required Argument Missing (key: 'number')"

        # Generate tempfiles we're going to need for the text and generated
        # speech.
        temp_text_file = tempfile.NamedTemporaryFile(suffix='.txt', dir='/tmp/',
            delete=False)
        temp_text_filename = temp_text_file.name

        # Extract the URI encoded arguments passed to the server.
        phone_number = data['number']
        message = data['message']

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
        return "Success"

# reconfigurable_web_app(): Subclass of web.py's web.application that can be
#   instantiated to listen on ports other than 8080 by default.  It also only
#   listens on 127.0.0.1, rather than every IP address on the system.  This is
#   for additional security - it can only be contacted by other applications
#   running on the same host.  It defaults to port 3030/tcp.
class reconfigurable_web_app(web.application):
    def run(self, port=3030, *middleware):
        func = self.wsgifunc(*middleware)
        return web.httpserver.runsimple(func, ('127.0.0.1', port))

# Core code...
# Stand up the web application server.
app = reconfigurable_web_app(urls, globals())
if __name__ == "__main__":
    app.run(port=3030)

# Fin.
