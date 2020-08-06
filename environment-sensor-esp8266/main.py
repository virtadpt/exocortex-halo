# print() statements are for serial terminal debugging.

# Modules for basic operation of the sensor.
import machine
import ssd1306
import sys
import time

from machine import I2C

# Pull in the config file.
import config

# Generic response to hardware call variable.  We need to be careful with
# memory usage.
response = None

# Status from the I2C device.
status = None

# Initialize the I2C bus.
i2c = I2C(sda=machine.Pin(4), scl=machine.Pin(5))
response = i2c.scan()
print("I2C devices found on the bus: %s" % response)

# Repeating documentation from boot.py
# I2C addresses are assigned by manufacturers so they're static.  When scanning
# the I2C bus you get decimal values, but everyone else refers to them as hex
# values.  So...
# i2c.scan() value      hex value      device
# ----------------      ---------      ------
# I2C address 56        0x38           AHT20 temperature/humidity sensor
# I2C address 60        0x3c           SSD1306 monochrome OLED

# I2C devices' bus addresses are hardwired and standardized, so we don't
# necessarily have to worry about this changing.  Making it a constant makes
# the code more literate.
aht20_device_id = 0x38

# I2C bus status bytes are standardized, also.
status_busy = b'\x80'
status_calibrated = b'\x08'

# I2C commands, as constants to make them easier to work with (and document

# Status from the I2C device.# them).
reset_command = b'\xba'
calibrate_command = b'\xe1\x08\x00'
read_command = b'\xac'

# Reset the AHT20 device.
response = None
response = i2c.writeto(aht20_device_id, reset_command)
time.sleep(config.delay)
if response:
    print("I2C device %s has been successfully reset." % (aht20_device_id))
else:
    print("I2C device %s was not successfully reset." % (aht20_device_id))
    sys.exit(1)

# Calibrate the AHT20 sensor.
response = None
response = i2c.writeto(aht20_device_id, calibrate_command)
print("Value of response: %s" % response)

# We do this in a loop because it can take a while.
while True:
    status = i2c.readfrom(aht20_device_id, 1)

    # If the device is still running its calibration sequence, let it.
    if status == status_busy:
        print("Calibration sequence running.")
        time.sleep(config.delay)
        continue

    # If the device is done calibrating itself, bounce.
    if status == status_calibrated:
        # Do something on the display here.
        print("The device is now calibrated: %s" % status)
        break

    # If the device returned an undocumented value, ABEND.
    # Do something on the display here.
    print("I have no idea what happened.  Returned status: %s" % status)
    sys.exit(1)

# Blank the display.

# Okay, let's do this.
while True
    
    time.sleep(config.delay)
