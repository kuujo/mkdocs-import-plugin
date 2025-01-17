import collections
import os
import os.path
import pathlib
import shutil
from pathlib import Path
from typing import IO, Mapping, Optional

from mkdocs.config import Config
from mkdocs.structure.files import File, Files


def file_sort_key(f: File):
    parts = pathlib.PurePath(f.src_path).parts
    return tuple(
        chr(f.name != "index" if i == len(parts) - 1 else 2) + p for i, p in enumerate(parts)
    )


class FileSystem:
    config: Config = None
    """The current MkDocs [config](https://www.mkdocs.org/user-guide/plugins/#config)."""
    directory: str = None
    """The base directory for `open()` ([docs_dir](https://www.mkdocs.org/user-guide/configuration/#docs_dir))."""
    edit_paths: Mapping[str, Optional[pathlib.Path]]

    def __init__(self, files: Files, config: Config, directory: Optional[str] = None):
        self._files = collections.ChainMap({}, {pathlib.Path(f.src_path): f for f in files})
        self.config = config
        if directory is None:
            directory = config["docs_dir"]
        self.directory = directory
        self.edit_paths = {}

    def open(self, name: Path, mode, buffering=-1, encoding=None, *args, **kwargs) -> IO:
        """Open a file under `docs_dir` virtually.

        This function, for all intents and purposes, is just an `open()` which pretends that it is
        running under [docs_dir](https://www.mkdocs.org/user-guide/configuration/#docs_dir)
        (*docs/* by default), but write operations don't affect the actual files when running as
        part of a MkDocs build, but they do become part of the site build.
        """
        path = self._get_file(name, new="w" in mode)
        if encoding is None and "b" not in mode:
            encoding = "utf-8"
        return open(path, mode, buffering, encoding, *args, **kwargs)

    def _get_file(self, name: Path, new: bool = False) -> str:
        new_f = File(
            name,
            src_dir=self.directory,
            dest_dir=self.config["site_dir"],
            use_directory_urls=self.config["use_directory_urls"],
        )

        if new or name not in self._files:
            os.makedirs(os.path.dirname(new_f.abs_src_path), exist_ok=True)
            self._files[name] = new_f
            self.edit_paths.setdefault(name, None)
            return new_f.abs_src_path

        f = self._files[name]
        if f.abs_src_path != new_f.abs_src_path:
            os.makedirs(os.path.dirname(new_f.abs_src_path), exist_ok=True)
            self._files[name] = new_f
            self.edit_paths.setdefault(name, None)
            shutil.copyfile(f.abs_src_path, new_f.abs_src_path)
            return new_f.abs_src_path

        return f.abs_src_path

    def set_edit_path(self, name: Path, edit_name: Optional[str]) -> None:
        """Choose a file path to use for the edit URI of this file."""
        self.edit_paths[name] = edit_name and str(edit_name)

    @property
    def files(self) -> Files:
        """Access the files as they currently are, as a MkDocs [Files][] collection.

        [Files]: https://github.com/mkdocs/mkdocs/blob/master/mkdocs/structure/files.py
        """
        files = sorted(self._files.values(), key=file_sort_key)
        return Files(files)
