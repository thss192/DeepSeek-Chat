#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from watchdog.events import FileSystemEventHandler


class FileChangeHandler(FileSystemEventHandler):
    """文件系统变化处理器"""

    def __init__(self, file_explorer):
        self.file_explorer = file_explorer

    def on_any_event(self, event):
        """监听所有文件系统事件"""
        if not event.is_directory:
            self.file_explorer.schedule_refresh()