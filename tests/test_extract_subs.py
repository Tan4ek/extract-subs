import os
import shutil
import tempfile
import unittest

from iso639 import languages

from extract_subs import ExtractSubs, AppRunConfig
from storage import Storage


class TestExtractSubs(unittest.TestCase):
    def test_something(self):
        tmp_dir = tempfile.mkdtemp()

        file = os.path.join(tmp_dir, 'fragment.mkv')
        shutil.copyfile('fragment.mkv', file)
        with Storage(':memory:') as storage:
            app_run_config = AppRunConfig(tmp_dir, [languages.get(part1=x) for x in ['ru', 'en', 'fr']],
                                          [(languages.get(part1='ru'), languages.get(part1='en'))], ".*", {}, False)

            extract_subs = ExtractSubs(app_run_config, storage)
            extract_subs.scan_files()

            video_files = storage.get_all_video_files()
            self.assertEqual(1, len(video_files))
            fragment_file = video_files[0]
            self.assertEqual(10, len(storage.get_all_subtitles_by_video_file_id(fragment_file['id'])))
            # 1 - cause forced subtitles is empty, file is empty, can't merge
            self.assertEqual(1, len(storage.get_all_merged_subtitles_by_video_file_id(fragment_file['id'])))

        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
