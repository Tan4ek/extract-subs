import os
import shutil
import tempfile
import time
import unittest
from collections import defaultdict

from watchdog.observers import Observer

from liste_files import FileFinallyCreatedEventHandler


class TestExtractSubs(unittest.TestCase):
    def test_watch_new_file(self):
        tmp_dir = tempfile.mkdtemp()

        created_file_count = defaultdict(lambda: 0)

        def _increment_counter(name: str, dir: str):
            created_file_count[os.path.join(dir, name)] += 1

        observer = Observer()
        file_watcher = FileFinallyCreatedEventHandler(['*.txt'], lambda name, dir: 'exclude' not in name,
                                                      _increment_counter, 1)
        observer.schedule(file_watcher, tmp_dir, recursive=True)
        observer.start()

        test_files = [os.path.join(tmp_dir, x) for x in ['test_0.txt', 'test_1.txt', 'java.script', 'exclude.txt']]
        for test_file_path in test_files:
            with open(test_file_path, 'w') as f:
                f.write('test ' + test_file_path)

        time.sleep(2)
        file_watcher.pending_watch_created_files()

        for test_file_path in test_files:
            if test_file_path.endswith('.txt') and 'exclude' not in test_file_path:
                self.assertEqual(1, created_file_count[test_file_path])
            else:
                self.assertEqual(0, created_file_count[test_file_path])

        observer.stop()
        observer.join()
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
