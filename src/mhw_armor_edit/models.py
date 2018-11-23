# coding: utf-8
import errno
import logging
import os

from PyQt5.QtCore import (QObject, pyqtSignal)

from mhw_armor_edit.editor.models import FilePluginRegistry

log = logging.getLogger()


class WorkspaceFile(QObject):
    reloaded = pyqtSignal()

    def __init__(self, directory, rel_path, model, parent=None):
        super().__init__(parent)
        self.directory = directory
        self.rel_path = rel_path
        self.abs_path, _ = directory.get_child_path(self.rel_path)
        self.model = model

    def set_model(self, model):
        self.model = model
        self.reloaded.emit()

    def set_directory(self, directory):
        self.directory = directory
        self.abs_path, _ = directory.get_child_path(self.rel_path)

    def reload(self):
        self.model = self.directory.load_file_model(
            self.abs_path, self.rel_path)
        self.reloaded.emit()

    def save(self):
        self.directory.ensure_dirs(self.rel_path)
        with open(self.abs_path, "wb") as fp:
            self.model["model"].save(fp)

    def __repr__(self):
        return f"<WorkspaceFile {self.abs_path}>"

    def __hash__(self):
        return hash(self.directory) ^ hash(self.abs_path)


class Directory(QObject):
    changed = pyqtSignal(str)

    def __init__(self, name, file_icon, path, parent=None):
        super().__init__(parent)
        self.name = name
        self.file_icon = file_icon
        self.path = path

    def set_path(self, path):
        self.path = path
        self.changed.emit(path)

    @property
    def is_valid(self):
        return self.path is not None and os.path.exists(self.path)

    def get_child_path(self, rel_path):
        path = os.path.join(self.path, rel_path)
        exists = os.path.exists(path)
        return path, exists

    def get_child_rel_path(self, abs_path):
        return os.path.relpath(abs_path, self.path)

    def ensure_dirs(self, rel_path):
        abs_path, _ = self.get_child_path(rel_path)
        dir_path = os.path.dirname(abs_path)
        try:
            os.makedirs(dir_path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise


class Workspace(QObject):
    fileOpened = pyqtSignal(str, str)
    fileActivated = pyqtSignal(str, str)
    fileClosed = pyqtSignal(str, str)
    fileLoadError = pyqtSignal(str, str, str)

    def __init__(self, directories, parent=None):
        super().__init__(parent)
        self.directories = directories
        self.files = dict()

    def open_file(self, directory, abs_path):
        abs_path = os.path.normpath(abs_path)
        rel_path = directory.get_child_rel_path(abs_path)
        if abs_path in self.files:
            self.fileActivated.emit(abs_path, rel_path)
        else:
            try:
                model = FilePluginRegistry.load_model(abs_path, rel_path)
                FilePluginRegistry.load_relations(model, self.directories)
                self.files[abs_path] = WorkspaceFile(directory, rel_path, model)
                self.fileOpened.emit(abs_path, rel_path)
            except Exception as e:
                log.exception("error loading path: %s", abs_path)
                self.fileLoadError.emit(abs_path, rel_path, str(e))

    def close_file(self, ws_file):
        try:
            self.files.pop(ws_file.abs_path)
            self.fileClosed.emit(ws_file.abs_path, ws_file.rel_path)
        except (ValueError, KeyError):
            log.exception("error while closing file %s", ws_file)

    def transfer_file(self, ws_file, target_directory):
        if target_directory is ws_file.directory:
            return
        self.close_file(ws_file)
        ws_file.set_directory(target_directory)
        ws_file.save()
        self.open_file(target_directory, ws_file.abs_path)
