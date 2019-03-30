Please note: I've ported this code to [Python 3](https://pythonclock.org) because Python v2.x will not be maintained past 1 January 2020.ev.  Everything henceforce will be written with that assumption.

This is a relatively simple bot that accepts web search requests via the [XMPP bridge](https://github.com/virtadpt/exocortex-halo/tree/master/exocortex_xmpp_bridge) and are executed by an instance of Searx (https://github.com/asciimoo/searx) defined in `web_search_bot.conf`.  For example, "Botname, top twenty hits for porting python 2 to python 3."

You can use a [public installation](https://github.com/asciimoo/searx/wiki/Searx-instances) of Searx or [install your own](https://asciimoo.github.io/searx/dev/install/installation.html), but if you do but don't bother with uwsgi or putting it behind a reverse proxy; just have it listen on 127.0.0.1 on some port you're not using (8888/tcp by default).

web_search_bot.py can also e-mail search results to an address specified in the command.  For example, "<agent>, send you@example.com top twenty hits for porting python 2 to python 3."

web_search_bot.py currently only supports up to fifty (50) search results.  Specifying an invalid number causes it to default to ten (10).

To install this bot you'll need to have the following Python modules available, either installed to the underlying system with native packages or installed into a [venv](https://docs.python.org/3/tutorial/venv.html):

* [pyParsing](http://pyparsing.wikispaces.com/)
* [requests](http://docs.python-requests.org/en/master/)

To set up a venv:

* `cd exocortex_halo/web_search_bot`
* `python3 -m venv env`
* source env/bin/activate
* pip install -r requirements.txt

The `run.sh` script will source the venv and run system_bot.py for you.

I've included a .service file (`web_search_bot.service`) in case you want to use [systemd](https://www.freedesktop.org/wiki/Software/systemd/) to manage your bots.  I've written the .service file specifically such that it can be run in [user mode](https://wiki.archlinux.org/index.php/Systemd/User) and will not require elevated permissions of any kind.  Here is the process for setting it up and using it:

* `mkdir -p ~/.config/systemd/user/`
* `cp ~/exocortex-halo/web_search_bot/web_search_bot.service ~/.config/systemd/user/`
* You configure the XMPP bridge by making a copy of `web_search_bot.conf.example` to `web_search_bot.conf` and editing it.
* Starting the XMPP bridge: `systemctl start --user web_search_bot.service`
  * You should see something like this if it worked:
```
[drwho@windbringer web_search_bot]$ ps aux | grep [w]eb_search
drwho     6039  0.1  0.1 459332 24572 ?        Ssl  14:15   0:06 python /home/drwho/exocortex-halo/web_search_bot/web_search_bot.py
```
* Setting the web search bot to start automatically on system boot: `systemctl enable --user web_search_bot.service`
  * You should see something like this if it worked:

```
[drwho@windbringer web_search_bot]$ ls -alF ~/.config/systemd/user/default.target.wants/
total 8
drwxr-xr-x 2 drwho drwho 4096 Jan 26 14:16 ./
drwxr-xr-x 3 drwho drwho 4096 Jan 26 14:15 ../
lrwxrwxrwx 1 drwho drwho   52 Jan 26 14:16 web_search_bot.service -> /home/drwho/.config/systemd/user/web_search_bot.service
```
* Ensure that systemd in --user mode will start on boot and run even when you're not logged in: `loginctl enable-linger <your username here>`
