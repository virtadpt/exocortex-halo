
This bot was originally developed for running the [SEN-15901 weather meter kit from Sparkfun](https://www.sparkfun.com/products/15901) and the [BME280 sensor from Adafruit](https://www.adafruit.com/product/2652).  I eventually want to make it modular, so that anybody can build a weather station using their own choice of sensors, copy a couple of template files, and (relatively) easily write their own modules to pull usable data from them.

It's a process, okay?

The computer used as the core of my weather station is a Raspberry Pi 2B+, which is why it's unavoidably GPIO-centric (with the odd SMI interface).  It may be possible to interface with devices using something like [Adafruit's FT232H breakout board](https://www.adafruit.com/product/2264) but I don't have one and haven't tried.

When setting up the venv for the bot on a RasPi you're going to need the `RPi.GPIO` module, which doesn't seem to be easy to find in the Pypi repository but is in the default Raspbian package repositories.  You will need to make Python modules installed at the system level available inside of the venv, like so:

* `sudo apt-get install rpi.gpio-common libatlas-base-dev
    * This will probably be a NOP but I've documented it for [anyone looking for answers](https://xkcd.com/979/).
* `python -mvenv env --system-site-packages`
* `. env/bin/activate`
* `pip install -r requirements.txt`

You'll have to run `source env/bin/activate` every time you want to start the environment monitoring bot.  I've included a shell script called `run.sh` which does this automatically for you.

As always, `./weather-station-bot.py --help` will display the most current online help.

Included is a .service file (`weather_station_bot.service`) in case you want to use [systemd](https://www.freedesktop.org/wiki/Software/systemd/) to manage your bots.  I've written the .service file specifically such that it can be run in [user mode](https://wiki.archlinux.org/index.php/Systemd/User) and will not require elevated permissions.  Here is the process for setting it up and using it:

* `mkdir -p ~/.config/systemd/user/`
* `cp ~/exocortex-halo/weather_station_bot/weather_station_bot.service ~/.config/systemd/user/`
* Configure the bot by making a copy of `weather_station_bot.conf.example` to `weather_station_bot.conf` and editing it.
* Configure the XMPP bridge by adding a new name to the list of message queues.
* Restart the XMPP bridge: `systemctl --user restart xmpp_bridge.service`
* Enable the environment monitoring bot prior to starting it: `systemctl --user enable weather_station_bot.service`
* Starting the environment monitoring bot: `systemctl --user start weather_station_bot.service`
  * You should see something like this if it worked:
```
[pi @ clavicula ~] (3) $ ps aux | grep [w]eather
pi        9989  0.7  5.1 109720 50928 pts/3    Sl+  16:35   0:35 python3 ./weather_station_bot.py
```
* Ensure that systemd in --user mode will start on boot and run even when you're not logged in: `loginctl enable-linger <your username here>`

At present, Weather Bot includes the following modules:
* `file_writer`, which once a cycle writes the last set of readings collected to a text file, set in the configuration file with the option `write_file` and `write_file_seconds`.  Please note that both settings are required to enable this module; if either is not set the module will be disabled.  This is done out of consideration for very small systems.  Also, please note that writes to the file are not cumulative; the file is deleted and rewritten at the bottom of each cycle.
* `influxdb` - `pip install influxdb-client[ciso]`

