How to install PJSIP (http://www.pjsip.org/) into a virtualenv on a fairly recent Ubuntu Linux (virtual) machine:

* `sudo apt-get install python3-dev swig`
* `cd ~/exocortex-halo/exocortex_sip_client`
* `python -mvenv env`
* `source env/bin/activate`
* `mkdir src`
* `cd src`
* download pjproject: `wget http://www.pjsip.org/release/2.7.2/pjproject-2.7.2.tar.bz2`
* `tar xvfj pjproject-2.7.2.tar.bz2`
* `cd pjproject-2.7.2`
* `./configure CFLAGS="$CFLAGS -fPIC"`
* `make dep`
* `make`
* `DESTDIR=$VIRTUAL_ENV make install`
* `cd pjsip-apps/src`
* `git clone https://github.com/mgwilliams/python3-pjsip.git`
* `cd python3-pjsip`
* `python ./setup.py build`
* `python ./setup.py install --prefix=$VIRTUAL_ENV`
* Testing the Python 3 module you just installed:
  * `python3`
  * `import pjsua`
  * If it works, it should work.

https://www.spinics.net/lists/pjsip/msg20666.html

To use the SIP client you will have to activate the venv (source env/bin/activate).  This is done automatically by the shell script `call.sh`, and in fact is called by `exocortex_web_to_speech.py`.

To test everything edit exocortex_web_to_speech.py and set a value for API_KEY.  I like to use pwgen to output a string of 30 to 40 garbage characters.  Make sure you have Festival installed (`sudo apt-get install -y festival`) to provide speech synthesis capability and ensure that the value of GENERATE points to the location of text2wave (included in Festival).  Also make sure the value of the exocortex_sip_client variable points to the directory into which you've installed exocortex_sip_client.py, which could very well be a virtualenv as described above.  In the event you need to use it, call.sh will need to be edited to point to where exocortex_sip_client.py is installed, also.

Start up exocortex_web_to_speech.py:

    ./exocortex_web_to_speech.py 127.0.0.1 8080

Included is huginn_test_agent.json, a dump of a test agent running in my exocortex.  It's an instance of PostAgent.  To instantiate it allocate a new agent (Agents -> New Agent -> Type: PostAgent).  Hit the "Toggle View" link to switch to the full text editor.  Cut and paste the contents of huginn_test_agent.json into the full text editor and hit the Save button.  Do not set a schedule or a Source on it.  To run the agent click on the Actions dropdown, then hit Run.  Wait a minute or so for exocortex_sip_client to call you (assuming that you've configured it properly).
