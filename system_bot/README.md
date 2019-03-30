Please note: I've ported this code to [Python 3](https://pythonclock.org) because Python v2.x will not be maintained past 1 January 2020.ev.  Everything henceforce will be written with that assumption.

Systembot is a bot which implements system monitoring of whatever machine it's running on.

To install it you'll need to have the following Python modules available, either installed to the underlying system with native packages or installed into a [venv](https://docs.python.org/3/tutorial/venv.html):

* [psutil](https://github.com/giampaolo/psutil)
* [pyParsing](http://pyparsing.wikispaces.com/)
* [requests](http://docs.python-requests.org/en/master/)
* [statistics](https://github.com/digitalemagine/py-statistics)

To set up a venv:

* `cd exocortex_halo/system_bot`
* `python3 -m venv env`
* source env/bin/activate
* pip install -r requirements.txt

I've included a `run.sh` script which will source the venv and run system_bot.py for you.

These are the system attributes Systembot monitors, and how to query them:

* Get the bot's online help.
  * <bot's name>, help
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
* Amount of disk space free per device:
  * <bot's name>, disk.
  * <bot's name>, disk usage.
  * <bot's name>, storage.
* Amount of system memory free:
  * <bot's name>, memory.
  * <bot's name>, free memory.
  * <bot's name>, RAM.
  * <bot's name>, free ram.
* System uptime:
  * <bot's name>, uptime.
* Current public routable IP address:
  * <bot's name>, IP address.
  * <bot's name>, public IP.
  * <bot's name>, IP addr.
  * <bot's name>, public IP address.
  * <bot's name>, addr.
* Current internal or local IP address:
  * <bot's name>, IP.
  * <bot's name>, local IP.
  * <bot's name>, local addr.
* System's network traffic stats:
  * <bot's name>, network traffic.
  * <bot's name>, traffic volume.
  * <bot's name>, network stats.
  * <bot's name>, traffic stats.
  * <bot's name>, traffic count.
* System hardware temperature:
  * <bot's name>, system temperature.
  * <bot's name>, system temp.
  * <bot's name>, temperature.
  * <bot's name>, temp.
  * <bot's name>, overheating.
  * <bot's name>, core temperature.
  * <bot's name>, core temp.

All of these commands (save the bot's name) are case insensitive.

Danger levels of system attributes are defined in the `system_bot.conf` file, and default to the following percentages of maximum:

* Disk usage: 90%
* Memory free: 15%
* Number of [standard deviations](https://www.mathsisfun.com/data/standard-deviation.html) of change between samples: 2 sigma
* Minimum lengths of sample [FIFO queues](https://en.wikipedia.org/wiki/FIFO_(computing_and_electronics)): 2
* Maximum lengths of sample [FIFO queues](https://en.wikipedia.org/wiki/FIFO_(computing_and_electronics)): 100

Systembot also automatically tracks temperatures reported by the hardware, if sensors are available.  If the sensors have an idea of high or critical temperatures (some do, some don't, this is a feature of the mainboard), a notification will be automatically sent to the user.  If the sensors do not, Systembot will automatically analyze device temperature trends and send an alert if something changes more than the number of standard deviations in the configuration file (default: 2 sigma).  If Systembot is running on a virtual machine (which typically don't expose hardware sensors) or the bot isn't able to access those device nodes for some reason, it will silently skip them.

This bot is also capable of optionally monitoring certain processes running on the system, specified in the configuration file.  If one or more of the processes is not found in the server's process table, it'll execute a command to restart it.  For example:

process1 = test_bot.py --loglevel,python /home/drwho/exocortex-halo/test_bot/test_bot.py --loglevel debug

This breaks down to "If the command `test_bot.py --loglevel` is not found in the process table, then run the command `python /home/drwho/exocortex-halo/test_bot/test_bot.py --loglevel debug`."  The command can be anything, not just a process restart.  Look at the sample configuration file for more details.

Included is a .service file (`system_bot.service`) in case you want to use [systemd](https://www.freedesktop.org/wiki/Software/systemd/) to manage your bots.  I've written the .service file specifically such that it can be run in [user mode](https://wiki.archlinux.org/index.php/Systemd/User) and will not require elevated permissions of any kind.  Here is the process for setting it up and using it:

* `mkdir -p ~/.config/systemd/user/`
* `cp ~/exocortex-halo/system_bot/system_bot.service ~/.config/systemd/user/`
* Configure Systembot by making a copy of `system_bot.conf.example` to `system_bot.conf` and editing it.
* Starting Systembot: `systemctl start --user system_bot.service`
  * You should see something like this if it worked:
```
[drwho@windbringer system_bot]$ ps aux | grep [s]ystem
drwho     6039  0.1  0.1 459332 24572 ?        Ssl  14:15   0:06 python /home/drwho/exocortex-halo/system_bot/system_bot.py
```
* Setting Systembot to start automatically on system boot: `systemctl enable --user system_bot.service`
  * You should see something like this if it worked:

```
[drwho@windbringer system_bot]$ ls -alF ~/.config/systemd/user/default.target.wants/
total 8
drwxr-xr-x 2 drwho drwho 4096 Jan 26 14:16 ./
drwxr-xr-x 3 drwho drwho 4096 Jan 26 14:15 ../
lrwxrwxrwx 1 drwho drwho   52 Jan 26 14:16 system_bot.service -> /home/drwho/.config/systemd/user/system_bot.service
```
* Ensure that systemd in --user mode will start on boot and run even when you're not logged in: `loginctl enable-linger <your username here>`
