#!/usr/bin/env bash

# run.sh - Shell script that wraps around dixie_flatline_bot.py if you had
#    to install it to a virtualenv like I did.  This script assumes that you
#    set up the virtualenv the way you're supposed to and didn't tinker with
#    the sandbox too much.  If you did, you're on your own.

# by: The Doctor [412/724/301/703/415][ZS] <drwho at virtadpt dot net>

# Variables
# Full path to where exocortex_sip_client.py is installed.
BOT_DIR="/path/to/irc_bot"

# Core code.
cd $BOT_DIR

# Bring in the virtualenv.  Imagine whatever sci-fi sound effects you wish
# as this happens.
source env/bin/activate

# Grab the first command line argument (which should be a number) and sleep
# that many seconds.  This is totally a yucky hack.
sleep $1
shift

# Call the bot with the remaining command line args.
python ./dixie_flatline_bot.py $@

# Clean up.
exit 0

# End of core code.

