Similar to the [RaspberryPi version](/environment-sensor-raspbian), this is the firmware for building an ultra-tiny environment monitoring sensor out of an ESP8266 development board (I used a [Feather Huzzah 8266](https://www.adafruit.com/product/2821) from Adafruit), an AHT20 temperature and humidity sensor board ([also from Adafruit](https://www.adafruit.com/product/4566)), and optionally an OLED display (I developed with an SSD1306 based [Feather Wing OLED](https://www.adafruit.com/product/2900), also from Adafruit).  I soldered headers to the 8266, soldered the display onto the headers, and then soldered wires between the AHT20 and the power and I2C pins on the 8266.  I really should write a buildlog for this, but for now look at the pinouts.  It's not terribly difficult if you have some experience building electronic kits.

At the moment, this project carries out the following tasks:

* Associate with a wireless network (802.11 b, g, n)
* Take temperature and relative humidity readings every couple of seconds
* Display the readings on the on-board OLED display

On the development roadmap:

* Send the temperature and relative humidity readings to a [webhook](https://en.wikipedia.org/wiki/Webhook) for processing.

To drive the display, this repository has a copy of Adafruit's [SSD 1306 module for Micropython](https://github.com/adafruit/micropython-adafruit-ssd1306) included with it.  The driver module itself has been checked into this repository because the Git repository has been archived, which means that it could go away without warning.  At the moment I haven't made it optional yet, but that's on the roadmap.

Why [Micropython](https://micropython.org/)?  Circuitpython [no longer supports](https://learn.adafruit.com/welcome-to-circuitpython/circuitpython-for-esp8266) the ESP8266.

How to use:

* Build the environment sensor.
* [Install Micropython](https://docs.micropython.org/en/latest/esp8266/tutorial/intro.html) on the ESP8266.
* [Install ampy](https://github.com/scientifichackers/ampy) on your workstation if you haven't yet.
  * ampy is a serial communications utility for manipulating the local filestore of microcontrollers, kind of like using cURL for FTP.
  * If you're logged into the ESP8266 with a serial package, you won't be able to use ampy until you disconnect.  You can't share serial ports on Linux, apparently.
* (optional) Install a communications package like [Picocom](https://github.com/npat-efault/picocom) on your workstation to communicate interactively with the ESP8266.
* Plug your ESP8266 into your workstation.
  * It'll probably show up on your workstation as `/dev/ttyUSB0`
  * To check: `ls -ltr /dev | tail`
  * Dynamically allocated devices (like USB devices) will always be the newest files in /dev, and will show up last.
* Make a copy of the sample config file: `cp config.py.example config.py`
* Edit the config file appropriately.  At the very least, set the wireless settings.
* Upload the Python files to the ESP8266:
  * `ampy --port /dev/ttyUSB0 put boot.py`
  * `ampy --port /dev/ttyUSB0 put config.py`
  * `ampy --port /dev/ttyUSB0 put main.py`
  * `ampy --port /dev/ttyUSB0 put ssd1306.py`
* Cycle power on the sensor by unplugging it and plugging it back in.
* After a few seconds, the display will show text as it tries to get on the wireless network you set in `config.py` (remember: The 8266 can only do wifi b, g, and n, so make sure you set the right ESSID!)
* After the sensor is on the wireless network, it'll initialize the AHT20 sensor and display the current temperature and relative humidity every couple of seconds.
