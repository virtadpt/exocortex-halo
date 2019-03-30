Please note: I've ported this code to [Python 3](https://pythonclock.org) because Python v2.x will not be maintained past 1 January 2020.ev.  Everything henceforce will be written with that assumption.

This is a bot which takes URLs submitted via XMPP ("Botname, download https://example.com/foo.pdf") and downloads it to the local server, putting it in a directory specified in the configuration file.  If you have a propensity to grab a lot of files to read later this is likely a useful tool for you.

This bot at a minimum requires the [requests](http://docs.python-requests.org/en/master/) Python module.  I highly recommend installing it into a [venv](https://docs.python.org/3/tutorial/venv.html) to keep from splattering files all over your file system.  Here's one way to do it (and, in fact, is the recommended and supported method):

* `cd exocortex_halo/download_bot`
* `python3 -m venv env`
* `source env/bin/activate`
* `pip install -r requirements.txt`

You'll have to run `source env/bin/activate` every time you want to start Download Bot.  I've included a shell script called `run.sh` which does this automatically for you.

If you have [youtube-dl](https://github.com/rg3/youtube-dl) for Python installed, you can use this bot to download any media stream Youtube-DL can download.  Here's how I did it:

* `cd exocortex_halo/download_bot`
* `python3 -m venv env` (if you haven't done this already)
* . env/bin/activate
* pip install youtube-dl
* python ./download_bot.py

As always, `./download_bot.py --help` will display the most current online help.

Included a .service file (`download_bot.service`) in case you want to use [systemd](https://www.freedesktop.org/wiki/Software/systemd/) to manage your bots.  Unlike supervisord, systemd can actually manage dependencies of system services, and as much as I find the service irritating it does a fairly decent job of this.  I've written the .service file specifically such that it can be run in [user mode](https://wiki.archlinux.org/index.php/Systemd/User) and will not require elevated permissions of any kind.  Here is the process for setting it up and using it:

* `mkdir -p ~/.config/systemd/user/`
* `cp ~/exocortex-halo/download_bot/download_bot.service ~/.config/systemd/user/`
* Configure the XMPP bridge by making a copy of `download_bot.conf.example` to `download_bot.conf` and editing it.
* Starting the XMPP bridge: `systemctl start --user download_bot.service`
  * You should see something like this if it worked:
```
[drwho@windbringer download_bot]$ ps aux | grep [d]ownload_bot
drwho     6039  0.1  0.1 459332 24572 ?        Ssl  14:15   0:06 python /home/drwho/exocortex-halo/download_bot/download_bot.py
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
