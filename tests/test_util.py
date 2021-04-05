import unittest
from pathlib import Path

from src.extract_mkv_info import parse_mkv_subtitles_info_from_str
from src.util import bcp47_language_code_to_iso_639_str, iso639_from_str, detect_iso639_from_str


class TestUtils(unittest.TestCase):
    def test_bcp47_language_code_to_iso_639(self):
        with open('example_mkvinfo_output_2', 'r') as info_file:
            subtitles_mkv_info = parse_mkv_subtitles_info_from_str(info_file.read())
            for sub_info in subtitles_mkv_info:
                iso_639_code = bcp47_language_code_to_iso_639_str(sub_info.language_ietf, default=sub_info.language)
                self.assertIsNotNone(iso_639_code)
                self.assertTrue(len(iso_639_code) >= 2)
                self.assertTrue(iso_639_code.islower())

    def test_iso639_from_str(self):
        self.assertIsNotNone(iso639_from_str('fre'))
        self.assertEqual(iso639_from_str('fre').name, "French")
        self.assertIsNotNone(iso639_from_str('fr'))
        self.assertEqual(iso639_from_str('fr').name, "French")
        self.assertIsNotNone(iso639_from_str('rus'))
        self.assertEqual(iso639_from_str('rus').name, "Russian")
        self.assertIsNotNone(iso639_from_str('ru'))
        self.assertEqual(iso639_from_str('ru').name, "Russian")
        self.assertIsNotNone(iso639_from_str('en'))
        self.assertEqual(iso639_from_str('en').name, "English")

    def test_detect_iso639(self):
        self.assertEqual(detect_iso639_from_str('und', Path('test_russian.srt')).name, 'Russian')
        self.assertEqual(detect_iso639_from_str('rus', Path('test_russian.srt')).name, 'Russian')
        self.assertEqual(detect_iso639_from_str('ru', Path('test_russian.srt')).name, 'Russian')
        self.assertEqual(detect_iso639_from_str('python', Path('test_russian.srt')).name, 'Russian')
        self.assertEqual(detect_iso639_from_str('und', Path('file_doesnt_exist.srt')).name, 'Undetermined')
        self.assertEqual(detect_iso639_from_str('python', Path('file_doesnt_exist.srt')), None)


if __name__ == '__main__':
    unittest.main()
