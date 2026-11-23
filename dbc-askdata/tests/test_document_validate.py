from __future__ import annotations

from pathlib import Path

from dbc_askdata.config import Settings
from dbc_askdata.documents import ConvertError
from dbc_askdata.documents.validate import validate_upload


def test_reject_exe(tmp_path: Path) -> None:
    settings = Settings(documents_dir=str(tmp_path))
    dest = tmp_path / "a.bin"
    try:
        validate_upload(
            filename="tool.exe",
            data=b"MZ" + b"\x00" * 32,
            dest=dest,
            settings=settings,
        )
        raise AssertionError("should fail")
    except ConvertError as ex:
        assert "可执行" in ex.message or "格式" in ex.message


def test_pdf_magic(tmp_path: Path) -> None:
    settings = Settings(documents_dir=str(tmp_path))
    dest = tmp_path / "a.pdf"
    pipeline, fmt = validate_upload(
        filename="a.pdf",
        data=b"%PDF-1.4\n%",
        dest=dest,
        settings=settings,
    )
    assert pipeline == "DOCUMENT"
    assert fmt == "pdf"


def test_png_image_pipeline(tmp_path: Path) -> None:
    settings = Settings(documents_dir=str(tmp_path))
    dest = tmp_path / "a.png"
    pipeline, fmt = validate_upload(
        filename="shot.png",
        data=b"\x89PNG\r\n\x1a\n" + b"\x00" * 8,
        dest=dest,
        settings=settings,
    )
    assert pipeline == "IMAGE"
    assert fmt == "png"
