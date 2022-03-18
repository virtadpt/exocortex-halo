#!/usr/bin/env bash

# searx-search_manticore.sh - A shell script that take search requests from
#   Searx's (https://github.com/searx/searx) command.py engine, builds a search
#   request specific to the Manticore search engine
#   (https://manticoresearch.com), and generates the kind of output that Searx
#   can parse.
#
#   Requires cURL (https://curl.se) and jq (https://stedolan.github.io/jq/).
#
#   The search term is everything passed on the command line that isn't the
#   filename.  Could be better, could certainly be worse.
#
#   Part of the Exocortex Halo project.
#       (https://github.com/virtadpt/exocortex-halo)

# by: The Doctor [412/724/301/703/415/510] (drwho at virtadpt dot net)
#	  PGP fingerprint: <7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1>

# TODO
# - Add `source`able config file support so that the script doesn't have to
#   be edited by the end user.
# - Add pagination support with a command line argument.

# Configuration variables
# Edit these as appropriate.
# Name of Manticore's index.
INDEX="articles"

# The search term from the user (by way of Searx).
QUERY=""

# Variables
# JSON template for search requests sent to Manticore's searchd.
SEARCH_REQUEST=""

SEARCH_RESULT=""

ERROR_RESULT=""

# Core code.
# Test for curl.
which curl
if [ $? -ne 0 ]; then
    echo "ERROR: curl not installed"
    exit 1
fi

# Test for jq.
which jq
if [ $? -ne 0 ]; then
    echo "ERROR: jq not installed"
    exit 1
fi

# Clean up.
exit 0

# End of core code.

# Subroutines
