This is a bot which takes URLs submitted via XMPP ("Botname, download https://example.com/foo.pdf") and tries to download it to the local server, putting it in a directory specified in the configuration file.  If you have a propensity to grab a lot of files to read later this is likely a useful tool for you.

As always, `download_bot.py --help` will display the most current online help.

If you have [youtube-dl](https://github.com/rg3/youtube-dl) for Python2 installed, you can use this bot to download any media stream Youtube-DL can download.  Here's how I did it:

```
cd exocortex-halo/download_bot
virtualenv2 env
. env/bin/activate
pip install youtube-dl
pip install requests
python ./download_bot.py
```

Includes is a `run.sh` shell script which automates starting up download_bot.py somewhat if you're using a virtualenv.  It requires that you called your virtualenv `env` and you created it inside of the download_bot/ directory.  Please see the contents of the shell script for more details (of which there are few - I tried to keep it as short and simple as I could).

