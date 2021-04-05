from collections import namedtuple
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from iso639 import languages as iso639


@dataclass(frozen=True, eq=True)
class MKVTrackInfo:
    name: str
    track_type: str
    track_number: int
    language: str
    language_ietf: str
    _raw_properties: dict


@dataclass(frozen=True, eq=True)
class TrackMetadata:
    file_container_path: Path
    srt_track_id: int
    language_code: iso639
    track_info: MKVTrackInfo


@dataclass(frozen=True, eq=True)
class ScannedFile:
    filename: str
    basename: str
    extension: str
    dir: Path
    full_path: Path
    subtitles: List[TrackMetadata]


@dataclass(frozen=True, eq=True)
class ExtractedMKVTrack:
    metadata: TrackMetadata
    track_path: Path
    is_temp_file: bool = False

    def __hash__(self):
        return self.track_path.__hash__()


@dataclass(frozen=True, eq=True)
class ExtractMKVTrackIntent:
    track_id: int
    target_track_path: Path


@dataclass(frozen=True, eq=True)
class MergedSubtitle:
    top_track: ExtractedMKVTrack
    bot_track: ExtractedMKVTrack
    srt_path: Path


@dataclass(frozen=True, eq=True)
class ProcessedFile:
    scanned_file: ScannedFile
    extracted_tracks: List[ExtractedMKVTrack]
    merged_subtitles: List[MergedSubtitle] = field(default_factory=list)


@dataclass(frozen=True, eq=True)
class FileToScan:
    root: str
    filename: str


AppRunConfig = namedtuple('AppRunConfig', ['target_path', 'target_languages', 'merge_languages_pairs',
                                           'validation_regex', 'opensubtitles_auth', 'download_online',
                                           'listen_new'])
