#!/usr/bin/env python3
"""
Copyright 2015 Juan Orti Alcaine <j.orti.alcaine@gmail.com>


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import argparse
import logging
import os
import re
import signal
import sys
import threading
import time
from collections import namedtuple
from pathlib import Path
from typing import List, Set

from babelfish import Language
from iso639 import languages as iso639, Iso639
from subliminal import save_subtitles, scan_video, region, download_best_subtitles, subtitle
from watchdog.observers import Observer

import mergesubs
import util
from extract_mkv_info import parse_mkv_subtitles_info_from_file, extract_mkv_tracks
from liste_files import FileFinallyCreatedEventHandler
from storage import Storage

ScannedFile = namedtuple('ScanFile', ['filename', 'basename', 'extension', 'dir', 'full_path', 'subtitles',
                                      'merged_subtitles'])
FileToScan = namedtuple('FileToScan', ['root', 'filename'])
AppRunConfig = namedtuple('AppRunConfig', ['target_path', 'target_languages', 'merge_languages_pairs',
                                           'validation_regex', 'opensubtitles_auth', 'download_online',
                                           'listen_new'])

CACHE_FILE_NAME = '.extractsubs'
# dictionary, saving in root_path/CACHE_FILE_NAME
_SUPPORTED_FILE_EXTENSIONS = ['.mkv', '.mp4', '.avi', '.mpg', '.mpeg']

logging.basicConfig(level='INFO', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class ExtractSubs:
    SUBLIMINAL_CACHE_DIR = os.path.join(os.getenv('HOME'), '.subliminal')

    def __init__(self, app_config: AppRunConfig, storage: Storage):
        self.app_config = app_config
        self._storage = storage
        self._validation = re.compile(app_config.validation_regex)

    def _check(self):
        if not self.app_config.target_path:
            logging.error("No directory supplied")
            sys.exit(1)
        if not os.path.isdir(self.app_config.target_path) and not os.path.isfile(self.app_config.target_path):
            sys.exit(f"Error, {self.app_config.target_path} is not a directory or file")

    def _prepare_subliminal(self):
        if not os.path.exists(ExtractSubs.SUBLIMINAL_CACHE_DIR):
            os.makedirs(ExtractSubs.SUBLIMINAL_CACHE_DIR)
        cache_file = os.path.join(ExtractSubs.SUBLIMINAL_CACHE_DIR, 'subliminal.cachefile.dbm')
        # configure the cache
        region.configure('dogpile.cache.dbm', arguments={'filename': cache_file})

    def _is_file_valid(self, name, root):
        (basename, ext) = os.path.splitext(name)
        is_not_system_folder = '/@Recycle' not in root and '/@Recently-Snapshot' not in root
        return ext in _SUPPORTED_FILE_EXTENSIONS and self._validation.match(name) is not None and is_not_system_folder

    def _is_file_already_scanned(self, name, root):
        try:
            return self._storage.is_file_scanned(os.path.join(root, name))
        except Exception as e:
            logging.error(f"Download error {e}")
            return False

    def _merge_subs(self, file: ScannedFile):
        if not self.app_config.merge_languages_pairs or not file:
            return

        def file_path_by_lang(file_subtitles: list, iso639_language: iso639) -> Set[str]:
            return {x['srt_full_path'] for x in file_subtitles if x['srt_lang_code'] is iso639_language}

        subtitles = file.subtitles if file.subtitles else []

        for merge_lang_pair in self.app_config.merge_languages_pairs:
            lang_top = merge_lang_pair[0]
            lang_bot = merge_lang_pair[1]
            top_subtitle_paths = file_path_by_lang(subtitles, lang_top)
            bot_subtitle_paths = file_path_by_lang(subtitles, lang_bot)

            def _subtitle_path_exists(subtitle_path: str) -> bool:
                return subtitle_path is not None and Path(subtitle_path).exists()

            index = 1

            for top_subtitle_path in top_subtitle_paths:
                for bot_subtitle_path in bot_subtitle_paths:
                    if _subtitle_path_exists(top_subtitle_path) and _subtitle_path_exists(bot_subtitle_path):
                        index_suffix = f"_{index}" if len(top_subtitle_paths) == 1 and len(bot_subtitle_paths) == 1 \
                            else ""
                        merged_srt_path = f"{os.path.join(file.dir, file.basename)}" \
                                          f".{lang_top.part1}_{lang_bot.part1}{index_suffix}.ass"
                        try:
                            mergesubs.merge(top_subtitle_path,
                                            bot_subtitle_path,
                                            merged_srt_path)
                            file.merged_subtitles.append({
                                'lang_top': lang_top,
                                'lang_bot': lang_bot,
                                'srt_full_path': merged_srt_path
                            })
                            index = index + 1
                        except Exception as e:
                            import traceback, sys
                            traceback.print_exc(file=sys.stdout)
                            logging.error(f"Merge error {str(e)}")

    def _read_subtitles(self, file_to_scan: FileToScan) -> ScannedFile:
        name = file_to_scan.filename
        root = file_to_scan.root
        (basename, ext) = os.path.splitext(name)
        if ext == '.mkv':
            subtitles = []
            # todo find existed merged subtitles
            movie = ScannedFile(name, basename, ext, root, os.path.join(root, name), subtitles, [])

            for mkv_subtitle_info in parse_mkv_subtitles_info_from_file(os.path.join(root, name)):
                track_iso639_lang_code = util.bcp47_language_code_to_iso_639(mkv_subtitle_info.language_ietf,
                                                                             default=mkv_subtitle_info.language)
                name_suffix = f"_{mkv_subtitle_info.name}" if mkv_subtitle_info.name else ""
                srt_full_path = os.path.join(root, f"{basename}_{track_iso639_lang_code}{name_suffix}.srt")
                srt_exists = os.path.isfile(srt_full_path)
                s = {
                    'srt_track_id': mkv_subtitle_info.track_number,
                    'srt_full_path': srt_full_path,
                    'srt_exists': srt_exists
                }
                if track_iso639_lang_code:
                    s['srt_lang_code'] = util.iso639_from_str(track_iso639_lang_code)

                subtitles.append(s)
            return movie
        else:
            empty_movie = ScannedFile(name, basename, ext, root, os.path.join(root, name), [], [])
            return empty_movie

    def _scrap_files_to_scan(self) -> List[FileToScan]:
        files_to_scan = []
        extr_path = self.app_config.target_path
        if os.path.isdir(extr_path):
            for dirpath, dirs, files in os.walk(extr_path):
                for name in files:
                    if self._is_file_valid(name, dirpath) and not self._is_file_already_scanned(name, dirpath):
                        files_to_scan.append(FileToScan(dirpath, name))
        elif os.path.isfile(extr_path):
            dirpath = os.path.dirname(extr_path)
            name = os.path.basename(extr_path)
            if self._is_file_valid(name, dirpath) and not self._is_file_already_scanned(name, dirpath):
                files_to_scan.append(FileToScan(dirpath, name))
        return files_to_scan

    def _save_scanned_files(self, file: ScannedFile):
        saved_video_file = self._storage.create_video_file(file.dir, file.filename)
        for file_subtitle in file.subtitles:
            self._storage.create_video_subtitle(saved_video_file['id'], file_subtitle['srt_full_path'],
                                                file_subtitle['srt_lang_code'].part3, file_subtitle['srt_track_id'],
                                                source='FILE')
        for merged_subtitles in file.merged_subtitles:
            lang_bot = merged_subtitles['lang_bot']
            lang_top = merged_subtitles['lang_top']
            self._storage.create_video_subtitle(saved_video_file['id'], merged_subtitles['srt_full_path'],
                                                f"{lang_top.part3},{lang_bot.part3}", None, 'Merge')

    def _extract_subs(self, file: ScannedFile):
        logging.info("*****************************")
        logging.info(f"Directory: {file.dir}")
        logging.info(f"File: {file.filename}")
        logging.info("Embedded subtitles found.")
        extract_mkv_tracks(file.full_path, file.subtitles)
        extracted_languages = [subtitle for subtitle in file.subtitles if subtitle['srt_lang_code'] is not None]
        languages_to_download = [x for x in self.app_config.target_languages if x not in extracted_languages]

        if self.app_config.download_online:
            self._download_subs(file, languages_to_download)

    def _download_subs(self, file: ScannedFile, download_subtitle_langs=None):
        if download_subtitle_langs is None:
            download_subtitle_langs = [iso639.get(part3='eng')]
        logging.info("Analyzing video file...")
        try:
            video = scan_video(file.full_path)
        except ValueError as ex:
            logging.info("Failed to analyze video. ", ex)
            return None
        logging.info("Choosing subtitle from online providers...")
        languages_to_download = set(map(lambda lang: Language(lang.part3), download_subtitle_langs))
        best_subtitles = download_best_subtitles({video}, languages_to_download, only_one=True,
                                                 provider_configs={'opensubtitles': (
                                                     self.app_config.opensubtitles_auth)})
        if best_subtitles[video]:
            logging.info("Downloading subtitles...")
            try:
                saved_subtitles = save_subtitles(video, best_subtitles[video])
                for saved_subtitle in saved_subtitles:
                    subtitle_path = subtitle.get_subtitle_path(video.name, saved_subtitle.language)
                    file_exist = os.path.isfile(subtitle_path)
                    file.subtitles = file.subtitles if file.subtitles else []
                    file.subtitles.append({
                        'srt_track_id': None,
                        'srt_full_path': subtitle_path,
                        'srt_exists': file_exist,
                        'srt_lang_code': iso639.get(part3=saved_subtitle.language.alpha3),
                    })

            except Exception as e:
                logging.error(f"Download error {e}")
        else:
            logging.error("No subtitles found online.")

    def scan_files(self):
        self._check()
        self._prepare_subliminal()

        files_to_scan = self._scrap_files_to_scan()

        self.extract_and_merge(files_to_scan)

    def extract_and_merge(self, files: List[FileToScan]):
        scanned_files = [self._read_subtitles(file_to_scan) for file_to_scan in files]

        for scanned_file in scanned_files:
            self._extract_subs(scanned_file)
            self._merge_subs(scanned_file)
            self._save_scanned_files(scanned_file)


class ListenNewFiles(threading.Thread):
    def __init__(self, extract_subs: ExtractSubs, target_path: str):
        super().__init__()
        self._file_observer = Observer()
        self.cease_continuous_run = threading.Event()
        self._extract_subs = extract_subs
        self._event_handler = FileFinallyCreatedEventHandler(["*.mkv"], self._filter_files, self._extract_and_merge)
        self._file_observer.schedule(self._event_handler, target_path, recursive=True)

    def _filter_files(self, name: str, dirpath: str) -> bool:
        return self._extract_subs._is_file_valid(name, dirpath) and \
               not self._extract_subs._is_file_already_scanned(name, dirpath)

    def _extract_and_merge(self, name: str, dirpath: str):
        self._extract_subs.extract_and_merge([FileToScan(dirpath, name)])

    def run(self):
        self._file_observer.start()
        while not self.cease_continuous_run.is_set():
            self._event_handler.pending_watch_created_files()
            time.sleep(1)

    def stop(self):
        self.cease_continuous_run.set()
        self._file_observer.stop()
        self._file_observer.join()


if __name__ == '__main__':

    def parse_opensubtitles_parameters(parameter):
        match = re.match(r"username=(?P<username>.*),password=(?P<password>.*)", parameter)
        if match is None:
            return {
                'username': '',
                'password': ''
            }
        username = match.group('username') or ''
        password = match.group('password') or ''
        return {
            'username': username,
            'password': password
        }


    def parse_merge_langs(parameter: str) -> List[List[Iso639]]:
        if parameter is None:
            return []
        languages_pairs = {pair.strip() for pair in parameter.split(',')}

        def parse_languages_pair_to_iso639_pair(languages_pair_str):
            return [iso639.get(part1=x) for x in (languages_pair_str.split('-'))]

        iso639_pairs = [parse_languages_pair_to_iso639_pair(pair_str) for pair_str in languages_pairs]
        return [pair for pair in iso639_pairs if len(pair) == 2]


    def parse_languages(parameter: str) -> List[Iso639]:
        if parameter is None:
            return []
        return [iso639.get(part1=lang) for lang in {x.strip() for x in (parameter.split(','))}]


    def get_root_dir(path: str) -> str:
        if os.path.isdir(path):
            return path
        elif os.path.isfile(path):
            return os.path.dirname(path)


    parser = argparse.ArgumentParser()
    parser.add_argument('path', help='extracting path to a folder or to a file', type=str)
    parser.add_argument('--validation-regex', help='validation folders/files regex', type=str)
    parser.add_argument('--opensubtitles',
                        help='auth for opensubtitles, example value--: username=myusername,password=mypassword',
                        type=str)
    parser.add_argument('--merge-languages',
                        help='two languages for merge 2-letter code, example: ru-fr,ru-en. It\'ll generate subtitle xxx.ru_fr.ass with ru on top and fr on bot',
                        type=str)
    parser.add_argument('--languages',
                        help='languages to extract and download in format iso639-1 separated by \',\', example: en,ru,fr',
                        type=str)
    parser.add_argument('--db-file', help='Full path to sqlite file', type=str, default='.extract-subs.sqlite3')
    parser.add_argument('--no-download-subtitles-online', dest='download_online',
                        action='store_false', help='do not try to download missed subtitles online')
    parser.add_argument('--listen-new', help='listen new files', action='store_true')
    parser.set_defaults(download_online=True)
    args = parser.parse_args()
    path = args.path
    validation_regex = args.validation_regex or '.*'
    opensubtitles = args.opensubtitles or ''
    opensubtitles_auth = parse_opensubtitles_parameters(opensubtitles)
    merge_languages_pairs = parse_merge_langs(args.merge_languages)
    target_languages = parse_languages(args.languages)

    with Storage(args.db_file) as storage:
        storage._migrate_from_cache_file(os.path.join(get_root_dir(path), CACHE_FILE_NAME))

        app_run_config = AppRunConfig(target_path=path, target_languages=target_languages,
                                      merge_languages_pairs=merge_languages_pairs,
                                      validation_regex=validation_regex, opensubtitles_auth=opensubtitles_auth,
                                      download_online=args.download_online, listen_new=args.listen_new)

        sub_extract = ExtractSubs(app_run_config, storage)
        sub_extract.scan_files()
        if args.listen_new:
            watcher = ListenNewFiles(sub_extract, app_run_config.target_path)


            def stop_app(g, i):
                watcher.stop()
                logging.info("File listener stopped")


            watcher.start()
            signal.signal(signal.SIGINT, stop_app)
            signal.signal(signal.SIGTERM, stop_app)
            signal.pause()
