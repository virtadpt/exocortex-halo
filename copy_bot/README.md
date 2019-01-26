This is a relatively simple bot which takes a copy command submitted via XMPP ("Botname, copy /foo/bar to /baz/quux") and copies the former file to the latter location (and new filename, optionally).  This seems like a fairly simple and dumb bot, and it is in many ways.  I wrote it as an example of a system utility bot, the uses of which are limited only to your imagination.

To install it you'll need to have the following Python modules available, either installed to the underlying system with native packages or installed into a virtualenv:

* [pyParsing](http://pyparsing.wikispaces.com/)
* [requests](http://docs.python-requests.org/en/master/)

To set up a virtualenv:

* virtualenv env
* source env/bin/activate
* pip install -r requirements.txt

I've included a `run.sh` script which will source the virtualenv and run system_bot.py for you.

As always, `copy_bot.py --help` will display the most current online help.

Included with the bot is a sample [supervisord](http://supervisord.org/) configuration file which will automatically start and manage the bot for you if you happen to be using it on your system.  It's much easier to wrangle than a huge .screenrc file, initscripts, or systemd service files.  If you want to use this file, install supervisord on the system, ideally from the default package repository (it's usually called **supervisor**).  Enable and start the supervisord service per your distribution's instructions.  Copy the **copy_bot.conf.supervisord** file as **copy_bot.conf** into your system's supervisord supplementary configuration file directory; on Raspbian this is */etc/supervisor/conf.d*.  Edit the file so that paths in the *command* and *directory* directives reflect where you checked out the source code.  Also set the *user* directive to the username that'll be running this bot (probably yourself).  For example, the */etc/supervisor/conf.d/copy_bot.conf* file on my test machine looks like this:

```[program:copybot]
command=/home/pi/exocortex-halo/copy_bot/run.sh
directory=/home/pi/exocortex-halo/copy_bot
startsecs=30
user=pi
redirect_stderr=true
process_name=copybot
startretries=0
```

Then tell supervisord to look for new configuration directives and automatically start anything it finds: **sudo supervisorctl update**

supervisord will read the new config file and start Systembot for you.

I've also included a .service file (`copy_bot.service`) in case you want to use [systemd](https://www.freedesktop.org/wiki/Software/systemd/) to manage your bots.  Unlike supervisord, systemd can actually manage dependencies of system services, and as much as I find the service irritating it does a fairly decent job of this.  I've written the .service file specifically such that it can be run in [user mode](https://wiki.archlinux.org/index.php/Systemd/User) and will not require elevated permissions of any kind.  Here is the process for setting it up and using it:

* `mkdir -p ~/.config/systemd/user/`
* `cp ~/exocortex-halo/copy_bot/copy_bot.service ~/.config/systemd/user/`
* You configure Copy Bot by making a copy of `copy_bot.conf.example` to `copy_bot.conf` and editing it.
* Starting the XMPP bridge: `systemctl start --user copy_bot.service`
  * You should see something like this if it worked:
```
[drwho@windbringer copy_bot]$ ps aux | grep [c]opy
drwho    11947  0.1  0.1  88980 21456 ?        Ss   15:32   0:00 python2 /home/drwho/exocortex-halo/copy_bot/copy_bot.py
```
* Setting Copy Bot to start automatically on system boot: `systemctl enable --user copy_bot.service`
  * You should see something like this if it worked:

```
[drwho@windbringer copy_bot]$ ls -alF ~/.config/systemd/user/default.target.wants/
total 8
drwxr-xr-x 2 drwho drwho 4096 Jan 26 14:16 ./
drwxr-xr-x 3 drwho drwho 4096 Jan 26 14:15 ../
lrwxrwxrwx 1 drwho drwho   52 Jan 26 14:16 copy_bot.service -> /home/drwho/.config/systemd/user/copy_bot.service
```

