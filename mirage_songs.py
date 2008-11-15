import sqlite3, os
import const
from plugins.songsmenu import SongsMenuPlugin
from mirage import Mir, Db
from quodlibet.util import copool


def get_title(song):
    """return lowercase UNICODE title of song"""
    version = song.comma("version").lower()
    title = song.comma("title").lower()
    if version:
        return "%s (%s)" % (title, version)
    return title


class MirageSongsPlugin(SongsMenuPlugin):
    PLUGIN_ID = "Mirage Analysis"
    PLUGIN_NAME = _("Mirage Analysis")
    PLUGIN_DESC = _("Perform Mirage Analysis of the selected songs.")
    PLUGIN_ICON = "gtk-find-and-replace"
    PLUGIN_VERSION = "0.1"

    def player_get_userdir(self):
        """get the application user directory to store files"""
        try:
            return const.USERDIR
        except AttributeError:
            return const.DIR

    def do_stuff(self, songs):
        dbpath = os.path.join(self.player_get_userdir(), "similarity.db")
        self.connection = sqlite3.connect(dbpath)
        db = Db(self.connection)
        l = len(songs)
        for i, song in enumerate(songs):
            artist_name = song.comma("artist").lower()
            title = get_title(song)
            print "%03d/%03d %s - %s" % (i + 1, l, artist_name, title)
            filename = song("~filename")
            if song("~#length") < 60:
                continue
            track = self.get_track(artist_name, title)
            track_id, artist_id = track[0], track[1]
            if db.get_track(track_id):
                continue
            exclude_ids = self.get_artist_tracks(artist_id)
            mir = Mir()

            scms = mir.analyze(filename)
            db.add_and_compare(track_id, scms,exclude_ids=exclude_ids)
            yield True
        print "done"
        
    def plugin_songs(self, songs):
        copool.add(self.do_stuff, songs)

    def get_track(self, artist_name, title):
        """get track information from the database"""
        self.connection.commit()
        cursor = self.connection.cursor()
        title = title.encode("UTF-8")
        artist_id = self.get_artist(artist_name)[0]
        cursor.execute(
            "SELECT * FROM tracks WHERE artist = ? AND title = ?",
            (artist_id, title))
        row = cursor.fetchone()
        if row:
            return row
        cursor.execute(
            "INSERT INTO tracks (artist, title) VALUES (?, ?)",
            (artist_id, title))
        self.connection.commit()
        cursor.execute(
            "SELECT * FROM tracks WHERE artist = ? AND title = ?",
            (artist_id, title))
        return cursor.fetchone()
            
    def get_artist(self, artist_name):
        """get artist information from the database"""
        self.connection.commit()
        cursor = self.connection.cursor()
        artist_name = artist_name.encode("UTF-8")
        cursor.execute("SELECT * FROM artists WHERE name = ?", (artist_name,))
        row = cursor.fetchone()
        if row:
            return row
        cursor.execute("INSERT INTO artists (name) VALUES (?)", (artist_name,))
        self.connection.commit()
        cursor.execute("SELECT * FROM artists WHERE name = ?", (artist_name,))
        return cursor.fetchone()

    def get_artist_tracks(self, artist_id):
        self.connection.commit()
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT tracks.id FROM tracks INNER JOIN artists"
            " ON tracks.artist = artists.id WHERE artists.id = ?",
            (artist_id, ))
        return [row[0] for row in cursor.fetchall()]