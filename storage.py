import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import List

from iso639_json_parser import Iso639Decoder, Iso639Encoder


class Storage:
    _VIDEO_SUBTITLE_FILE_TABLE = 'video_subtitle'
    _VIDEO_FILE_TABLE = 'video_file'

    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)

        def dict_factory(cursor, row):
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d

        self.conn.row_factory = dict_factory  # sqlite3.Row
        self.__ini_db()

    def __ini_db(self):
        sql_create_file_table = f"""
        CREATE TABLE IF NOT EXISTS {Storage._VIDEO_FILE_TABLE} (
        id INTEGER PRIMARY KEY,
        dir TEXT NOT NULL,
        filename TEXT NOT NULL,
        scan_time TEXT NOT NULL)
        """
        sql_create_file_subtitle_table = f"""
        CREATE TABLE IF NOT EXISTS {Storage._VIDEO_SUBTITLE_FILE_TABLE} (
          id integer PRIMARY key,
          video_file_id integer not NULL,
          full_path TEXT NOT NULL,
          language_iso639_3 TEXT NOT NULL,
          track_id INTEGER,
          source TEXT NOT NULL,
          FOREIGN KEY(video_file_id) REFERENCES video_file(id))
        """

        for sql in [sql_create_file_table, sql_create_file_subtitle_table]:
            self.conn.execute(sql)

    def create_video_file(self, dir: str, filename: str, override_on_exist: bool = False) -> sqlite3.Row:
        x = (dir.rstrip('/'), filename, datetime.utcnow().isoformat())
        with self.conn as c:
            exec_r = self.conn.execute(
                f"INSERT {'OR REPLACE' if override_on_exist else ''} INTO {self._VIDEO_FILE_TABLE} "
                f"(dir, filename, scan_time) VALUES (?,?,?)",
                x)
        return self.get_video_file_by_id(exec_r.lastrowid)

    def create_video_subtitle(self, video_file_id: int, full_path: str, language_iso639_3: str, track_id: int,
                              source='FILE', override_on_exist: bool = False) -> sqlite3.Row:
        x = (video_file_id, full_path, language_iso639_3, track_id, source)
        with self.conn:
            exec_r = self.conn.execute(
                f"INSERT {'OR REPLACE' if override_on_exist else ''} INTO {self._VIDEO_SUBTITLE_FILE_TABLE} "
                f"(video_file_id, full_path, language_iso639_3, track_id, source) VALUES (?,?,?,?,?)",
                x)
        return self.get_video_subtitle_by_id(exec_r.lastrowid)

    def get_video_file_by_id(self, id: int) -> sqlite3.Row:
        c = self.conn.cursor()
        r = c.execute(f"SELECT * FROM {Storage._VIDEO_FILE_TABLE} WHERE id == {id}")
        return c.fetchone()

    def get_video_subtitle_by_id(self, id: int) -> sqlite3.Row:
        c = self.conn.cursor()
        r = c.execute(f"SELECT * FROM {Storage._VIDEO_SUBTITLE_FILE_TABLE} WHERE id == {id}")
        return c.fetchone()

    def get_all_video_files(self) -> List[sqlite3.Row]:
        c = self.conn.cursor()
        r = c.execute(f"SELECT * FROM {Storage._VIDEO_FILE_TABLE}")
        return c.fetchall()

    def get_all_subtitles(self) -> List[sqlite3.Row]:
        c = self.conn.cursor()
        r = c.execute(f"SELECT * FROM {Storage._VIDEO_SUBTITLE_FILE_TABLE}")
        return c.fetchall()

    def get_all_subtitles_by_video_file_id(self, video_file_id: int) -> List[sqlite3.Row]:
        c = self.conn.cursor()
        r = c.execute(f"SELECT * FROM {Storage._VIDEO_SUBTITLE_FILE_TABLE} WHERE video_file_id = {video_file_id}")
        return c.fetchall()

    def get_video_file_by_full_path(self, full_path) -> sqlite3.Row:
        (dir, file_name) = os.path.split(full_path)
        c = self.conn.cursor()
        r = c.execute(f"SELECT * FROM {Storage._VIDEO_FILE_TABLE} WHERE dir = ? AND filename = ?",
                      (dir.rstrip('/'), file_name))
        x = c.fetchone()
        return x

    def _migrate_from_cache_file(self, cache_file_path):
        def read_cache(file_path):
            cache_file_path = file_path

            if not os.path.isfile(cache_file_path):
                return {}

            try:
                with open(cache_file_path) as json_file:
                    data = json.load(json_file, cls=Iso639Decoder)
                    return data or {}
            except Exception as e:
                logging.error(f"Open cache file {cache_file_path} error {e}")
            return {}

        def save_cache(file_path, cache):
            with open(file_path, 'w') as outfile:
                json.dump(cache, outfile, cls=Iso639Encoder, indent=4, sort_keys=True)

        cache = read_cache(cache_file_path)
        is_migration_complete = cache.get('migration_complete', False)

        if is_migration_complete:
            # skipping
            return

        for file in cache['files']:
            file_dir = file['dir']
            file_name = file['filename']
            x = self.create_video_file(file_dir, file_name)

            print(f"Migration from cache file {x['filename']}, id: {x['id']}")
            for subtitle in file['subtitles']:
                srt_full_path = subtitle['srt_full_path']
                srt_lang_code = subtitle['srt_lang_code']
                srt_track_id = subtitle['srt_track_id']
                self.create_video_subtitle(x['id'], srt_full_path, srt_lang_code.part3, srt_track_id)

            for merged_subtitles in file['merged_subtitles']:
                lang_bot = merged_subtitles['lang_bot']
                lang_top = merged_subtitles['lang_top']
                srt_full_path = merged_subtitles['srt_full_path']
                self.create_video_subtitle(x['id'], srt_full_path, f"{lang_top.part3},{lang_bot.part3}", None,
                                           source='Merge')

        cache['migration_complete'] = True
        save_cache(cache_file_path, cache)
