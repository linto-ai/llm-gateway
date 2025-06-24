from watchdog.events import FileSystemEventHandler
import os
import time


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, file_extension, callback, debounce_period=1.0):
        self.file_extension = file_extension
        self.callback = callback
        self.debounce_period = debounce_period
        self.last_modified_time = 0

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(self.file_extension):
            current_time = time.time()
            if current_time - self.last_modified_time > self.debounce_period:
                filename = os.path.basename(event.src_path)
                self.last_modified_time = current_time
                self.callback(filename)