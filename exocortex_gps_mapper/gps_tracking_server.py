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
import json
import sys
import web

# Constants.
# API key that the GPS tracker software has to include in its target URL to
# keep people from messing with it.  I'll probably change this before I go
# live.
API_KEY = "<put a bunch of junk here as your API key>"

# Global variables.
# Current GPS coordinates, as signed floating point values.
current_latitude = 0.0
current_longitude = 0.0

# The tracker app's status.
app_status = ''

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

# current_location: Sets up a REST rail that redirects whoever accesses it to
#   a relatively hi-res map centered on my current GPS coordinates.  Right now
#   it uses gps-coordinates.net, and their API takes the form
#   /latitude-longitude/<lat>/<lon>/<zoom>/roadmap
#   <zoom> is an integer value that controls the map's level of resolution.
class current_location:

    # They default to 10, 20 suits my purposes better.
    zoom = 20

    def GET(self):
        # Assemble a URL for the map.
        map_url = 'http://www.gps-coordinates.net/latitude-longitude/'
        map_url = map_url + str(current_latitude) + '/'
        map_url = map_url + str(current_longitude) + '/'
        map_url = map_url + str(self.zoom) + '/'
        map_url = map_url + 'roadmap'

        # Redirect to the mapping service.
        raise web.seeother(map_url)

# coordinates: Sets up a REST rail that listens for HTTP requests of the form
#   /coordinates?api_key=<foo> and returns a JSON doc of the last known set of
#   map coordinates.  The JSON doc takes the form
#   {"lat": current_latitude, "lon", current_longitude}
class coordinates:
    def GET(self):

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

        # If the checks have all passed, return the current map coordinates.
        coordinates = {"lat":current_latitude, "lon":current_longitude}
        return json.dumps(coordinates)

# Core code...
# Define the API rails the server will listen for.
urls = (
    '/gps', 'gps_tracker',
    '/map', 'current_location',
    '/coordinates', 'coordinates'
    )

# Allocate an HTTP server and kick it off.
app = web.application(urls, globals())
if __name__ == "__main__":
    app.run()

# Fin.

