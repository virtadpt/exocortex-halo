How to install PJSIP (http://www.pjsip.org/) into a virtualenv on a fairly recent Ubuntu Linux (virtual) machine:

* sudo apt-get install python2.7-dev
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

To use the SIP client you will have to activate the virtualenv (source env/bin/activate).  I recommend putting this into a shell script and using that to do the heavy lifting of running exocortex_sip_client.py.

