
This is a bot which accepts a handful of commands submitted via XMPP ("Botname, [temperature/temp, humidity, location, help].") and accesses a locally attached temperature and/or environment sensor for information as it currently understands it.  This is a prototype based upon the [AHT20 from Adafruit](https://www.adafruit.com/product/4566).  Eventually I'll build an embedded version but I wanted to make sure I could do it in an environment I'm more comfortable with first.  It was built with the [Blinka Python module](https://pypi.org/project/Adafruit-Blinka/) which implements a compatibility layer that lets you develop and run [Circuitpython](https://circuitpython.org/) code in a not-Circuitpython environment.

The strongly recommended and supported way to install this project's dependencies is inside a [Python virtualenv](https://docs.python-guide.org/dev/virtualenvs/), like so:

* `cd exocortex_halo/environment-sensor-raspbian/`
* `python3 -m venv env`
* `source env/bin/activate`
* `pip install --upgrade pip`
* `pip install -r requirements.txt`

You'll have to run `source env/bin/activate` every time you want to start the environment monitoring bot.  I've included a shell script called `run.sh` which does this automatically for you.

As always, `./environment-monitor.py --help` will display the most current online help.

Included a .service file (`environment_monitor.service`) in case you want to use [systemd](https://www.freedesktop.org/wiki/Software/systemd/) to manage your bots.  I've written the .service file specifically such that it can be run in [user mode](https://wiki.archlinux.org/index.php/Systemd/User) and will not require elevated permissions (though the account this bot runs under has to be in the group that owns the /dev/i2c-* device nodes; the bot will error out with a message telling you this if it's not).  Here is the process for setting it up and using it:

* `mkdir -p ~/.config/systemd/user/`
* `cp ~/exocortex-halo/environment-sensor-raspbian/environment_monitor.service ~/.config/systemd/user/`
* Configure the environment monitoring bot by making a copy of `environment-monitor.conf.example` to `environment-monitor.conf` and editing it.
* Configure the XMPP bridge by adding a new name to the list of message queues.
* Restart the XMPP bridge: `systemctl --user restart xmpp_bridge.service`
* Enable the environment monitoring bot prior to starting it: `systemctl --user enable environment_monitor.service`
* Starting the environment monitoring bot: `systemctl --user start environment_monitor.service`
  * You should see something like this if it worked:
```
[pi @ audra ~] (3) $ ps aux | grep [e]nvironment
pi        1865 30.1  3.2  24408 16028 pts/2    S+   15:22   0:03 python3 ./environment-monitor.py
```
* Ensure that systemd in --user mode will start on boot and run even when you're not logged in: `loginctl enable-linger <your username here>`
