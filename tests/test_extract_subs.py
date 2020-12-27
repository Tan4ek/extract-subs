import os
import shutil
import tempfile
import unittest

from iso639 import languages

from extract_subs import main
from storage import Storage


class TestExtractSubs(unittest.TestCase):
    def test_something(self):
        tmp_dir = tempfile.mkdtemp()

        file = os.path.join(tmp_dir, 'fragment.mkv')
        shutil.copyfile('fragment.mkv', file)
        storage = Storage(':memory:')

        main(tmp_dir, storage, [languages.get(part1=x) for x in ['ru', 'en', 'fr']],
             [(languages.get(part1='ru'), languages.get(part1='en'))], download_online=False)

        video_files = storage.get_all_video_files()
        self.assertEqual(1, len(video_files))
        fragment_file = video_files[0]
        self.assertEqual(10, len(storage.get_all_subtitles_by_video_file_id(fragment_file['id'])))
        # 1 - cause forced subtitles is empty, file is empty, can't merge
        self.assertEqual(1, len(storage.get_all_merged_subtitles_by_video_file_id(fragment_file['id'])))

        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
