import json
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from json import JSONDecodeError
from typing import List


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
                         f"stderr: {result.stderr}, stdout: {result.stdout}")


def parse_mkvinfo(mkvinfo_str: str) -> List[MKVTrackInfo]:
    try:
        mkvinfo_json = json.loads(mkvinfo_str)
        mkv_tracks = mkvinfo_json.get('tracks', [])
        if not len(mkv_tracks):
            return []
        return [_extract_mkvinfo(track) for track in mkv_tracks]
    except JSONDecodeError:
        return []


def _extract_mkvinfo(track: dict) -> MKVTrackInfo:
    properties = track.get('properties', defaultdict(lambda: None))
    name = properties.get("track_name")
    track_type = track.get("type", None)
    track_number = track.get("id", None)
    language = properties.get("language")
    language_ietf = properties.get("language_ietf")
    return MKVTrackInfo(name, track_type, track_number, language, language_ietf, properties)
