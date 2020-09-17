Similar to the [RaspberryPi version](/environment-sensor-raspbian), this is the firmware for building an ultra-tiny environment monitoring sensor out of an ESP8266 development board (I used a [Feather Huzzah 8266](https://www.adafruit.com/product/2821) from Adafruit), an AHT20 temperature and humidity sensor board ([also from Adafruit](https://www.adafruit.com/product/4566)), and optionally an OLED display (I developed with an SSD1306 based [Feather Wing OLED](https://www.adafruit.com/product/2900), also from Adafruit).  I soldered headers to the 8266, soldered the display onto the headers, and then soldered wires between the AHT20 and the power and I2C pins on the 8266.  I really should write a buildlog for this, but for now look at the pinouts.  It's not terribly difficult if you have some experience building electronic kits.

At the moment, this project carries out the following tasks:

* Associate with a wireless network (802.11 b, g, n)
* Take temperature and relative humidity readings every couple of seconds
* Display the readings on the on-board OLED display

If configured, the sensor code can contact an arbitrary URL with the value of an "Authorization" HTTP request header to send periodic measurements to.  Right now, the monitoring software in `main.py` is hardcoded to send a measurement packet to a
webhook not more often than every 60 seconds.  I need to figure out a better way of doing this, but for now it works.

The schema of the measurement packet looks like this:

```
{
    "stats": {
        "temperature": 93.0,
        "humidity": 23,
        "scale": "f"
    }
}
```

The code in this repository uses the built in ssd1306 module that is part of the Micropython ESP8266 firmware image.

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
* Cycle power on the sensor by unplugging it and plugging it back in.
* After a few seconds, the display will show text as it tries to get on the wireless network you set in `config.py` (remember: The 8266 can only do wifi b, g, and n, so make sure you set the right ESSID!)
* After the sensor is on the wireless network, it'll initialize the AHT20 sensor and display the current temperature and relative humidity every couple of seconds.

Included in this repository is a [sample webhook agent](sample_huginn_webhook_agent.json) for [Huginn](https://github.com/huginn/huginn) which can accept measurements from sensors running this software.

