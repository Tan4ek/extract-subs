import json
import logging
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from tempfile import mktemp
from typing import List

_MKV_TRACK_TYPE_SUBTITLE = 'subtitles'


@dataclass
class MKVTrackInfo:
    # very useful information https://tools.ietf.org/id/draft-lhomme-cellar-matroska-04.html
    name: str
    track_type: str
    track_number: int
    language: str
    language_ietf: str
    _raw_properties: dict


def parse_mkvinfo_from_file(file_path: str) -> List[MKVTrackInfo]:
    result = subprocess.run(['mkvmerge', '-i', '-J', '--output-charset', 'UTF-8', '--ui-language', 'en_US', file_path],
                            stdout=subprocess.PIPE)
    # https://mkvtoolnix.download/doc/mkvmerge.html#mkvmerge.exit_codes
    if result.returncode in [0, 1]:
        return parse_mkvinfo(result.stdout.decode('utf-8'))
    else:
        raise ValueError(f"Can't extract info from file {file_path}. Exit code: {result.returncode}, "
                         f"stderr: {result.stderr.decode('utf-8')}, stdout: {result.stdout.decode('utf-8')}")


def parse_mkv_subtitles_info_from_file(file_path: str) -> List[MKVTrackInfo]:
    mkv_tracks_info = parse_mkvinfo_from_file(file_path)
    return [i for i in mkv_tracks_info if i.track_type == _MKV_TRACK_TYPE_SUBTITLE]


def parse_mkvinfo(mkvinfo_str: str) -> List[MKVTrackInfo]:
    try:
        mkvinfo_json = json.loads(mkvinfo_str)
        mkv_tracks = mkvinfo_json.get('tracks', [])
        if not len(mkv_tracks):
            return []
        return [_extract_mkvinfo(track) for track in mkv_tracks]
    except JSONDecodeError:
        return []


def parse_mkv_subtitles_info_from_str(mkvinfo_str: str) -> List[MKVTrackInfo]:
    mkv_tracks_info = parse_mkvinfo(mkvinfo_str)
    return [i for i in mkv_tracks_info if i.track_type == _MKV_TRACK_TYPE_SUBTITLE]


def _extract_mkvinfo(track: dict) -> MKVTrackInfo:
    properties = track.get('properties', defaultdict(lambda: None))
    name = properties.get("track_name")
    track_type = track.get("type", None)
    track_number = track.get("id", None)
    language = properties.get("language")
    language_ietf = properties.get("language_ietf")
    return MKVTrackInfo(name, track_type, track_number, language, language_ietf, properties)


def extract_mkv_tracks(mkv_file_path: str, tracks_info: List[dict]) -> bool:
    logging.info(f"Extracting embedded subtitles from file {mkv_file_path}")
    if not tracks_info and not len(tracks_info):
        return False

    def _track_to_srt_path(_tracks_info: List[dict]) -> List[str]:
        return [str(s['srt_track_id']) + ":" + s['srt_full_path'] for s in _tracks_info]

    tracks_to_srt_paths = _track_to_srt_path(tracks_info)
    temp_file = mktemp()
    command = ["mkvextract", "tracks", mkv_file_path,
               *tracks_to_srt_paths, '-r', temp_file, '--ui-language', 'en_US']
    result = subprocess.run(command, stdout=subprocess.PIPE)
    logging.info(f"tmp logs file: {temp_file}")
    # https://mkvtoolnix.download/doc/mkvextract.html#d4e1284
    if result.returncode not in [0, 1]:
        mkvextract_output = Path(temp_file).read_text()
        logging.info(f"Can't extract subtitles from file {mkv_file_path}. Exit code: {result.returncode}, "
                     f"stderr: {result.stderr}, stdout: {result.stdout}, output: {mkvextract_output}")
        return False
    else:
        return True
