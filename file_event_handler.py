import logging
import os
from collections import namedtuple
from datetime import datetime
from typing import Callable, List

import schedule
from watchdog.events import PatternMatchingEventHandler, FileCreatedEvent

CreatedFile = namedtuple('created_file', ['path', 'timestamp', 'size'])


class FileFinallyCreatedEventHandler(PatternMatchingEventHandler):
    _CHECK_FILE_CHANGED_INTERVAL_SECONDS = 60

    def __init__(self, patterns: List[str], file_watcher_filter: Callable, on_file_create: Callable,
                 check_file_changed_interval_seconds: int = _CHECK_FILE_CHANGED_INTERVAL_SECONDS):
        super().__init__(patterns, ignore_directories=True, case_sensitive=False)
        self._created_files = dict()
        self._schedule = schedule.Scheduler()
        self._schedule.every(check_file_changed_interval_seconds).seconds.do(self._check_created_files)
        self._file_watcher_filter = file_watcher_filter
        self._on_file_create = on_file_create

    def _check_created_files(self):
        for src_path, created_file in self._created_files.copy().items():
            try:
                file_size = os.path.getsize(src_path)
                if created_file.size != file_size:
                    self._created_files[src_path] = CreatedFile(src_path, datetime.utcnow(), file_size)
                    logging.info(f"The file has changed its size {src_path}. Follow him further.")
                else:
                    dirpath = os.path.dirname(src_path)
                    name = os.path.basename(src_path)
                    logging.info(f"Call 'on_file_create' for {src_path}.")
                    self._on_file_create(name, dirpath)
                    self._created_files.pop(src_path)
            except Exception as e:
                logging.error(f"Callback on 'on_file_create' failed for file {src_path}. Error: {e}")

    def pending_watch_created_files(self):
        self._schedule.run_pending()

    def on_created(self, event: FileCreatedEvent):
        src_path = event.src_path
        dirpath = os.path.dirname(src_path)
        name = os.path.basename(src_path)
        logging.info(f"New file created {src_path}")
        if self._file_watcher_filter(name, dirpath):
            file_path = os.path.getsize(src_path)
            created_file = CreatedFile(src_path, datetime.utcnow(), file_path)
            self._created_files[src_path] = created_file
            logging.info(f"Handle new file {src_path}. Watching for change size.")
