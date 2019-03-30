Please note: I've ported this code to [Python 3](https://pythonclock.org) because Python v2.x will not be maintained past 1 January 2020.ev.  Everything henceforce will be written with that assumption.

This is a relatively simple bot which takes a copy command submitted via XMPP ("Botname, copy /foo/bar to /baz/quux") and copies the former file to the latter location (and new filename, optionally).  This seems like a fairly simple and dumb bot, and it is in many ways.  I wrote it as an example of a system utility bot, the uses of which are limited only to your imagination.

To install it you'll need to have the following Python modules available, either installed to the underlying system with native packages or installed into a [venv](https://docs.python.org/3/tutorial/venv.html):

* [pyParsing](http://pyparsing.wikispaces.com/)
* [requests](http://docs.python-requests.org/en/master/)

To set up a venv:

* `cd exocortex_halo/copy_bot`
* `python3 -m venv env`
* `source env/bin/activate`
* `pip install -r requirements.txt`

I've included a `run.sh` script which will source the venv and run system_bot.py for you.

As always, `copy_bot.py --help` will display the most current online help.

I've included a .service file (`copy_bot.service`) in case you want to use [systemd](https://www.freedesktop.org/wiki/Software/systemd/) to manage your bots.  Unlike supervisord, systemd can actually manage dependencies of system services, and as much as I find the service irritating it does a fairly decent job of this.  I've written the .service file specifically such that it can be run in [user mode](https://wiki.archlinux.org/index.php/Systemd/User) and will not require elevated permissions of any kind.  Here is the process for setting it up and using it:

* `mkdir -p ~/.config/systemd/user/`
* `cp ~/exocortex-halo/copy_bot/copy_bot.service ~/.config/systemd/user/`
* Configure Copy Bot by making a copy of `copy_bot.conf.example` to `copy_bot.conf` and editing it.
* Starting the XMPP bridge: `systemctl start --user copy_bot.service`
  * You should see something like this if it worked:
```
[drwho@windbringer copy_bot]$ ps aux | grep [c]opy
drwho    11947  0.1  0.1  88980 21456 ?        Ss   15:32   0:00 python /home/drwho/exocortex-halo/copy_bot/copy_bot.py
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
* Ensure that systemd in --user mode will start on boot and run even when you're not logged in: `loginctl enable-linger <your username here>`
