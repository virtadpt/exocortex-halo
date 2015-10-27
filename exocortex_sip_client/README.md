How to install PJSIP (http://www.pjsip.org/) into a virtualenv on a fairly recent Ubuntu Linux (virtual) machine:

* sudo apt-get install python2.7-dev
* mkdir exocortex_sip_client
* cd exocortex_sip_client
* virtualenv2 env
* source env/bin/activate
* mkdir src
* cd src
* download pjproject: wget http://www.pjsip.org/release/2.3/pjproject-2.3.tar.bz2
* tar xvfj pjproject-2.3.tar.bz2
* cd pjproject-2.3
* ./configure CFLAGS="$CFLAGS -fPIC"
* make
* cd pjsip-apps/src/python
* sed "s/python/python2/" -i Makefile
* make
* python2 ./setup.py install --prefix=$VIRTUAL_ENV

To use the SIP client you will have to activate the virtualenv (source env/bin/activate).  I've put this into a shell script (call.sh) which'll make it easier to use, and in fact it'll probably be necessary to call it from exocortex_web_to_speech.py.

To test everything edit exocortex_web_to_speech.py and set a value for API_KEY.  I like to use pwgen to output a string of 30 to 40 garbage characters.  Make sure you have Festival installed (`sudo apt-get install -y festival`) to provide speech synthesis capability and ensure that the value of GENERATE points to the location of text2wave (included in Festival).  Also make sure the value of the exocortex_sip_client variable points to the directory into which you've installed exocortex_sip_client.py, which could very well be a virtualenv as described above.  In the event you need to use it, call.sh will need to be edited to point to where exocortex_sip_client.py is installed, also.

Start up exocortex_web_to_speech.py:

    ./exocortex_web_to_speech.py 127.0.0.1 8080

Included is huginn_test_agent.json, a dump of a test agent running in my exocortex.  It's an instance of PostAgent.  To instantiate it allocate a new agent (Agents -> New Agent -> Type: PostAgent).  Hit the "Toggle View" link to switch to the full text editor.  Cut and paste the contents of huginn_test_agent.json into the full text editor and hit the Save button.  Do not set a schedule or a Source on it.  To run the agent click on the Actions dropdown, then hit Run.  Wait a minute or so for exocortex_sip_client to call you (assuming that you've configured it properly).

