# Modules for basic operation of the sensor.
import machine
import ssd1306
import time

from machine import I2C

# Pull in the config file.
import config

# Initialize the I2C bus.
i2c = I2C(sda=machine.Pin(4), scl=machine.Pin(5))
i2c.scan()

# Repeating documentation from boot.py
# I2C addresses are assigned by manufacturers so they're static.  When scanning
# the I2C bus you get decimal values, but everyone else refers to them as hex
# values.  So...
# i2c.scan() value      hex value      device
# ----------------      ---------      ------
# I2C address 56        0x38           AHT20 temperature/humidity sensor
# I2C address 60        0x3c           SSD1306 monochrome OLED


# Blank the display.

# Okay, let's do this.
while True

    time.sleep(config.delay)
