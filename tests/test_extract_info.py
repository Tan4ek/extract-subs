import unittest

from extract_mkv_info import parse_mkvinfo, parse_mkvinfo_from_file


class MyTestCase(unittest.TestCase):
    def test_invalid_parse_format(self):
        with open('example_mkvinfo_output_1', 'r') as sub_file:
            sub_string = sub_file.read()
            parsed = parse_mkvinfo(sub_string)
            self.assertTrue(len(parsed) == 0)

    def test_parse_success(self):
        with open('example_mkvinfo_output_2', 'r') as sub_file:
            sub_string = sub_file.read()
            mkv_tracks_info = parse_mkvinfo(sub_string)
            self.assertTrue(len(mkv_tracks_info) > 0)
            subtitles_mkv_info = [i for i in mkv_tracks_info if i.track_type == 'subtitles']
            self.assertTrue(len(subtitles_mkv_info) > 0)

    def test_parse_file_success(self):
        mkv_tracks_info = parse_mkvinfo_from_file('tt-001.mkv')
        self.assertTrue(len(mkv_tracks_info) > 0)
        subtitles_mkv_info = [i for i in mkv_tracks_info if i.track_type == 'subtitles']
        self.assertTrue(len(subtitles_mkv_info) > 0)


if __name__ == '__main__':
    unittest.main()
