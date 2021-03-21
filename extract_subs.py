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
import shutil
import signal
import sys
import threading
import time
from pathlib import Path
from typing import List, Set

from iso639 import languages as iso639, Iso639
from subliminal import region
from watchdog.observers.polling import PollingObserver

import mergesubs
import util
from entities import AppRunConfig, ProcessedFile, ExtractedMKVTrack, MergedSubtitle, FileToScan, \
    ScannedFile, TrackMetadata
from extract_mkv_info import parse_mkv_subtitles_info_from_file, extract_mkv_tracks, \
    MKV_TRACK_TYPE_SUBTITLE
from file_event_handler import FileFinallyCreatedEventHandler
from storage import Storage

CACHE_FILE_NAME = '.extractsubs'
# dictionary, saving in root_path/CACHE_FILE_NAME
_SUPPORTED_FILE_EXTENSIONS = ['.mkv', '.mp4', '.avi', '.mpg', '.mpeg']

logging.basicConfig(level='INFO', format='%(asctime)s - [%(filename)s:%(lineno)d] - %(levelname)s - %(message)s')
logging.getLogger('schedule').propagate = False


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

    def _merge_subs(self, processed_file: ProcessedFile) -> ProcessedFile:
        extracted_tracks = processed_file.extracted_tracks
        if not self.app_config.merge_languages_pairs or not extracted_tracks or len(extracted_tracks) == 0:
            return processed_file

        def tracks_by_language(iso639_language: iso639) -> Set[ExtractedMKVTrack]:
            return {extracted_track for extracted_track in extracted_tracks if
                    extracted_track.metadata.language_code is iso639_language}

        merged_subtitles = processed_file.merged_subtitles if processed_file.merged_subtitles else []
        for merge_lang_pair in self.app_config.merge_languages_pairs:
            lang_top = merge_lang_pair[0]
            lang_bot = merge_lang_pair[1]
            top_tracks = tracks_by_language(lang_top)
            bot_tracks = tracks_by_language(lang_bot)

            def _subtitle_path_exists(subtitle_path: Path) -> bool:
                return subtitle_path is not None and subtitle_path.exists()

            index = 1

            for top_track in top_tracks:
                for bot_track in bot_tracks:
                    if _subtitle_path_exists(top_track.track_path) and _subtitle_path_exists(bot_track.track_path):
                        index_suffix = f"_{index}" if len(top_tracks) == 1 and len(bot_tracks) == 1 \
                            else ""
                        merged_srt_filename = f"{processed_file.scanned_file.basename}.{lang_top.part3}_{lang_bot.part3}{index_suffix}.ass"
                        merged_srt_path = processed_file.scanned_file.dir / merged_srt_filename
                        try:
                            mergesubs.merge(top_track.track_path,
                                            bot_track.track_path,
                                            merged_srt_path)
                            merged_subtitles.append(MergedSubtitle(top_track, bot_track, merged_srt_path))
                            index = index + 1
                        except Exception as e:
                            import traceback, sys
                            traceback.print_exc(file=sys.stdout)
                            logging.error(f"Merge error {str(e)}")
        return ProcessedFile(processed_file.scanned_file, processed_file.extracted_tracks, merged_subtitles)

    def _read_subtitles(self, file_to_scan: FileToScan) -> ScannedFile:
        name = file_to_scan.filename
        root = file_to_scan.root
        container_file_path = os.path.join(root, name)
        (basename, ext) = os.path.splitext(name)
        if ext == '.mkv':
            subtitles = [TrackMetadata(Path(container_file_path), mkv_subtitle_info.track_number,
                                       util.bcp47_language_code_to_iso_639(mkv_subtitle_info),
                                       mkv_subtitle_info)
                         for mkv_subtitle_info in parse_mkv_subtitles_info_from_file(container_file_path)]
            return ScannedFile(name, basename, ext, Path(root), Path(container_file_path), subtitles)
        else:
            return ScannedFile(name, basename, ext, Path(root), Path(container_file_path), [])

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

    def _save_scanned_files(self, processed_file: ProcessedFile) -> ProcessedFile:
        file = processed_file.scanned_file
        saved_video_file = self._storage.create_video_file(str(file.dir), file.filename)
        for extracted_track in processed_file.extracted_tracks:
            self._storage.create_video_subtitle(saved_video_file['id'], str(extracted_track.track_path),
                                                extracted_track.metadata.language_code.part3,
                                                extracted_track.metadata.srt_track_id,
                                                source='FILE')
        for merged_subtitle in processed_file.merged_subtitles:
            bot_track = merged_subtitle.bot_track
            top_track = merged_subtitle.top_track
            langs_part3 = f"{top_track.metadata.language_code.part3},{bot_track.metadata.language_code.part3}"
            self._storage.create_video_subtitle(saved_video_file['id'], str(merged_subtitle.srt_path),
                                                langs_part3, None, 'Merge')
        return processed_file

    def _extract_subs(self, file: ScannedFile) -> ProcessedFile:
        return ProcessedFile(file, extract_mkv_tracks(file.full_path, file.subtitles))

    # TODO fix downloading subtitle
    # def _download_subs(self, file: ScannedFile, download_subtitle_langs=None):
    #     if download_subtitle_langs is None:
    #         download_subtitle_langs = [iso639.get(part3='eng')]
    #     logging.info("Analyzing video file...")
    #     try:
    #         video = scan_video(file.full_path)
    #     except ValueError as ex:
    #         logging.info("Failed to analyze video. ", ex)
    #         return None
    #     logging.info("Choosing subtitle from online providers...")
    #     languages_to_download = set(map(lambda lang: Language(lang.part3), download_subtitle_langs))
    #     best_subtitles = download_best_subtitles({video}, languages_to_download, only_one=True,
    #                                              provider_configs={'opensubtitles': (
    #                                                  self.app_config.opensubtitles_auth)})
    #     if best_subtitles[video]:
    #         logging.info("Downloading subtitles...")
    #         try:
    #             saved_subtitles = save_subtitles(video, best_subtitles[video])
    #             for saved_subtitle in saved_subtitles:
    #                 subtitle_path = subtitle.get_subtitle_path(video.name, saved_subtitle.language)
    #                 file.subtitles = file.subtitles if file.subtitles else []
    #                 file.subtitles.append({
    #                     'srt_track_id': None,
    #                     'srt_full_path': subtitle_path,
    #                     'srt_lang_code': iso639.get(part3=saved_subtitle.language.alpha3),
    #                 })
    #
    #         except Exception as e:
    #             logging.error(f"Download error {e}")
    #     else:
    #         logging.error("No subtitles found online.")

    def scan_files(self):
        self._check()
        # TODO fix downloading subtitle
        # self._prepare_subliminal()

        files_to_scan = self._scrap_files_to_scan()

        self.extract_and_merge(files_to_scan)

    def extract_and_merge(self, files: List[FileToScan]):
        for file_to_scan in files:
            scanned_file = self._read_subtitles(file_to_scan)
            pf = self._extract_subs(scanned_file)
            pf_with_lang = self._detect_missed_tracks_languages(pf)
            pf_with_merged_subs = self._merge_subs(pf_with_lang)
            pf = self._save_tmp_tracks(pf_with_merged_subs)
            self._save_scanned_files(pf)

    def _detect_missed_tracks_languages(self, pf: ProcessedFile) -> ProcessedFile:
        def _detect_track_lang(processed_track: ExtractedMKVTrack) -> ExtractedMKVTrack:
            metadata = processed_track.metadata
            if metadata.track_info.track_type == MKV_TRACK_TYPE_SUBTITLE:
                lang_code = util.detect_iso639(metadata.language_code, processed_track.track_path)
                track_metadata_with_fixed_language_code = \
                    TrackMetadata(metadata.file_container_path, metadata.srt_track_id, lang_code, metadata.track_info)
                return ExtractedMKVTrack(track_metadata_with_fixed_language_code, processed_track.track_path,
                                         processed_track.is_temp_file)
            else:
                return processed_track

        tracks_with_fixed_language_code = [_detect_track_lang(pt) for pt in pf.extracted_tracks]
        return ProcessedFile(pf.scanned_file, tracks_with_fixed_language_code)

    def _save_tmp_tracks(self, processed_file: ProcessedFile):
        extracted_tracks = []
        for extracted_track in processed_file.extracted_tracks:
            if extracted_track.is_temp_file:
                track_name = extracted_track.metadata.track_info.name
                name_suffix = f"_{track_name}" if track_name else ""
                basename = processed_file.scanned_file.basename
                track_iso639_lang_code = extracted_track.metadata.language_code.part3
                root = processed_file.scanned_file.dir
                srt_full_path = root / f"{basename}_{track_iso639_lang_code}{name_suffix}.srt"

                logging.info(f"Moving from {extracted_track.track_path} to {srt_full_path}")
                shutil.move(str(extracted_track.track_path), str(srt_full_path))

                extracted_tracks.append(ExtractedMKVTrack(extracted_track.metadata, srt_full_path, False))
            else:
                extracted_tracks.append(extracted_track)
        return ProcessedFile(processed_file.scanned_file, extracted_tracks, processed_file.merged_subtitles)


class NewFilesListener(threading.Thread):
    DEFAULT_OBSERVER_TIMEOUT = 5 * 60  # in seconds

    def __init__(self, extract_subs: ExtractSubs, target_path: str):
        super().__init__()
        self._file_observer = PollingObserver(NewFilesListener.DEFAULT_OBSERVER_TIMEOUT)
        self.cease_continuous_run = threading.Event()
        self._extract_subs = extract_subs
        self._target_path = target_path
        self._event_handler = FileFinallyCreatedEventHandler(["*.mkv"], self._file_predicate, self._extract_and_merge)
        self._file_observer.schedule(self._event_handler, target_path, recursive=True)

    def _file_predicate(self, name: str, dirpath: str) -> bool:
        return self._extract_subs._is_file_valid(name, dirpath) and \
               not self._extract_subs._is_file_already_scanned(name, dirpath)

    def _extract_and_merge(self, name: str, dirpath: str):
        self._extract_subs.extract_and_merge([FileToScan(dirpath, name)])

    def run(self):
        self._file_observer.start()
        logging.info(f"Start to listen new files in {self._target_path}")
        while not self.cease_continuous_run.is_set():
            self._event_handler.pending_watch_created_files()
            time.sleep(1)

    def __enter__(self):
        self.run()
        return self

    def stop(self):
        self.cease_continuous_run.set()
        self._file_observer.stop()
        self._file_observer.join()
        logging.info("File listener stopped")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


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
            with NewFilesListener(sub_extract, app_run_config.target_path):
                signal.pause()
