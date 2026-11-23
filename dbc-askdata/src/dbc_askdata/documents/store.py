from __future__ import annotations

import logging
import shutil
from pathlib import Path

from dbc_askdata.config import Settings

log = logging.getLogger(__name__)


class FileStore:
    """本地目录存储。TODO(production): 架构概要 §6 换对象存储。"""

    def __init__(self, settings: Settings) -> None:
        self.root = settings.resolved_documents_dir()
        self.root.mkdir(parents=True, exist_ok=True)

    def doc_dir(self, owner_user_id: int, doc_id: int) -> Path:
        return self.root / str(owner_user_id) / str(doc_id)

    def source_path(self, owner_user_id: int, doc_id: int, ext: str) -> Path:
        d = self.doc_dir(owner_user_id, doc_id)
        d.mkdir(parents=True, exist_ok=True)
        return d / f"source.{ext}"

    def assets_dir(self, owner_user_id: int, doc_id: int) -> Path:
        d = self.doc_dir(owner_user_id, doc_id) / "assets"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def relpath(self, path: Path) -> str:
        return path.resolve().relative_to(self.root.resolve()).as_posix()

    def abs_from_rel(self, rel: str) -> Path:
        if ".." in Path(rel).as_posix().split("/"):
            raise ValueError("非法路径")
        p = (self.root / rel).resolve()
        try:
            p.relative_to(self.root.resolve())
        except ValueError as ex:
            raise ValueError("非法路径") from ex
        return p

    def wipe_assets(self, owner_user_id: int, doc_id: int) -> None:
        d = self.doc_dir(owner_user_id, doc_id) / "assets"
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)

    def remove_doc(self, owner_user_id: int, doc_id: int) -> None:
        d = self.doc_dir(owner_user_id, doc_id)
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
