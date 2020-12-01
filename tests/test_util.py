import unittest

from extract_mkv_info import parse_mkvinfo
from util import bcp47_language_code_to_iso_639


class MyTestCase(unittest.TestCase):
    def test_bcp47_language_code_to_iso_639(self):
        with open('example_mkvinfo_output_2', 'r') as info_file:
            mkv_tracks_info = parse_mkvinfo(info_file.read())
            subtitles_mkv_info = [i for i in mkv_tracks_info if i.track_type == 'subtitles']
            for sub_info in subtitles_mkv_info:
                iso_639_code = bcp47_language_code_to_iso_639(sub_info.language_ietf)
                self.assertTrue(len(iso_639_code) >= 2)


if __name__ == '__main__':
    unittest.main()
