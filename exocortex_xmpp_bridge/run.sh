#!/usr/bin/env bash

# run.sh - Shell script that wraps around exocortex_xmpp_bridge.py if you had
#    to install it to a virtualenv like I did.  This script assumes that you
#    set up the virtualenv the way you're supposed to and didn't tinker with
#    the sandbox too much.  If you did, you're on your own.

# by: The Doctor [412/724/301/703/415][ZS] <drwho at virtadpt dot net>

# Variables
# Full path to where exocortex_xmpp_bridge.py is installed.
SIP_CLIENT_DIR="/path/to/exocortex_xmpp_bridge/installation/dir"

# Core code.
cd $SIP_CLIENT_DIR

# Bring in the virtualenv.  Imagine whatever sci-fi sound effects you wish
# as this happens.
source env/bin/activate

# Run the XMPP-to-MQTT bridge with any appropriate command line args.
./exocortex_xmpp_bridge.py $@

# Clean up.
exit 0

