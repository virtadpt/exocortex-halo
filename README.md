# exocortex-halo
Various and sundry additional pieces of software I've written to incorporate into my exocortex that extend the functionality of Huginn (https://github.com/cantino/huginn).  You never know what you're going to find in here because I do a lot of idiosyncratic stuff and as I get ideas for functionality to incorporate new things will appear in here.  Not all of them will make sense.

exocortex_gps_mapper/

A relatively simple web application that uses web.py (http://webpy.org/) to implement a REST API.  An application running on a smartphone periodically pings an endpoint with its current GPS coordinates.  Contacting the web app throws up a Google Map with the GPS coordinates.  It's far from complete because I don't know JavaScript.

exocortex_sip_client/

A command line application (mostly) that can be used to place calls into the PSTN via a Voice-Over-IP provider and play a .wav file into the call.  I designed it to work as part of a larger toolkit of utilities.  Requires PJSIP (http://www.pjsip.org/) (but NOT PJSUA) to implement SIP functionality.

Special thanks to The Test Call (http://thetestcall.blogspot.com/) for providing the default phone number for debugging.  I got kind of tired of rickrolling myself...

exocortex_xmpp_bridge/

A daemon that logs into an arbitrary XMPP server on one side, and connects to an arbitrary MQTT v3.1 broker on the other (I used Mosquitto http://mosquitto.org/ when developing but most any compliant MQTT broker that speaks v3.1 of the protocol should work.  The idea is that you should be able to send chat messages to the XMPP address the daemon logs into (it checks to see if they are from the bot's registered owner) and forward the contents of the messages to Huginn (https://github.com/cantino/huginn/) agents (MQTTagents in particular).  Basically, this is so you can send orders to Huginn agents to command them to do something.  It's a work a progress, a lot of the processing will have to be done in the Huginn agent networks themselves.

