When setting up the venv for the bot you're going to need the RPi.GPIO module, which doesn't seem to be easy to find in the Pypi repository but is in the default Raspbian package repositories.  But, you can make modules installed at the system level available inside of a venv, like so:

* `sudo apt-get install rpi.gpio-common`
    * This will probably be a NOP but I've documented it for anyone looking for answers.
* `python -mvenv env --system-site-packages`


