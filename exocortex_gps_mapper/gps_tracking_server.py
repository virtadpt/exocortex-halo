#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# gps_tracking_server.py - Implements a basic HTTP server that the Self Hosted
#   GPS Tracker app (https://github.com/herverenault/Self-Hosted-GPS-Tracker)
#   can send GPS coordinates to.  I don't actually have any specific plans for
#   it right now, just a general idea of making a me-tracker that'll alert
#   somebody if I suddenly stop moving or drop off the map.  Implements a REST
#   API and uses a user-defined API key to prevent random people from stuffing
#   bad data into it if they find it.

# URL: http://exocortex:

# By: The Doctor [412/724/301/703/415] [ZS] <drwho at virtadpt dot net>

# License: GPLv3

# v1.2 - Renamed current_location to map, because, what was I thinking?
# - Changed the URI for serving the HTML page to /.
# - Added code that forces the user to log into the application if they want
#   to look at the map.  Added code that requests the cookie the app sets in
#   the browser and compares it to the nonce created at start-time.
# - Added code that returns the HTML page gps_tracking_map.html static page
#   when a logged-in user visits the root URI.
# v1.1 - Added API key support to the /coordinates endpoint, so that someone
#   can't just connect to the server and find out where the user is.
# - When the app status changes to 'stop', reset the current GPS coordinates
#   to known values (0.0 / 0.0) so that third party code has a stop value to
#   look out for.
# - Fixed a bug in which the /coordinates endpoint didn't return valid JSON
#   because I'm dumb.
# v1.0 - Initial release.

# TO-DO:
# - Figure out a way of sending error logs for diagnosis.  Maybe e-mail me so
#   that I can keep an eye on it?
# - Add a feature in which a "send help" condition is triggered in the event
#   that I haven't moved in a certain period of time (coordinates don't change
#   noticeably for a definable period of time).
# - Add password authentication to /map for a little extra security.
# - Figure out how to proxy this through the existing web server.
# - Find a mapping service that will let me do Hollywood-style "follow me
#   around" tracking.  That'll probably involve serving up a local HTML page
#   with the right kinds of JavaScript.  Have to ask around about that.

# Load modules.
import base64
import json
import random
import re
import sys
import web

# Constants.
# API key that the GPS tracker software has to include in its target URL to
# keep people from messing with it.  I'll probably change this before I go
# live.
API_KEY = "123456"

# Global variables.
# Current GPS coordinates as signed floating point values.
current_latitude = 0.0
current_longitude = 0.0

# The tracker app's status.
app_status = ''

# Usernames and passwords of users who are allowed to view the map.  Can be
# extended arbitrarily but for now just one will do.  Note that the final pair
# in teh list needs a comma after it for authentication to work.
credentials = (
    ('user', 'password'),
    )

# This is a randomly generated nonce given to the browser upon a successful
# login.  It's used to determine whether or not the loaded map page can access
# the user's coordinates.
random.seed()
nonce = random.getrandbits(64)
nonce = base64.b64encode(str(nonce))

# Classes.
# gps_tracker: Sets up a REST rail that listens for HTTP requests of the form
#   /gps?api_key=<foo>&lat=<bar>&lon=<baz>.
class gps_tracker:
    def GET(self):
        # Redeclare these as global so their values can be updated.
        global current_latitude
        global current_longitude
        global app_status

        # Extract the arguments passed to this REST rail.
        uri_args = web.input()

        # Check the API key.  If it isn't there, send back a 401 (unauthorized).
        # If they don't match, send back a 403 (forbidden).
        if not uri_args.get('api_key'):
            web.ctx.status = '401 Unauthorized'
            return
        if uri_args.api_key != API_KEY:
            web.ctx.status = '403 Forbidden'
            return

        # Make sure there are latitude and longitude values.  If there aren't
        # do nothing and assume that current coordinates haven't changed.
        if not uri_args.get('lat'):
            print "WARNING: The app didn't send a latitude value.  WTF?"
        else:
            current_latitude = uri_args.lat

        if not uri_args.get('lon'):
            print "WARNING: The app didn't send a longitude value.  WTF?"
        else:
            current_longitude = uri_args.lon

        print "Current latitude: " + str(current_latitude)
        print "Current longitude: " + str(current_longitude)

        # Sometimes the tracker app sends its status.  For the purposes of
        # debugging it would be handy to capture that.
        if uri_args.get('tracker'):
            app_status = uri_args.tracker
            print "Current app status: " + app_status

        # If the tracking app has just shut down, reset the coordinates to a
        # known value.
        if app_status == 'stop':
            current_latitude = 0.0
            current_longitude = 0.0

# map: Sets up a REST rail that redirects whoever accesses it to a relatively
#   hi-res map centered on the user's current GPS coordinates.  Requires the
#   user to enter a username and passphrase to log in, which is hardcoded above.
class map:
    def GET(self):
        # Check to see if the viewer has logged into the app.  If they are,
        # return the gps_tracking_map.html page.  If not, redirect them to the
        # login handler.
        if web.ctx.env.get('HTTP_AUTHORIZATION') is not None:
            # Check to see if the browser is authenticated (i.e. has a cookie
            # set).
            cookie = web.cookies().get('gps-tracking-server-key')
            if cookie == nonce:
                raise web.seeother('/static/gps_tracking_map.html')
            else:
                return "Waitaminute..."
        else:
            raise web.seeother('/login')

# login: HTTP basic auth handler that protects the map rail from casual or
#   malicious browsers.
class login:
    def GET(self):
        # Check the HTTP session's environment for for the existence of the
        # "I'm authenticated!" header.
        auth = web.ctx.env.get('HTTP_AUTHORIZATION')

        # Is this an authorization request?
        auth_req = False

        # Not authenticated yet.
        if auth is None:
            auth_req = True
        else:
            # Extract the presented username and passphrase from the auth
            # header.
            auth = re.sub('^Basic ', '', auth)
            (username, password) = base64.decodestring(auth).split(':')

            # Test to see if the presented credentials are in the hardcoded
            # list of credentials at the top level.  Remember that when the
            # global credentials() list is edited, each entry must have a
            # comma after it, even if it's at the end.
            # (I spent way too long troubleshooting that bit.)
            if (username, password) in credentials:
                # Set a cookie in the browser.  It'll expire when the browser
                # closes.
                web.setcookie('gps-tracking-server-key', nonce)

                # Redirect to the map.
                raise web.seeother('/')
            else:
                # Credentials not found, next time through there will be
                # another authentication attempt.
                auth_req = True

        # If this is an authentication request, send a 401 back to the browser.
        if auth_req:
            web.header('WWW-Authenticate',
                'Basic realm="Orbital Laser Targeting"')
            web.ctx.status = '401 Unauthorized'
            return

# coordinates: Sets up a REST rail that listens for HTTP requests of the form
#   /coordinates?api_key=<foo> and returns a JSON doc of the last known set of
#   map coordinates.  The JSON doc takes the form
#   {"lat": current_latitude, "lon", current_longitude}
class coordinates:
    def GET(self):
        # Extract the arguments passed to this REST rail.
        uri_args = web.input()

        # MOOF MOOF MOOF - This is going away and will be replaced with a
        # cookie check.
        # Check the API key.  If it isn't there, send back a 401 (unauthorized).
        # If they don't match, send back a 403 (forbidden).
        if not uri_args.get('api_key'):
            web.ctx.status = '401 Unauthorized'
            return
        if uri_args.api_key != API_KEY:
            web.ctx.status = '403 Forbidden'
            return

        # If the checks have all passed, return the current map coordinates.
        coordinates = {"lat":current_latitude, "lon":current_longitude}
        return json.dumps(coordinates)

# Core code...
# Define the API rails the server will listen for.
urls = (
    '/coordinates', 'coordinates',
    '/gps', 'gps_tracker',
    '/login', 'login',
    '/', 'map'
    )

# Allocate an HTTP server and kick it off.
app = web.application(urls, globals())
if __name__ == "__main__":
    app.run()

# Fin.

