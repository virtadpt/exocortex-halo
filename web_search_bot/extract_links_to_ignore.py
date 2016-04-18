#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# This utility is used to help customize the web_search_bot.conf script to add
#   additional search engines to it.  It does this by running a web search and
#   capturing the HTML, parsing it to extract the hyperlinks, and then printing
#   them out.  The user must then figure out for themselves which ones they
#   want web_search_bot.py to ignore.
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:

# Load modules.
from bs4 import BeautifulSoup
from bs4 import SoupStrainer

import argparse
import requests
import sys

# Global variables.
# Handle to the command line argument parsr.
argparser = None

# Command line arguments.
args = None

# Handle to an HTTP request object.
request = None

# Handle to an HTML entity extractor customized for <a ...> constructs.
link_extractor = None

# Handle to parsed HTML.
html = None

# A list of all of the links extracted from the parsed HTML.
links = []

# A list of hyperlinks extracted from the parsed html.
hyperlinks = []

# Core code...
# Set up the command line argument parser.
argparser = argparse.ArgumentParser(description="This is a utility with which you can make a request of a search engine and figure out what links to populate the 'hyperlinks_we_dont_want' part of the web_search_bot.conf file with to expand the number of search engines that it can use.  Note that you may need to escape shell metacharacters (such as '?' or '&') to make this work as expected.")

# Add the one required command line option, the search term.
argparser.add_argument('--url', action='store', required=True,
    help="This is the URL of a search request to parse for its internal links.  This is mandatory and takes the form https://example.com/?q=foo+bar+baz")

# Verbose mode?
argparser.add_argument('--verbose', action='store_true', default=False,
    help="Verbose mode.")

# Parse the arguments.
args = argparser.parse_args()

# Set up the link extractor.
link_extractor = SoupStrainer('a')

# Make the search request and parse the HTML.
request = requests.get(args.url.strip())
html = BeautifulSoup(request.content, 'html.parser', parse_only=link_extractor)
if args.verbose:
    print "Downloaded HTML:"
    print html.prettify()
    print

# Extract all of the links (<a ...>) from the HTML.
links = html.find_all('a')
if args.verbose:
    print "Links extracted:"
    print str(links)
    print
for i in links:
    hyperlink = i.get("href")
    if not hyperlink:
        continue
    hyperlinks.append(hyperlink.strip())

# Unique-ify the hyperlinks to make life easier.
hyperlinks = list(set(hyperlinks))

# Display the found links.
print "Here are the hyperlinks extracted from the search results to consider:"
for i in hyperlinks:
    print i

# Fin.
sys.exit(0)

