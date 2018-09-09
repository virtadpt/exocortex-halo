#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim: set expandtab tabstop=4 shiftwidth=4 :

# media_library.py - Kodi Bot module which does the heavy lifting of acquiring,
#   organizing, and manipulating a media library from Kodi.  Kodi doesn't offer
#   any of this functionality so we have to do it ourselves.
#
#   This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo/).

# By: The Doctor <drwho at virtadpt dot net>
#       0x807B17C1 / 7960 1CDC 85C9 0B63 8D9F  DD89 3BD8 FF2B 807B 17C1

# License: GPLv3

# v1.0 - Initial release.

# TO-DO:
# -

# Load modules.
import logging
import os

from kodipydent import Kodi

# Constants.

# Global variables.

# Handles to the results returned from the Kodi library API.
artists = None
albums = None
songs = None
movies = None
tv = None
musicvideos = None
audio = None
video = None

# Functions.

# Generate a list of media sources on the Kodi box.  From the Kodi docs, there
#   are only two we have to care about, video and music.  I'm using the
#   canonical Kodi names for consistency's sake.  Takes one argument, a Kodi
#   client object.  Returns a hash table containing the media sources the Kodi
#   box has configured.
def get_media_sources(kodi):
    logging.debug("Entered media_library.get_media_sources().")

    sources = {}
    sources["video"] = []
    sources["music"] = []
    tmp = None

    # Build a list of video sources on the Kodi box.
    tmp = kodi.Files.GetSources("video")
    for i in tmp["result"]["sources"]:
        sources["video"].append(i["file"])

    # Build a list of music sources on the Kodi box.
    tmp = kodi.Files.GetSources("music")
    for i in tmp["result"]["sources"]:
        sources["music"].append(i["file"])

    logging.debug("Known media sources: %s" % str(sources))
    return sources

# Function that builds the local media library, because there's no
#   straightforward way to query Kodi.  Takes four args, a reference to a
#   Kodi client object, a hash table of media sources, a hash table
#   representing the media library, and a list of directories to ignore.
#   Returns a new copy of the media library.
def build_media_library(kodi, sources, media_library, exclude_dirs):
    logging.debug("entered kodi_library.build_media_library().")
    logging.info("Now indexing media library... this could take a while.")

    # Set up categories in the media library.
    media_library["artists"] = []
    media_library["albums"] = []
    media_library["audio"] = []
    media_library["movies"] = []
    media_library["music"] = []
    media_library["musicvideos"] = []
    media_library["songs"] = []
    media_library["tv"] = []
    media_library["video"] = []

    # For every media source...
    for source in sources.keys():
        # For every directory in every media source...
        #logging.debug("Now scanning media source %s..." % source)
        for directory in sources[source]:
            logging.debug("Now scanning media directory %s..." % directory)

            # Skip the EXT?fs lost+found directory.
            if directory.endswith("lost+found/"):
                continue

            # Check the list of directories to skip.
            bounce = False
            for x in exclude_dirs:
                if bounce:
                    logging.debug("Sorry - gotta bounce!")
                    break
                if x in directory:
                    logging.debug("Skipping over excluded directory %s." % directory)
                    bounce = True
                    break
            if bounce:
                logging.debug("Nope - skipping this directory!")
                continue

            # Get the contents of the directory.
            tmp = kodi.Files.GetDirectory(directory)

            # Catch file system errors, like file permissions.
            if "error" in tmp.keys():
                logging.warn("Got one of Kodi's 'Invalid params' error messages when accessing %s.  Might be bad permissions.  Skipping." % directory)
                continue

            # Catch the "no files in directory" case.
            if tmp["result"]["limits"]["start"] == 0:
                if tmp["result"]["limits"]["end"] == 0:
                    logging.debug("Found empty directory %s, skipping." % directory)
                    continue
            # "Explicit is better than implicit."

            tmp = tmp["result"]["files"]
            # For every thing in that directory...
            for k in tmp:

                # If you run into a subdirectory, append it to the list of
                # sources so it can also be scanned.  There is undoubtedly a
                # better and more stable way of doing this but I don't know
                # what it is yet.
                if k["file"].endswith("/"):
                    #logging.debug("Found subdirectory %s in the media library.  Adding it to the queue to index later." % k["file"])
                    sources[source].append(k["file"])
                    continue

                # Otherwise, add the media to the library.
                media_tmp = {}
                media_tmp["file"] = k["file"]
                media_tmp["label"] = k["label"]
                media_library[source].append(media_tmp)

    return media_library

# Load the media library from Kodi in steps, because there are multiple library
# databases inside of Kodi.  This is simultaneously interesting, opaque, and
# frustrating because I've been dorking around with this all night.
def get_media_metadata():
    logging.debug("Now constructing index of artists.")
    artists = kodi.AudioLibrary.GetArtists()
    if "artists" not in artists["result"]:
        logging.warn("No artists found in library.")
    else:
        for i in artists["result"]["artists"]:
            tmp = {}
            tmp["artistid"] = i["artistid"]
            tmp["artist"] = i["artist"]
            media_library["artists"].append(tmp)
    artists = None

    logging.debug("Now constructing index of albums.")
    albums = kodi.AudioLibrary.GetAlbums()
    if "albums" not in albums["result"]:
        logging.debug("No albums found in library.")
    else:
        for i in albums["result"]["albums"]:
            tmp = {}
            tmp["albumid"] = i["albumid"]
            tmp["label"] = i["label"]
            media_library["albums"].append(tmp)
    albums = None

    logging.debug("Now constructing index of songs.")
    songs = kodi.AudioLibrary.GetSongs()
    if "songs" not in songs["result"]:
        logging.debug("No songs found in library.")
    else:
        for i in songs["result"]["songs"]:
            tmp = {}
            tmp["songid"] = i["songid"]
            tmp["label"] = i["label"]
            media_library["songs"].append(tmp)
    songs = None

    logging.debug("Now constructing index of movies.")
    movies = kodi.VideoLibrary.GetMovies()
    if "movie" not in movies["result"]:
        logging.debug("No movies found in library.")
    else:
        for i in movies["result"]["movies"]:
            tmp = {}
            tmp["movieid"] = i["movieid"]
            tmp["label"] = i["label"]
            media_library["movies"].append(tmp)
    movies = None

    logging.debug("Now constructing index of television episodes.")
    tv = kodi.VideoLibrary.GetTVShows()
    if "movie" not in movies["result"]:
        logging.debug("No movies found in library.")
    else:
        for i in movies["result"]["movies"]:
            tmp = {}
            tmp["movieid"] = i["movieid"]
            tmp["label"] = i["label"]
            media_library["movies"].append(tmp)
    movies = None

    # At this point, we should have a full media library.  In practice, we don't
    # and I'm not sure why.  My media box is certainly useable but

if "__name__" == "__main__":
    pass
