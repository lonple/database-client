from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dbc_askdata.config import Settings
from dbc_askdata.documents import ConvertError

log = logging.getLogger(__name__)

_IMG_ONLY = re.compile(r"!\[.*?]\(.*?\)", re.DOTALL)


def _set_opt(obj: Any, name: str, value: Any) -> None:
    if hasattr(obj, name):
        setattr(obj, name, value)


@dataclass
class ConvertOutcome:
    markdown: str
    asset_files: list[str]


def _strip_for_emptiness(md: str) -> str:
    t = _IMG_ONLY.sub("", md or "")
    return re.sub(r"\s+", "", t)


def convert_file(
    *,
    source: Path,
    pipeline: str,
    assets_dir: Path,
    asset_url_prefix: str,
    settings: Settings,
) -> ConvertOutcome:
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
    except ImportError as ex:
        raise ConvertError(
            "未安装 Docling。问数使用 .venv：若已装在宿主机 Python，将 "
            ".venv/pyvenv.cfg 中 include-system-site-packages 设为 true 后重启；"
            "或在虚拟环境执行 .\\.venv\\Scripts\\python.exe -m pip install -e \".[document]\""
        ) from ex

    pdf_opts = PdfPipelineOptions()
    _set_opt(pdf_opts, "do_ocr", pipeline == "IMAGE")
    _set_opt(pdf_opts, "do_table_structure", True)
    _set_opt(pdf_opts, "do_picture_description", False)
    _set_opt(pdf_opts, "do_picture_classification", False)
    _set_opt(pdf_opts, "do_chart_extraction", False)
    _set_opt(pdf_opts, "generate_picture_images", pipeline == "DOCUMENT")
    try:
        from docling.datamodel.pipeline_options import RapidOcrOptions

        if pipeline == "IMAGE" and hasattr(pdf_opts, "ocr_options"):
            pdf_opts.ocr_options = RapidOcrOptions()
    except Exception:
        log.debug("RapidOcrOptions 不可用，使用默认 OCR 配置", exc_info=True)

    fmt_opts: dict[Any, Any] = {
        InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_opts),
    }
    image_fmt = getattr(InputFormat, "IMAGE", None)
    if image_fmt is not None:
        fmt_opts[image_fmt] = PdfFormatOption(pipeline_options=pdf_opts)

    converter = DocumentConverter(format_options=fmt_opts)
    try:
        result = converter.convert(str(source))
    except Exception as ex:
        log.error("Docling 转换失败 path=%s", source, exc_info=True)
        raise ConvertError(f"转换失败: {ex}") from ex

    doc = result.document
    assets_dir.mkdir(parents=True, exist_ok=True)
    asset_files: list[str] = []
    pictures = getattr(doc, "pictures", None) or []
    for i, pic in enumerate(pictures, start=1):
        if pipeline != "DOCUMENT":
            break
        fname = f"pic-{i}.png"
        dest = assets_dir / fname
        saved = False
        img = getattr(pic, "image", None)
        pil = getattr(img, "pil_image", None) if img is not None else None
        if pil is None:
            pil = getattr(pic, "pil_image", None)
        if pil is not None:
            try:
                pil.save(dest, format="PNG")
                saved = dest.is_file()
            except Exception:
                log.error("保存抽出图片失败 index=%s", i, exc_info=True)
        if saved:
            asset_files.append(fname)

    try:
        md = doc.export_to_markdown()
    except Exception as ex:
        log.error("导出 Markdown 失败", exc_info=True)
        raise ConvertError(f"导出 Markdown 失败: {ex}") from ex

    md = md or ""
    for i, fname in enumerate(asset_files, start=1):
        url = f"{asset_url_prefix.rstrip('/')}/{fname}"
        md = md.replace(f"<!-- image -->", f"![图{i}]({url})", 1)

    if len(md) > settings.document_markdown_max_chars:
        raise ConvertError(f"转换结果超过 {settings.document_markdown_max_chars} 字符")

    leftover = _strip_for_emptiness(md)
    if pipeline == "DOCUMENT" and len(leftover) < 8:
        raise ConvertError("未抽出文本层。扫描版 PDF 本期不识别，请改传图片文件")
    if pipeline == "IMAGE" and len(leftover) < 2:
        raise ConvertError("图片中未识别到文字或表格")
    return ConvertOutcome(markdown=md, asset_files=asset_files)
