#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# Given a URL on the command line, authenticate to a Wallabag instance and
#   add the link to the database.  Returns 0 on success, non-zero on failure.

# By: The Doctor <drwho at virtadpt dot net>
# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# - Turn this into a real utility.  This is just a hack.

# Load modules.
import requests
import sys

# Constants.
client_id = "x_..."
client_secret = "1..."
username = "user"
password = "lovesexsecretgod"
url = "https://wallabg.example.com"

# Global variables.
parameters = {}
headers = {}
request = None
token = None
data = {}

# Core code...
# If no URL was given, ABEND.
if len(sys.argv) < 2:
    sys.exit(1)

# Request a bearer token from Wallabag.
parameters["grant_type"] = "password"
parameters["client_id"] = client_id
parameters["client_secret"] = client_secret
parameters["username"] = username
parameters["password"] = password
try:
    request = requests.post(url + "/oauth/v2/token", data=parameters)
except:
    print("Unable to get bearer token.")
    sys.exit(1)
token = request.json()["access_token"]

# Shoot the URL over to Wallabag.
headers["Authorization"] = "Bearer " + token
data ["url"] = sys.argv[1]
try:
    request = requests.post(url + "/api/entries.json", data=data,
        headers=headers)
except:
    sys.exit(1)

# Fin.
sys.exit(0)
