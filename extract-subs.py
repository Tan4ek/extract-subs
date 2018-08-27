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

import sys
import os
import re
import subprocess
import argparse
from subliminal import save_subtitles, scan_video, region, download_best_subtitles
from babelfish import Language

from langdetect import detect


def get_mkv_tracks_id(file_path):
    """ Returns iterator of the track ID of the SRT subtitles track"""
    try:
        raw_info = subprocess.check_output(["mkvmerge", "-i", file_path],
                                           stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as ex:
        print(ex)
        sys.exit(1)
    pattern = re.compile('(\d+): subtitles \(SubRip/SRT\)', re.DOTALL)
    finder = pattern.finditer(str(raw_info))

    return map(lambda x: (raw_info, x.group(1)), finder)


def download_subs(file, download_subtitle_langs='eng'):
    print("    Analyzing video file...")
    try:
        video = scan_video(file['full_path'])
    except ValueError as ex:
        print("    Failed to analyze video. ", ex)
        return None
    print("    Choosing subtitle from online providers...")
    languages = set(map(lambda x: Language(x.strip()), download_subtitle_langs.split(',')))
    best_subtitles = download_best_subtitles({video}, languages, only_one=True)
    if best_subtitles[video]:
        print("    Downloading subtitles...")
        try:
            save_subtitles(video, best_subtitles[video])
        except:
            print("    ERROR: Download error {}".format(sys.exc_info()[0]))
    else:
        print("    ERROR: No subtitles found online.")


def extract_mkv_subs(file):
    print("    Extracting embedded subtitles...")
    try:
        srt_full_path = file['srt_full_path']
        subprocess.call(["mkvextract", "tracks", file['full_path'],
                         file['srt_track_id'] + ":" + srt_full_path])
        with open(srt_full_path, 'r') as sub_file:
            sub_string = sub_file.read().replace('\n', '')
            lang_code = detect(sub_string)
            if lang_code:
                os.rename(srt_full_path, re.sub('\.srt$', '.' + lang_code + '.srt', srt_full_path))
        print("    OK.")
    except subprocess.CalledProcessError:
        print("    ERROR: Could not extract subtitles")


def extract_subs(files, download_subtitle_langs):
    for file in files:
        print("*****************************")
        print("Directory: {d}".format(d=file['dir']))
        print("File: {f}".format(f=file['filename']))
        if file['srt_exists']:
            print("    Subtitles ready. Nothing to do.")
            continue
        if not file['srt_track_id']:
            print("    No embedded subtitles found.")
            download_subs(file, download_subtitle_langs)
        else:
            print("    Embedded subtitles found.")
            extract_mkv_subs(file)


def main(extr_path, validation_regex='*', download_subtitle_langs='eng'):
    supported_extensions = ['.mkv', '.mp4', '.avi', '.mpg', '.mpeg']
    if not extr_path:
        print("Error, no directory supplied")
        sys.exit(1)
    if not os.path.isdir(extr_path) and not os.path.isfile(extr_path):
        sys.exit("Error, {f} is not a directory or file".format(f=extr_path))
    global WDIR
    WDIR = extr_path
    cache_dir = os.path.join(os.getenv('HOME'), '.subliminal')
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    cache_file = os.path.join(cache_dir, 'subliminal.cachefile.dbm')
    # configure the cache
    region.configure('dogpile.cache.dbm', arguments={'filename': cache_file})
    file_list = []
    validation = re.compile(validation_regex)

    def is_file_valid(name, root):
        (basename, ext) = os.path.splitext(name)
        is_not_system_folder = '/@Recycle' not in root and '/@Recently-Snapshot' not in root
        return ext in supported_extensions and validation.match(name) is not None and is_not_system_folder

    def read_subtitles(name, root):
        (basename, ext) = os.path.splitext(name)
        if ext == '.mkv':
            for (raw_track_info, track_id) in get_mkv_tracks_id(os.path.join(root, name)):
                srt_full_path = os.path.join(root, basename + ".srt")
                srt_exists = os.path.isfile(srt_full_path)
                file_list.append({'filename': name,
                                  'basename': basename,
                                  'extension': ext,
                                  'dir': root,
                                  'full_path': os.path.join(root, name),
                                  'srt_track_id': track_id,
                                  'srt_full_path': srt_full_path,
                                  'srt_exists': srt_exists,
                                  'raw_info': raw_track_info
                                  })
        else:
            srt_full_path = os.path.join(root, basename + ".srt")
            srt_exists = os.path.isfile(srt_full_path)
            file_list.append({'filename': name,
                              'basename': basename,
                              'extension': ext,
                              'dir': root,
                              'full_path': os.path.join(root, name),
                              'srt_track_id': None,
                              'srt_full_path': srt_full_path,
                              'srt_exists': srt_exists,
                              'raw_info': None
                              })
    if os.path.isdir(WDIR):
        for root, dirs, files in os.walk(WDIR):
            for name in files:
                if is_file_valid(name, root):
                    read_subtitles(name, root)
    elif os.path.isfile(WDIR):
        root = os.path.dirname(WDIR)
        name = os.path.basename(WDIR)
        if is_file_valid(name, root):
            read_subtitles(name, root)

    extract_subs(file_list, download_subtitle_langs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path', help='extracting path to a folder or to a file', type=str)
    parser.add_argument('--validation-regex', help='validation folders/files regex', type=str)
    parser.add_argument('--download-subtitle-langs',
                        help='languages for download subtitles. String of 3-letter ISO-639-3 language code separated '
                             'by ,',
                        type=str)
    args = parser.parse_args()
    path = args.path
    validation_regex = args.validation_regex
    download_subtitle_langs = args.download_subtitle_langs
    if validation_regex is None:
        validation_regex = '.*'
    if download_subtitle_langs is None:
        download_subtitle_langs = 'eng'
    main(path, validation_regex, download_subtitle_langs)
