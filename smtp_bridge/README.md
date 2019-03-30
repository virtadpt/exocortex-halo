Please note: I've ported this code to [Python 3](https://pythonclock.org) because Python v2.x will not be maintained past 1 January 2020.ev.  Everything henceforce will be written with that assumption.

This is a bot which pretends to be an [SMTP server](https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol) insofar as things running on the box can try to send outbound e-mail through it, and as far as they're concerned they won't be able to distinguish it from, say, [Postfix](http://www.postfix.org).  The bot will accept the SMTP transmission but reformat it internally to extract only the salient bits and then forward them to the [Exocortex XMPP bridge](https://github.com/virtadpt/exocortex-halo/tree/master/exocortex_xmpp_bridge).  In situations where outbound SMTP is heavily restricted (usually in the case of most large ISPs), this will permit messages to be transmitted.

To facilitate this, the SMTP bridge must be started as the root user (because the default SMTP port is 25/tcp).  Once it's opened that port it will then drop privileges to those specified in the `smtp_bridge.conf` file, by default user "nobody," group "nobody" but any non-root user and group that exist on the machine will work.  By default, the SMTP bridge bot will only listen on the network loopback (127.0.0.1 or localhost), but you can change this in the config file.  Please note that this can potentially cause problems with spurious messages if the box is on an untrusted network, so think carefully before doing this.

This bot requires the [requests](http://docs.python-requests.org/en/master/) Python module.  I highly recommend installing it into a [venv](https://docs.python.org/3/tutorial/venv.html) to keep from splattering files all over your system.  Here's one way to do it (and, in fact, is the recommended and supported method):

* `cd exocortex_halo/smtp_bridge`
* `python3 -m venv env`
* `source env/bin/activate`
* `pip install -r requirements.txt`

You'll have to run `source env/bin/activate` every time you want to start the SMTP bridge.  I've included a shell script called `run.sh` which does this automatically for you.

As always, `smtp_bridge.py --help` will display the most current online help.

To create a config file, copy the `smtp_bridge.conf.example` file to `smtp_bridge.conf`, edit it with your favorite text editor, and save it.  The bridge will send everything through the XMPP bridge's **/requests** API rail, so you don't need to add a new message queue.

I haven't yet written and tested a systemd .service file, so please stand by.  Pull requests are gratefully accepted!
