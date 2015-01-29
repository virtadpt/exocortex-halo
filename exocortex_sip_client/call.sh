#!/usr/bin/env bash

# call.sh - Shell script that wraps around exocortex_sip_client.py if you had
#    to install it to a virtualenv like I did.  This script assumes that you
#    set up the virtualenv the way you're supposed to and didn't tinker with
#    the sandbox too much.  If you did, you're on your own.

# by: The Doctor [412/724/301/703/415][ZS] <drwho at virtadpt dot net>

# Variables
# Full path to where exocortex_sip_client.py is installed.
SIP_CLIENT_DIR="/home/drwho/exocortex_sip_client"

# Core code.
cd $SIP_CLIENT_DIR

# Bring in the virtualenv.  Imagine whatever sci-fi sound effects you wish
# as this happens.
source env/bin/activate

# Call the SIP client with the command line args.
./exocortex_sip_client.py $@

# Clean up.
exit 0

# End of core code.

