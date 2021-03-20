System Script is a bot (maybe bot-adjacent?) which implements system monitoring in as close a fashion as [Systembot](/system_bot) but without all of the dependencies.  The use case here is devices running [OpenWRT](https://openwrt.org/) which don't have the storage capacity for a Python install like the one Systembot needs.

It was designed specifically around [Busybox's](https://busybox.net/about.html) built in implementation of [ash](https://linux.die.net/man/1/ash), which is the default for just about every OpenWRT install out there.  This script only depends upon the [bc](https://www.gnu.org/software/bc/manual/html_mono/bc.html) command-line calculator utility, which can be installed with [the usual methods](https://openwrt.org/packages/start) in OpenWRT.  If it's not present System Script will error out.  This is due to the fact that pretty much every shell out there doesn't handle floating point values of any kind, but `bc` does, and can even do basic logic with them.

At present, System Script is not interactive.  I want to get basic monitoring functionality working first before I try to make the utility more complex.

System Script does not have any built-in way of getting alerts off-system.  It is designed to operate in the context of a separate messaging mechanism, be it a [cross-compiled](https://drwho.virtadpt.net/archive/2021-03-01/cross-compiling-go-sendxmpp/) copy of [go-sendxmpp](https://salsa.debian.org/mdosch/go-sendxmpp), a REST API like Prosody's [mod_rest](https://modules.prosody.im/mod_rest.html) with [cURL](https://curl.se/), Busybox's wget, [xmppcd](https://github.com/stanson-ch/xmppcd), or whatever other clever thing you might devise.  Please let me know what you come up with so I can add it to this file.

The to-do list is pretty long, so don't expect to get full functionality just yet.  Implemented at this time:

* Library functions
    * Calculation of the average of a list of numbers
    * Calculation of the standard deviation of a list of numbers
* Monitoring the one, five, and ten minute load averages
* Monitoring available space on all writable file systems mounted on the device
* Monitoring memory usage of the device

On the roadmap:

* Monitoring the temperature sensors in the device
* Config file support
* Command line options
* Interactive commands
* Alert cooldown so you don't get flooded with warnings every __n__ seconds

Default settings:

* Default number of samples averaged for each system metric: 10
* Time to sleep in between loops: 10 seconds
* Number of [standard deviations](https://www.mathsisfun.com/data/standard-deviation.html) which will trigger an alert: 2 sigma
* Disk space usage danger zone: 85% of capacity
* Memory usage danger zone: 85% of capacity

Installation

* Install the messaging utility of your choice.
* Install bc.
* Copy system-script.sh over to the system.
* `./system-script.sh | your-messaging-utility`
    * Set up automatic start at boot-time.
    * Set up "make sure this script stays up" measures if you need to.

