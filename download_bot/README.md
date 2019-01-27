This is a bot which takes URLs submitted via XMPP ("Botname, download https://example.com/foo.pdf") and tries to download it to the local server, putting it in a directory specified in the configuration file.  If you have a propensity to grab a lot of files to read later this is likely a useful tool for you.

As always, `download_bot.py --help` will display the most current online help.

If you have [youtube-dl](https://github.com/rg3/youtube-dl) for Python2 installed, you can use this bot to download any media stream Youtube-DL can download.  Here's how I did it:

```
cd exocortex-halo/download_bot
virtualenv2 env
. env/bin/activate
pip install youtube-dl
pip install requests
python ./download_bot.py
```

Includes is a `run.sh` shell script which automates starting up download_bot.py somewhat if you're using a virtualenv.  It requires that you called your virtualenv `env` and you created it inside of the download_bot/ directory.  Please see the contents of the shell script for more details (of which there are few - I tried to keep it as short and simple as I could).

Included with the bot is a sample [supervisord](http://supervisord.org/) configuration file which will automatically start and manage the bot for you if you happen to be using it on your system.  It's much easier to wrangle than a huge .screenrc file, initscripts, or systemd service files.  If you want to use this file, install supervisord on the system, ideally from the default package repository (it's usually called **supervisor**).  Enable and start the supervisord service per your distribution's instructions.  Copy the **download_bot.conf.supervisord** file as **download_bot.conf** into your system's supervisord supplementary configuration file directory; on Raspbian this is */etc/supervisor/conf.d*.  Edit the file so that paths in the *command* and *directory* directives reflect where you checked out the source code.  Also set the *user* directive to the username that'll be running this bot (probably yourself).  For example, the */etc/supervisor/conf.d/downloadbot.conf* file on my test machine looks like this:

```[program:downloadbot]
command=/home/pi/exocortex-halo/download_bot/run.sh
directory=/home/pi/exocortex-halo/download_bot
startsecs=30
user=pi
redirect_stderr=true
process_name=downloadbot
startretries=0
```

Then tell supervisord to look for new configuration directives and automatically start anything it finds: **sudo supervisorctl update**

supervisord will read the new config file and start Downloadbot for you.

I've also included a .service file (`download_bot.service`) in case you want to use [systemd](https://www.freedesktop.org/wiki/Software/systemd/) to manage your bots.  Unlike supervisord, systemd can actually manage dependencies of system services, and as much as I find the service irritating it does a fairly decent job of this.  I've written the .service file specifically such that it can be run in [user mode](https://wiki.archlinux.org/index.php/Systemd/User) and will not require elevated permissions of any kind.  Here is the process for setting it up and using it:

* `mkdir -p ~/.config/systemd/user/`
* `cp ~/exocortex-halo/download_bot/download_bot.service ~/.config/systemd/user/`
* You configure the XMPP bridge by making a copy of `download_bot.conf.example` to `download_bot.conf` and editing it.
* Starting the XMPP bridge: `systemctl start --user download_bot.service`
  * You should see something like this if it worked:
```
[drwho@windbringer download_bot]$ ps aux | grep [d]ownload_bot
drwho     6039  0.1  0.1 459332 24572 ?        Ssl  14:15   0:06 python2 /home/drwho/exocortex-halo/download_bot/download_bot.py
```
* Setting Download Bot to start automatically on system boot: `systemctl enable --user download_bot.service`
  * You should see something like this if it worked:

```
[drwho@windbringer download_bot]$ ls -alF ~/.config/systemd/user/default.target.wants/
total 8
drwxr-xr-x 2 drwho drwho 4096 Jan 26 14:16 ./
drwxr-xr-x 3 drwho drwho 4096 Jan 26 14:15 ../
lrwxrwxrwx 1 drwho drwho   52 Jan 26 14:16 download_bot.service -> /home/drwho/.config/systemd/user/download_bot.service
```

