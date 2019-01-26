Please note that the less well curated your media collection is, the more trouble the bot will have interacting with it.  At the very least make sure that your media metadata is not fallacious (such as Folk Music mislabled as Talk Radio).

#The Command Parser
The command parser for this bot is very different from the other ones I've written.  It uses a parser that draws from [NLP](https://en.wikipedia.org/wiki/Natural_language_processing) techniques as well as [fuzzy matching](https://en.wikipedia.org/wiki/Fuzzy_matching_(computer-assisted_translation] using a module called [Fuzzywuzzy](https://github.com/seatgeek/fuzzywuzzy).  This means that the command parser needs to be front-loaded with sample text to train it.  I've included a directory of [sample corpora](https://en.wikipedia.org/wiki/Text_corpus) in the subdirectory *corpora/*.  Each file contains text which corresponds to a particular kind of question or command you can send the bot, such as "Do I have Johnny Mnemonic in my video library?" or "Play everything in my library by Information Society."

The name of each file corresponds to the type of interaction to parse: A search or a command.  For example, *corpora/search_requests_genres.txt* is used to teach the parser how to recognize when the user is asking the bot to search the genres (media metadata, like ID3 tags).  You can and should update these files with text that is more idiosyncratic of how you would ask questions and give commands to Kodi as if it had a verbal command interface.  All of these files must be present, but if a function is not used on your install (say, music playback on a set-top box) it should be of length 0.  I also plan on adding a list of disabled command classes in the configuration file.

Recognized filenames and corresponding functions:

* search_requests_genres.txt - Questions pertaining to searching your media library by genre.
* search_requests_artists.txt - Questions pertaining to searching your media library by artist or musician.
* search_requests_albums.txt - Questions pertaining to searching your media library by title of album or collection.
* search_requests_songs.txt - Questions pertaining to searching your media library by title of song or track.
* search_requests_videos.txt - Questions pertaining to searching your media library by title of video, movie, or show.
* commands_play.txt - Commands pertaining to starting playback of media.
* commands_pause.txt - Commands pertaining to pausing playback of media.
* commands_stop.txt - Commands pertaining to halting playback of media.
* commands_forward.txt - Commands pertaining to skipping forward.
* commands_backward.txt - Commands pertaining to skipping backward.
* commands_shuffle.txt - Commands pertaining to shuffling through your music library.  This is where party mode happens.
* help_basic.txt - Basic questions for getting online help.
* help_audio.txt - Questions for getting online help for audio.
* help_video.txt - Questions for getting online help for video.
* help_commands.txt - Questions for getting online help for other commands.

If the bot isn't quite sure if it's got a good match, it'll tell you so.  By default, kodi_bot.py will consider any confidence metric over 25% a good match.  You can change this by editing the configuration file and restarting the bot.

To make this bot work reliably, you'll probably have to create an *advancedsettings.xml* file in the Kodi *userdirectory/* directory on your Kodi box, per [these instructions](https://kodi.wiki/view/Advancedsettings.xml).  At least in part, the contents of this file should look something like this:

```
<advancedsettings>
    <network>
        <curlclienttimeout>120</curlclienttimeout>
    </network>
</advancedsettings>
```

Then restart Kodi.  I've found that this modification makes it much easier for the bot to generate a media library.  Why doesn't Kodi have an API to do this?  I don't know.

Please note that if you have any filenames with broken character encodings, Python will not be able to decode the bytestring and will barf.  By "broken" I mean filenames that look like this: **The.X-Files.S09E03.D'$'\346''monicus.WEBRip.x264-FUM.mp4**

Includes is a `run.sh` shell script which automates starting up kodi_bot.py somewhat if you're using a virtualenv.  It requires that you called your virtualenv `env` and you created it inside of the kodi_bot/ directory.  Please see the contents of the shell script for more details (of which there are few - I tried to keep it as short and simple as I could).

Included with the bot is a sample [supervisord](http://supervisord.org/) configuration file which will automatically start and manage the bot for you if you happen to be using it on your system.  It's much easier to wrangle than a huge .screenrc file, initscripts, or systemd service files.  If you want to use this file, install supervisord on the system, ideally from the default package repository (it's usually called **supervisor**).  Enable and start the supervisord service per your distribution's instructions.  Copy the **kodi_bot.conf.supervisord** file as **kodi_bot.conf** into your system's supervisord supplementary configuration file directory; on Raspbian this is */etc/supervisor/conf.d*.  Edit the file so that paths in the *command* and *directory* directives reflect where you checked out the source code.  Also set the *user* directive to the username that'll be running this bot (probably yourself).  For example, the */etc/supervisor/conf.d/kodibot.conf* file on my test machine looks like this:

```[program:kodibot]
command=/home/pi/exocortex-halo/kodi_bot/run.sh
directory=/home/pi/exocortex-halo/kodi_bot
startsecs=30
user=pi
redirect_stderr=true
process_name=kodibot
startretries=0
```

Then tell supervisord to look for new configuration directives and automatically start anything it finds: **sudo supervisorctl update**

supervisord will read the new config file and start Kodibot for you.

I've also included a .service file (`kodi_bot.service`) in case you want to use [systemd](https://www.freedesktop.org/wiki/Software/systemd/) to manage your bots.  Unlike supervisord, systemd can actually manage dependencies of system services, and as much as I find the service irritating it does a fairly decent job of this.  I've written the .service file specifically such that it can be run in [user mode](https://wiki.archlinux.org/index.php/Systemd/User) and will not require elevated permissions of any kind.  Here is the process for setting it up and using it:

* `mkdir -p ~/.config/systemd/user/`
* `cp ~/exocortex-halo/kodi_bot/kodi_bot.service ~/.config/systemd/user/`
* You configure Kodibot by making a copy of `kodi_bot.conf.example` to `kodi_bot.conf` and editing it.
* Starting Kodibot: `systemctl start --user kodi_bot.service`
  * You should see something like this if it worked:
```
[drwho@windbringer kodi_bot]$ ps aux | grep [k]odi_bot
drwho     6039  0.1  0.1 459332 24572 ?        Ssl  14:15   0:06 python2 /home/drwho/exocortex-halo/kodi_bot/kodi_bot.py
```
* Setting the XMPP bridge to start automatically on system boot: `systemctl enable --user kodi_bot.service`
  * You should see something like this if it worked:

```
[drwho@windbringer kodi_bot]$ ls -alF ~/.config/systemd/user/default.target.wants/
total 8
drwxr-xr-x 2 drwho drwho 4096 Jan 26 14:16 ./
drwxr-xr-x 3 drwho drwho 4096 Jan 26 14:15 ../
lrwxrwxrwx 1 drwho drwho   52 Jan 26 14:16 kodi_bot.service -> /home/drwho/.config/systemd/user/kodi_bot.service
```

