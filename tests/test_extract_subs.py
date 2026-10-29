import os
import shutil
import tempfile
import unittest
from pathlib import Path

import pysubs2
from iso639 import languages

from extract_subs import ExtractSubs, AppRunConfig
from src.mergesubs import merge
from src.storage import Storage


class TestExtractSubs(unittest.TestCase):
    def test_merge_subtitles_on_current_python(self):
        with tempfile.TemporaryDirectory() as directory:
            top = Path(directory) / 'top.srt'
            bottom = Path(directory) / 'bottom.srt'
            output = Path(directory) / 'merged.ass'
            top.write_text('1\n00:00:01,000 --> 00:00:02,000\nTop subtitle\n', encoding='utf-8')
            bottom.write_text('1\n00:00:01,000 --> 00:00:02,000\nBottom subtitle\n', encoding='utf-8')

            merge(top, bottom, output)

            merged = pysubs2.load(str(output))
            self.assertEqual({(line.text, line.style) for line in merged},
                             {('Top subtitle', 'top'), ('Bottom subtitle', 'bot')})
            self.assertEqual(merged.styles['top'].alignment, 8)
            self.assertEqual(merged.styles['bot'].alignment, 2)

    def test_extract_subs(self):
        tmp_dir = tempfile.mkdtemp()

        file = os.path.join(tmp_dir, 'fragment.mkv')
        shutil.copyfile('fragment.mkv', file)
        with Storage(':memory:') as storage:
            app_run_config = AppRunConfig(tmp_dir, [languages.get(part1=x) for x in ['ru', 'en', 'fr']],
                                          [(languages.get(part1='ru'), languages.get(part1='en'))], ".*", {}, False,
                                          False)

            extract_subs = ExtractSubs(app_run_config, storage)
            extract_subs.scan_files()

            video_files = storage.get_all_video_files()
            self.assertEqual(1, len(video_files))
            fragment_file = video_files[0]
            subtitles = storage.get_all_subtitles_by_video_file_id(fragment_file['id'])
            self.assertEqual(5, len(subtitles))
            subtitles_file_names = set(os.path.basename(subtitle['full_path']) for subtitle in subtitles)
            self.assertEqual({'fragment_eng_SDH.srt', 'fragment_fra.srt', 'fragment.rus_eng.ass',
                              'fragment_rus_Forced.srt', 'fragment_rus.srt'}, subtitles_file_names)
            # 1 - cause forced subtitles is empty, file is empty, can't merge
            self.assertEqual(1, len(storage.get_all_merged_subtitles_by_video_file_id(fragment_file['id'])))

        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
