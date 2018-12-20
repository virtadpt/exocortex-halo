#!/usr/bin/env bash

export VIRTUAL_ENV="$(pwd)/env"
export PATH=$VIRTUAL_ENV/bin:$PATH
export PS1="(virtualenv) $PS1"
unset PYTHON_HOME

exec "./system_bot.py"

exit 0
