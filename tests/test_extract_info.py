import unittest

from extract_mkv_info import parse_mkvinfo, parse_mkvinfo_from_file, parse_mkv_subtitles_info_from_str


class MyTestCase(unittest.TestCase):
    def test_invalid_parse_format(self):
        with open('example_mkvinfo_output_1', 'r') as info_file:
            parsed = parse_mkvinfo(info_file.read())
            self.assertTrue(len(parsed) == 0)

    def test_parse_success(self):
        with open('example_mkvinfo_output_2', 'r') as info_file:
            mkv_tracks_info = parse_mkvinfo(info_file.read())
            self.assertTrue(len(mkv_tracks_info) > 0)
            subtitles_mkv_info = [i for i in mkv_tracks_info if i.track_type == 'subtitles']
            self.assertTrue(len(subtitles_mkv_info) > 0)

    def test_parse_file_success(self):
        mkv_tracks_info = parse_mkvinfo_from_file('tt-001.mkv')
        self.assertTrue(len(mkv_tracks_info) > 0)
        subtitles_mkv_info = [i for i in mkv_tracks_info if i.track_type == 'subtitles']
        self.assertTrue(len(subtitles_mkv_info) > 0)

    def test_parse_language_not_empty(self):
        with open('example_mkvinfo_output_2', 'r') as info_file:
            mkv_subtitles_info = parse_mkv_subtitles_info_from_str(info_file.read())
            for mkv_subtitle_info in mkv_subtitles_info:
                self.assertIsNotNone(mkv_subtitle_info.language)


if __name__ == '__main__':
    unittest.main()
