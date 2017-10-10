#!/usr/bin/env bash

# run.sh - Shell script that wraps around server.py if you installed it into
#    into a virtualenv like I did.  This script assumes that you set up the
#    virtualenv the way you're supposed to and didn't tinker with the sandbox
#    too much.  If you did, you're on your own.

# by: The Doctor [412/724/301/703/415] <drwho at virtadpt dot net>

# Core code.
# Activate in the virtualenv.  Imagine whatever sci-fi sound effects you wish
# as this happens.
source env/bin/activate

# Grab the first command line argument (which should be a number) and sleep
# that many seconds.  This is totally a yucky hack but needed under some
# circumstances.
sleep $1
shift

# Call the discussion engine bot with the remaining command line args.
python ./server.py $@

# Clean up.
exit 0

# End of core code.

