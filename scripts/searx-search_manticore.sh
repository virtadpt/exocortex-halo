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

# URL of searchd's HTTP port.
SEARCHD="http://localhost:9308/search"

# Name of Manticore's index.
INDEX="articles"

# The search term from the user (by way of Searx).
QUERY="$@"

# Variables
# JSON template for search requests sent to Manticore's searchd.
# I can't say I expected to find a solution here, but any port in a storm.
# https://github.com/maxrooted/instashell/blob/master/instashell.sh#L140
SEARCH_REQUEST='
{
    "index": "'$INDEX'",
    "query": {
        "match_phrase": {
            "title,content": {
                "query": "'$QUERY'",
                "operator": "and"
            }
        }
    },
    "limit": 20,
    "offset": 0
}
'

# JSON of the search result, returned from searchd.
SEARCH_RESULT=''

# Captures the code curl exits with.
CURL_EXIT_CODE=0

# String that holds the meaning of the exit code.
CURL_EXIT_REASON=""

# Core code.
# Test for curl.
which curl 1>/dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: curl not installed."
    exit 1
fi

# Test for jq.
which jq 1>/dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: jq not installed."
    exit 1
fi

# Test the number of command line arguments passed to the script.
if [ $# -eq 0 ]; then
    echo "ERROR: No command line arguments found."
    exit 2
fi

# Send a search request to searchd.
# -f - Fail silently on server errors.
# -s - Run silently, no output other than what the server sends back.
# -X - HTTP POST method.
# -d - Payload (data) for the POST request.
SEARCH_RESULT=$(curl -f -s -X POST "$SEARCHD" -d "$SEARCH_REQUEST")
CURL_EXIT_CODE=$?

# Figure out what happened with curl.
if [ $CURL_EXIT_CODE -eq 7 ]; then
    CURL_EXIT_REASON="Unable to connect to searchd at $SEARCHD."
elif [ $CURL_EXIT_CODE -eq 8 ]; then
    CURL_EXIT_REASON="I have no idea what searchd returned."
elif [ $CURL_EXIT_CODE -eq 22 ]; then
    CURL_EXIT_REASON="HTTP error >=400 returned by searchd."
elif [ $CURL_EXIT_CODE -eq 28 ]; then
    CURL_EXIT_REASON="Connection to $SEARCHD timed out."
fi

# Define the error result now that we have the values that go into it.
ERROR_RESULT='
{
    "error_code": "'$CURL_EXIT_CODE'",
    "error": "'$CURL_EXIT_REASON'"
}
'

# Finally, if the exit code is non-zero, return the error and exit.
if [ $CURL_EXIT_CODE -gt 0 ]; then
    echo $ERROR_RESULT
    exit 1
fi

# If we made it this far, the query worked.  Output the search result so that
# Searx can pick it up and exit.
echo $SEARCH_RESULT

# Clean up.
exit 0

# End of core code.

