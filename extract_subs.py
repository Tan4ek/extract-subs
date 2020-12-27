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
import sys
from collections import namedtuple
from pathlib import Path
from typing import List, Set

from babelfish import Language
from iso639 import languages as iso639
from subliminal import save_subtitles, scan_video, region, download_best_subtitles, subtitle

import mergesubs
import util
from extract_mkv_info import parse_mkv_subtitles_info_from_file, extract_mkv_tracks
from storage import Storage

ScannedFile = namedtuple('ScanFile', ['filename', 'basename', 'extension', 'dir', 'full_path', 'subtitles',
                                      'merged_subtitles'])

FileToScan = namedtuple('FileToScan', ['root', 'filename'])

CACHE_FILE_NAME = '.extractsubs'
# dictionary, saving in root_path/CACHE_FILE_NAME
_SUPPORTED_FILE_EXTENSIONS = ['.mkv', '.mp4', '.avi', '.mpg', '.mpeg']

logging.basicConfig(level='INFO', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def download_subs(file: ScannedFile, download_subtitle_langs=None, opensubtitles_auth={}):
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
                                             provider_configs={'opensubtitles': opensubtitles_auth})
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


def extract_subs2(file: ScannedFile, opensubtitles_auth: dict, target_langs: list, download_online=True):
    logging.info("*****************************")
    logging.info(f"Directory: {file.dir}")
    logging.info(f"File: {file.filename}")
    logging.info("Embedded subtitles found.")
    extract_mkv_tracks(file.full_path, file.subtitles)
    extracted_languages = list(
        filter(lambda subtitle: subtitle['srt_lang_code'] is not None, file.subtitles))
    languages_to_download = list(filter(lambda lang: lang not in extracted_languages, target_langs))

    if download_online:
        download_subs(file, languages_to_download, opensubtitles_auth)


def merge_subs2(file: ScannedFile, merge_languages_pairs):
    if not merge_languages_pairs or not file:
        return

    def file_path_by_lang(file_subtitles: list, iso639_language: iso639) -> Set[str]:
        return {x['srt_full_path'] for x in file_subtitles if x['srt_lang_code'] is iso639_language}

    subtitles = file.subtitles if file.subtitles else []

    for merge_lang_pair in merge_languages_pairs:
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


def main(extr_path, storage: Storage, target_languages=[], merge_languages_pairs=[], validation_regex='.*',
         opensubtitles_auth={}, download_online=True):
    if not extr_path:
        logging.error("No directory supplied")
        sys.exit(1)
    if not os.path.isdir(extr_path) and not os.path.isfile(extr_path):
        sys.exit(f"Error, {extr_path} is not a directory or file")
    if download_online:
        cache_dir = os.path.join(os.getenv('HOME'), '.subliminal')
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        cache_file = os.path.join(cache_dir, 'subliminal.cachefile.dbm')
        # configure the cache
        region.configure('dogpile.cache.dbm', arguments={'filename': cache_file})
    validation = re.compile(validation_regex)

    def is_file_valid(name, root):
        (basename, ext) = os.path.splitext(name)
        is_not_system_folder = '/@Recycle' not in root and '/@Recently-Snapshot' not in root
        return ext in _SUPPORTED_FILE_EXTENSIONS and validation.match(name) is not None and is_not_system_folder

    def is_file_already_scanned(name, root):
        try:
            return storage.is_file_scanned(os.path.join(root, name))
        except Exception as e:
            logging.error(f"Download error {e}")
            return False

    def read_subtitles(file_to_scan: FileToScan) -> ScannedFile:
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
                    'srt_track_language': track_iso639_lang_code,
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

    def scrap_files_to_scan(extr_path: str) -> List[FileToScan]:
        files_to_scan = []
        if os.path.isdir(extr_path):
            for dirpath, dirs, files in os.walk(extr_path):
                for name in files:
                    if is_file_valid(name, dirpath) and not is_file_already_scanned(name, dirpath):
                        files_to_scan.append(FileToScan(dirpath, name))
        elif os.path.isfile(extr_path):
            dirpath = os.path.dirname(extr_path)
            name = os.path.basename(extr_path)
            if is_file_valid(name, dirpath) and not is_file_already_scanned(name, dirpath):
                files_to_scan.append(FileToScan(dirpath, name))
        return files_to_scan

    files_to_scan = scrap_files_to_scan(extr_path)

    scanned_files = [read_subtitles(file_to_scan) for file_to_scan in files_to_scan]

    for scanned_file in scanned_files:
        extract_subs2(scanned_file, opensubtitles_auth, target_languages, download_online)

    for scanned_file in scanned_files:
        merge_subs2(scanned_file, merge_languages_pairs)

    for scanned_file in scanned_files:
        save_scanned_files(scanned_file, storage)


def save_scanned_files(file: ScannedFile, storage: Storage):
    saved_video_file = storage.create_video_file(file.dir, file.filename)
    for file_subtitle in file.subtitles:
        storage.create_video_subtitle(saved_video_file['id'], file_subtitle['srt_full_path'],
                                      file_subtitle['srt_lang_code'].part3, file_subtitle['srt_track_id'],
                                      source='FILE')
    for merged_subtitles in file.merged_subtitles:
        lang_bot = merged_subtitles['lang_bot']
        lang_top = merged_subtitles['lang_top']
        storage.create_video_subtitle(saved_video_file['id'], merged_subtitles['srt_full_path'],
                                      f"{lang_top.part3},{lang_bot.part3}", None, 'Merge')


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


def parse_merge_langs(parameter):
    if parameter is None:
        return []
    languages_pairs = set(map(lambda pair: pair.strip(), parameter.split(',')))

    def parse_languages_pair_to_iso639_pair(languages_pair_str):
        languages_str = languages_pair_str.split('-')
        return list(map(lambda x: iso639.get(part1=x), languages_str))

    iso639_pairs = map(parse_languages_pair_to_iso639_pair, languages_pairs)
    iso639_pairs_filtered = filter(lambda pair: len(pair) == 2, iso639_pairs)
    return list(iso639_pairs_filtered)


def parse_languages(parameter):
    if parameter is None:
        return []
    languages = parameter.split(',')
    return list(set(map(lambda lang: iso639.get(part1=lang.strip()), languages)))


if __name__ == '__main__':
    def get_root_dir(path):
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
    parser.add_argument('--db-file', help='Fullpath to sqlite', type=str, default='.extract-subs.sqlite3')
    parser.add_argument('--no-download-subtitles-online', dest='download_online',
                        action='store_false', help='do not try to download missed subtitles online')
    parser.set_defaults(download_online=True)
    args = parser.parse_args()
    path = args.path
    validation_regex = args.validation_regex or '.*'
    opensubtitles = args.opensubtitles or ''
    opensubtitles_auth = parse_opensubtitles_parameters(opensubtitles)
    merge_languages_pairs = parse_merge_langs(args.merge_languages)
    target_languages = parse_languages(args.languages)

    storage = Storage(args.db_file)
    storage._migrate_from_cache_file(os.path.join(get_root_dir(path), CACHE_FILE_NAME))

    main(path, storage, target_languages, merge_languages_pairs, validation_regex, opensubtitles_auth,
         args.download_online)
