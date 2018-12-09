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
