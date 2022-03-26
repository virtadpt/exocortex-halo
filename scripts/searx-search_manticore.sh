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
SEARCH_RESULTS=''

# Core code.
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
SEARCH_RESULTS=$(curl -f -s -X POST "$SEARCHD" -d "$SEARCH_REQUEST")

# Sort the returned search hits by their relative ranking.
TMP=$(echo $SEARCH_RESULTS | jq '.hits.hits|=sort_by(-._score)')
SEARCH_RESULTS=$TMP
TMP=""

# MOOF MOOF MOOF
# Emit only X or fewer search results.
# This will require adding a feature to accept the maximum number of search
# results as a command line switch.  It also requires figuring out how to
# use search result paging.
TMP=$(echo $SEARCH_RESULTS | jq '.hits.hits | .[0:20]')
SEARCH_RESULTS=$TMP
TMP=""

# Format of search results:
# article_id;;;article_title;;;article_score;;;article_url
# I wish I could use JSON, but that requires Searx's json_engine.py, and that
# doesn't do HTTP POSTs.

# Loop through the retained search results, extract the bits we want from each
# one, and build a line of the search result to send back to Searx.
# jq -c: Every object jq emits is printed as a single line so that it will be
#   treated as a single item.
echo $SEARCH_RESULTS | jq '.[] | [(._id | tostring), ._source.title, (._score | tostring), ._source.url] | join(";;;")'

# Clean up.
exit 0

# End of core code.

