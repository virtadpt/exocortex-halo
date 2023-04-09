This bot was originally developed for running the [SEN-15901 weather meter kit from Sparkfun](https://www.sparkfun.com/products/15901) and the [BME280 sensor from Adafruit](https://www.adafruit.com/product/2652).

I've tried to make it as extensible as possible, because you might have used a different set of sensors to build your own weather station.

MOOF MOOF MOOF - here's the process for adding a module for adding a new sensor and the code to run it

When setting up the venv for the bot you're going to need the RPi.GPIO module, which doesn't seem to be easy to find in the Pypi repository but is in the default Raspbian package repositories.  But, you can make modules installed at the system level available inside of a venv, like so:

* `sudo apt-get install rpi.gpio-common`libatlas3-base
    * This will probably be a NOP but I've documented it for [anyone looking for answers](https://xkcd.com/979/).
* `python -mvenv env --system-site-packages`
* `. env/bin/activate`
* `pip install -r requirements.txt`

