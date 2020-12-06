import json
import os
import shutil
import tempfile
import unittest
from random import shuffle

from iso639_json_parser import Iso639Decoder
from storage import Storage


def read_cache(file_path):
    cache_file_path = file_path

    if not os.path.isfile(cache_file_path):
        return {}

    with open(cache_file_path) as json_file:
        data = json.load(json_file, cls=Iso639Decoder)
        return data or {}


class TestStorage(unittest.TestCase):
    def test_migration(self):
        storage = Storage(':memory:')
        tmp_dir = tempfile.mkdtemp()

        _cache_file_path = os.path.join(tmp_dir, 'cache_sample.json')
        shutil.copyfile('cache_sample.json', _cache_file_path)

        storage._migrate_from_cache_file(_cache_file_path)

        all_video_files = storage.get_all_video_files()
        cache = read_cache(_cache_file_path)
        self.assertEqual(True, cache['migration_complete'])
        self.assertEqual(len(cache['files']), len(all_video_files))
        shuffle(cache['files'])
        for file in cache['files']:
            s_file = storage.get_video_file_by_full_path(file['full_path'])
            self.assertIsNotNone(s_file, f"For file path: {file['full_path']}")
            self.assertEqual(file['dir'].rstrip('/'), s_file['dir'])
            self.assertEqual(file['filename'], s_file['filename'])
            self.assertEqual(len(file['subtitles']) + len(file['merged_subtitles']),
                             len(storage.get_all_subtitles_by_video_file_id(s_file['id'])))


if __name__ == '__main__':
    unittest.main()
