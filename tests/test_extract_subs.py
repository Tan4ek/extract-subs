import os
import shutil
import tempfile
import unittest

from iso639 import languages

from extract_subs import main, CACHE


class MyTestCase(unittest.TestCase):
    def test_something(self):
        tmp_dir = tempfile.mkdtemp()

        file = os.path.join(tmp_dir, 'fragment.mkv')
        shutil.copyfile('fragment.mkv', file)

        main(tmp_dir, [languages.get(part1=x) for x in ['ru', 'en', 'fr']],
             [(languages.get(part1='ru'), languages.get(part1='en'))])

        cache_files = CACHE['files']
        self.assertEquals(1, len(cache_files))
        fragment_file = cache_files[0]
        self.assertEquals(10, len(fragment_file['subtitles']))
        self.assertEquals(2, len(fragment_file['merged_subtitles']))

        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
