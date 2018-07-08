Systembot is a bot which implements system monitoring of whatever machine it's running on.  It's still in its early stages (it shows, it's taken this long to write a README).

To install it you'll need to have the following Python modules available, either installed to the underlying system with native packages or installed into a virtualenv:

* [psutil](https://github.com/giampaolo/psutil)
* [pyParsing](http://pyparsing.wikispaces.com/)
* [requests](http://docs.python-requests.org/en/master/)

To set up a virtualenv:

* virtualenv env
* source env/bin/activate
* pip install -r requirements.txt

I've included a `run.sh` script which will source the virtualenv and run system_bot.py for you.

Right now, these are the system stats Systembot keeps tabs on, and how to access them:

* Get the bot's online help.
  * help
* Current system load:
  * <bot's name>, load.
  * <bot's name>, sysload.
  * <bot's name>, system load.
* System info:
  * <bot's name>, uname.
  * <bot's name>, info.
  * <bot's name>, system info.
* Number of CPUs on the system:
  * <bot's name>, cpus.
  * <bot's name>, CPUs.
* Amount of free disk space per device:
  * <bot's name>, disk.
  * <bot's name>, disk usage.
  * <bot's name>, storage.
* Amount of free system memory:
  * <bot's name>, memory.
  * <bot's name>, free memory.
  * <bot's name>, RAM.
  * <bot's name>, free ram.
* Current system uptime:
  * <bot's name>, uptime.
* Current public routable IP address:
  * <bot's name>, IP.
  * <bot's name>, IP address.
  * <bot's name>, public IP.
  * <bot's name>, IP addr.
  * <bot's name>, public IP address.
  * <bot's name>, addr.
* System's network traffic stats:
  * <bot's name>, network traffic.
  * <bot's name>, traffic volume.
  * <bot's name>, network stats.
  * <bot's name>, traffic stats.
  * <bot's name>, traffic count.

All of these commands (save the bot's name) are case insensitive.

Systembot automatically tracks the current system load, CPU idle time (per core), amount of free disk space remaining, and remaining unused RAM.  If any of these scores hit 20% left or less, an alert will automatically be sent to the bot's owner.  I have to be honest, this functionality isn't very good yet, it's unreliable and really needs a proper implementation but I haven't had time to come up with something that doesnt' suck.  It's on my to-do list.

This bot is also capable of optionally monitoring certain processes running on the system, specified in the configuration file.  If one or more of the processes is not found in the server's process table, it'll execute a command to restart it.  For example:

process1 = test_bot.py --loglevel,python2 /home/drwho/exocortex-halo/test_bot/test_bot.py --loglevel debug

This breaks down to "If the command `test_bot.py --loglevel` is not found in the process tbale, then run the command `python2 /home/drwho/exocortex-halo/test_bot/test_bot.py --loglevel debug`."  The command can be anything, not just a process restart.  Look at the sample configuration file for more details.

