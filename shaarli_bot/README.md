This is a bot which takes search requests submitted via XMPP ("Botname, search for open source transhumanist projects.") and runs them against a [Shaarli](https://github.com/shaarli/Shaarli) instance specified in the configuration file.  Shaarli is a very flexible tool that can be used for more than just bookmarking hyperlinks: It can be used for note-taking, as a linkblog, or even a [card catalogue](https://en.wikipedia.org/wiki/Library_catalog) for a media collection.

You will need to enable the Shaarli [REST API](https://shaarli.github.io/api-documentation/) for this bot to work:

* Log into Shaarli.
* Tools -> Configure your Shaarli
* Check "Enable REST API"
* Type a value (ideally, randomly generated) into the "API secret" field to serve as an API key.
* Save.

This bot requires the following Python modules which, if you they aren't available in your distro's default package repo (they are in Ubuntu v14.04 Server LTS) you'll have to install on your own.  The modules are:

* [pyJWT](https://github.com/jpadilla/pyjwt)
* [pyParsing](http://pyparsing.wikispaces.com/)
* [requests](http://docs.python-requests.org/en/master/)

If they're not I highly recommend installing them into a [venv](https://docs.python.org/3/tutorial/venv.html) to keep from splattering them all over your file system.  Here's one way to do it (and, in fact, is the recommended and supported method):

* `cd exocortex_halo/shaarli_bot`
* `python3 -m venv env`
* `source env/bin/activate`
* `pip install -r requirements.txt`

Included is a `run.sh` shell script which automates starting up `kodi_bot.py`.

As always, `shaarli_bot.py --help` will display the most current online help.

To create a config file, copy the `shaarli_bot.conf.example` file to `shaarli_bot.conf`, edit it with your favorite text editor, and save it.  When you give your bot a name, you'll need to reconfigure the XMPP bridge and add that name to the `agents` line so there will be a message bridge for it to take orders from.

Included with the bot is a sample [systemd](https://freedesktop.org/wiki/Software/systemd/) .service file which will automatically start and manage the bot for you if you want.  It's much easier to wrangle than a huge .screenrc file or initscripts.  I've written the .service file specifically such that it can be run in [user mode](https://wiki.archlinux.org/index.php/Systemd/User) and will not require elevated permissions of any kind.  If you want to use this file, you must have installed the bot's dependencies in a virtualenv and created a config file, then follow this procedure:

* `mkdir -p $HOME/.config/systemd/user/`
* `cp exocortex-halo/shaarli_bot/shaarli_bot.service $HOME/.config/systemd/user/`
* Start Shaarlibot: `systemctl --user start shaarli_bot.service`
  * You should see something like this if it worked:
```
[drwho@windbringer shaarli_bot]$ ps aux | grep [s]haarli_bot
4242 ?        Ss     0:00 python /home/drwho/exocortex-halo/shaarli_bot/shaarli_bot.py
```
* Enable Shaarlibot on boot: `systemctl --user enable shaarli_bot.service`
  * You should see something like this if it worked:
```
[drwho@windbringer download_bot]$ ls -alF ~/.config/systemd/user/default.target.wants/
total 8
drwxr-xr-x 2 drwho drwho 4096 Jan 26 14:16 ./
drwxr-xr-x 3 drwho drwho 4096 Jan 26 14:15 ../
lrwxrwxrwx 1 drwho drwho   52 Jan 26 14:16 download_bot.service -> /home/drwho/.config/systemd/user/download_bot.service
```
* Ensure that systemd in --user mode will start on boot and run even when you're not logged in: `loginctl enable-linger <your username here>`
