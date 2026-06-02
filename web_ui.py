"""
Gradio Web 管理界面
功能：文档入库、文档列表、检索、统计
启动方式：python web_ui.py
"""

import os
import sys
import re
import json
import copy
import threading
import base64
import mimetypes
import html as html_lib
import hashlib
from urllib.parse import urlparse


WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, WORKSPACE_ROOT)

import gradio as gr
import numpy as np
import faiss
from tqdm import tqdm
from scripts.db_manager import DatabaseManager, Corpus, Chunk
from scripts.manage_documents import DocumentManager
from scripts.add_documents import (
    DocumentProcessor,
    RESOURCE_DIRECTORY_NAMES,
    SUPPORTED_DOCUMENT_EXTENSIONS,
)
from scripts.bm25_indexer import BM25Indexer
from scripts.config_manager import get_config
from scripts.locales import LANGUAGE_CHOICES, normalize_lang, t


ACADEMIC_PRIMARY = gr.themes.Color(
    name="minir_blue",
    c50="#EFF6FF", c100="#DBEAFE", c200="#BFDBFE",
    c300="#93C5FD", c400="#60A5FA", c500="#3B82F6",
    c600="#2563EB", c700="#1D4ED8", c800="#1E40AF",
    c900="#1E3A8A", c950="#172554",
)

ACADEMIC_THEME = gr.themes.Default(
    primary_hue=ACADEMIC_PRIMARY,
    secondary_hue="slate",
).set(
    body_background_fill="#F6F8FB",
    background_fill_primary="#FFFFFF",
    background_fill_secondary="#F3F6FA",
    border_color_accent="#D6DEE8",
    shadow_spread="0",
)

ACADEMIC_CSS = """
.gradio-container { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif !important; }
h1, h2, h3, h4 { color: #111827; letter-spacing: 0; }
h1 { font-size: 1.8rem !important; font-weight: 700 !important; }
.markdown h1 { border-bottom: 1px solid #E5E7EB; padding-bottom: 8px; }
.tab-nav button { font-weight: 600 !important; }
.mr-header-row { align-items: start !important; gap: 16px !important; margin-bottom: 8px !important; }
.mr-app-title h1 { border-bottom: 0 !important; padding-bottom: 0 !important; margin: 0 !important; }
.mr-language-box { width: 260px !important; min-width: 240px !important; max-width: 280px !important; flex: 0 0 260px !important; margin-left: auto !important; }
.mr-language-box .form { padding: 10px 12px !important; }
table thead th { background-color: #F3F6FA !important; color: #111827 !important; font-weight: 600; }
.mr-overview { display: grid; gap: 12px; }
.mr-doc-group { border: 1px solid #D6DEE8; border-radius: 8px; overflow: hidden; background: #fff; }
.mr-doc-head { display: flex; justify-content: space-between; gap: 12px; padding: 10px 12px; background: #F3F6FA; border-bottom: 1px solid #D6DEE8; font-weight: 700; color: #111827; }
.mr-chunk-row { padding: 9px 12px; border-bottom: 1px solid #EEF2F7; }
.mr-chunk-row:last-child { border-bottom: 0; }
.mr-chunk-title { display: flex; align-items: center; justify-content: space-between; gap: 10px; color: #111827; font-weight: 650; }
.mr-chunk-title small { color: #64748B; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mr-status { background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; border-radius: 4px; padding: 1px 6px; font-size: 12px; }
.mr-chunk-meta { margin-top: 4px; color: #2563EB; font-size: 12px; }
.mr-snippet { margin-top: 4px; color: #475569; font-size: 13px; line-height: 1.5; }
.mr-current-preview, .mr-result-card { border: 1px solid var(--border-color-primary); border-radius: 8px; background: var(--background-fill-primary); overflow: hidden; margin-bottom: 12px; }
.mr-current-head, .mr-result-head { display: flex; justify-content: space-between; gap: 10px; padding: 10px 12px; background: var(--background-fill-secondary); border-bottom: 1px solid var(--border-color-primary); color: var(--body-text-color); font-weight: 700; }
.mr-current-head span, .mr-result-title { color: var(--body-text-color-subdued); font-size: 13px; font-weight: 500; }
.mr-current-body, .mr-result-body { padding: 12px; max-height: 420px; overflow: auto; background: var(--background-fill-primary); color: var(--body-text-color); font-size: 14px; line-height: 1.7; }
.mr-current-images { display: flex; flex-wrap: wrap; gap: 8px; padding: 10px 12px; border-top: 1px solid #E5E7EB; background: #F8FAFC; }
.mr-empty-images { color: #64748B; font-size: 13px; border: 1px solid #E5E7EB; border-radius: 8px; }
.mr-thumb { width: 104px; text-decoration: none; color: #475569; font-size: 12px; }
.mr-thumb img { width: 104px; height: 76px; object-fit: contain; display: block; border: 1px solid #D6DEE8; border-radius: 6px; background: #fff; }
.mr-thumb span { display: block; margin-top: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mr-ph-token { display: inline-block; padding: 1px 7px; margin: 0 2px; border-radius: 4px; background: #DBEAFE; border: 1px solid #93C5FD; color: #1D4ED8; font-size: 12px; font-weight: 650; white-space: nowrap; vertical-align: baseline; }
.mr-missing-image { display: inline-block; padding: 1px 7px; border-radius: 4px; background: #FEE2E2; color: #B91C1C; font-size: 12px; }
.mr-inline-image { display: block; width: fit-content; max-width: 100%; margin: 8px 0; cursor: zoom-in; }
.mr-inline-image img { display: block; max-width: min(100%, 720px); max-height: 420px; object-fit: contain; border: 1px solid #D6DEE8; border-radius: 6px; background: #fff; }
.mr-lightbox { display: none; position: fixed; inset: 0; z-index: 9999; background: rgba(15, 23, 42, 0.86); align-items: center; justify-content: center; padding: 24px; cursor: zoom-out; }
.mr-lightbox:target { display: flex; }
.mr-lightbox img { max-width: 92vw; max-height: 88vh; width: auto; height: auto; object-fit: contain; border-radius: 8px; background: #fff; box-shadow: 0 20px 60px rgba(0,0,0,0.35); }
.mr-lightbox-close { position: fixed; top: 18px; right: 24px; color: #fff; font-size: 32px; line-height: 1; font-weight: 700; }
.mr-result-head span { font-size: 15px; }
.mr-result-title { padding: 7px 12px; border-bottom: 1px solid #E5E7EB; }
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #EEF2F7; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #94A3B8; }
"""


def _muted_html(text):
    return f"<p style='color:#888;'>{html_lib.escape(text)}</p>"


def _empty_images_html(lang):
    return f"<div class='mr-current-images mr-empty-images'>{html_lib.escape(t('no_current_images', lang))}</div>"


def _is_new_status(status):
    return "新文档" in str(status) or "New document" in str(status)


def _is_existing_status(status):
    return "已入库" in str(status) or "Indexed" in str(status)


def _table_to_rows(table_data):
    if table_data is None:
        return []
    if hasattr(table_data, "empty") and table_data.empty:
        return []
    if isinstance(table_data, list):
        return table_data
    if hasattr(table_data, "values"):
        return table_data.values.tolist()
    return []


def _localize_scan_rows(table_data, lang):
    rows = []
    for row in _table_to_rows(table_data):
        next_row = list(row)
        if len(next_row) > 2:
            if _is_new_status(next_row[2]):
                next_row[2] = t("new_doc", lang)
            elif _is_existing_status(next_row[2]):
                next_row[2] = t("existing_doc", lang)
        rows.append(next_row)
    return rows


def _image_choice(index, lang):
    return f"图片{index}" if normalize_lang(lang) == "zh" else f"Image {index}"


def _chunk_option_label(chunk, index, lang):
    doc_name = chunk.get("doc_name", t("unknown_doc", lang))
    label = f"{doc_name} / {t('chunk_label_compact', lang, index=index + 1)}"
    if chunk.get("title"):
        label += f": {chunk.get('title')}"
    return label


_processor = None
_cached_db = None
_cached_dm = None
_retriever = None
_managers_lock = threading.Lock()


def _get_managers():
    global _cached_db, _cached_dm
    with _managers_lock:
        if _cached_db is None:
            try:
                print("[WebUI] 正在初始化数据库连接...")
                _cached_db = DatabaseManager()
                _cached_db.init_database()
                _cached_dm = DocumentManager(db=_cached_db)
                print("[WebUI] 数据库连接初始化完成")
            except Exception as e:
                print(f"[WebUI] 数据库连接失败: {e}")
                raise
    return _cached_db, _cached_dm


def _reset_managers():
    global _cached_db, _cached_dm, _processor, _retriever
    with _managers_lock:
        if _cached_db is not None:
            try:
                _cached_db.close()
            except Exception:
                pass
        _cached_db = None
        _cached_dm = None
        _processor = None
        _retriever = None


def _reset_retriever():
    global _retriever
    with _retriever_lock:
        _retriever = None


def _get_processor():
    global _processor
    if _processor is None:
        _processor = DocumentProcessor()
    return _processor


def _get_paths_from_table(table_data):
    if table_data is None:
        return []
    if hasattr(table_data, 'empty') and table_data.empty:
        return []
    if len(table_data) == 0:
        return []
    if isinstance(table_data, list):
        return [row[0] for row in table_data]
    return table_data.iloc[:, 0].tolist()


def _get_new_paths_from_table(table_data):
    if table_data is None:
        return []
    if hasattr(table_data, 'empty') and table_data.empty:
        return []
    if len(table_data) == 0:
        return []
    if isinstance(table_data, list):
        return [row[0] for row in table_data if len(row) > 2 and _is_new_status(row[2])]
    if table_data.shape[1] < 3:
        return table_data.iloc[:, 0].tolist()
    status_series = table_data.iloc[:, 2].astype(str)
    return table_data[status_series.apply(_is_new_status)].iloc[:, 0].tolist()


def scan_server_folder(folder_path, lang):
    if not folder_path:
        return t("enter_folder", lang), []
    folder_path = os.path.abspath(folder_path.strip())
    if not os.path.isdir(folder_path):
        return t("path_not_exist", lang), []
    print(f"[WebUI] 扫描文件夹: {folder_path}")

    doc_files = []
    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if d.lower() not in RESOURCE_DIRECTORY_NAMES]
        for f in sorted(files):
            if os.path.splitext(f)[1].lower() in SUPPORTED_DOCUMENT_EXTENSIONS:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, folder_path)
                doc_files.append((full_path, rel_path))

    if not doc_files:
        return t("no_md_files", lang) + f": {folder_path}", []

    rows = []
    try:
        db, _ = _get_managers()
    except Exception:
        db = None

    for full_path, rel_path in doc_files:
        doc_name = os.path.splitext(os.path.basename(full_path))[0]
        exists = False
        if db is not None:
            try:
                cfg = get_config()
                exists = db.get_corpus_by_path(full_path, cfg.to_relative_path(full_path)) is not None
            except Exception:
                exists = False
        status_mark = t("existing_doc", lang) if exists else t("new_doc", lang)
        rows.append([full_path, rel_path, status_mark])

    new_count = sum(1 for r in rows if _is_new_status(r[2]))
    exist_count = len(rows) - new_count
    print(f"[WebUI] 扫描完成，找到 {len(doc_files)} 个文件（新 {new_count}，已入库 {exist_count}）")
    info = t("found_files", lang, count=len(doc_files), new=new_count, exist=exist_count)
    return info, rows


_pending_chunks = []


def _render_preview_html(chunks_data, lang="zh"):
    if not chunks_data:
        return _muted_html(t("no_chunks", lang))

    doc_groups = {}
    for i, chunk in enumerate(chunks_data):
        doc_name = chunk.get("doc_name", t("unknown_doc", lang))
        if doc_name not in doc_groups:
            doc_groups[doc_name] = []
        doc_groups[doc_name].append((i, chunk))

    html = ["<div class='mr-overview'>"]
    for doc_idx, (doc_name, doc_chunks) in enumerate(doc_groups.items()):
        html.append(f"<div class='mr-doc-group'>")
        html.append(f"<div class='mr-doc-head'>")
        html.append(f"<span>{html_lib.escape(doc_name)}</span>")
        html.append(f"<span>{t('chunk_count', lang, count=len(doc_chunks))}</span>")
        html.append(f"</div>")

        for chunk_idx, chunk in doc_chunks:
            i = chunk_idx
            title = chunk.get("title", "")
            content = chunk.get("content", "")
            images_rel = chunk.get("images", [])
            original_content = chunk.get("original_content", "")
            original_images = chunk.get("original_images", [])
            modified = (original_content and original_content != content) or (original_images and original_images != images_rel)

            html.append(f"<div class='mr-chunk-row'>")
            html.append(f"<div class='mr-chunk-title'><span>{t('chunk_label', lang, index=i + 1)}</span>")
            if modified:
                html.append(f" <span class='mr-status'>{t('modified', lang)}</span>")
            if title:
                html.append(f"<small>{html_lib.escape(title)}</small>")
            html.append(f"</div>")
            if images_rel:
                html.append(f"<div class='mr-chunk-meta'>{t('image_count', lang, count=len(images_rel))}</div>")
            snippet = re.sub(r'\s+', ' ', content).strip()
            html.append(f"<div class='mr-snippet'>{html_lib.escape(snippet[:180])}{'...' if len(snippet) > 180 else ''}</div>")
            html.append(f"</div>")

        html.append(f"</div>")
    html.append("</div>")
    return "".join(html)


def _render_single_chunk_preview(chunk, lang="zh"):
    if not chunk:
        return _muted_html(t("select_chunk", lang))
    cfg = get_config()
    images = [cfg.to_absolute_path(p) for p in chunk.get("images", [])]
    file_dir = os.path.dirname(chunk.get("file_path", "")) if chunk.get("file_path") else None
    title = chunk.get("title", "")
    html = ["<div class='mr-current-preview'>"]
    html.append("<div class='mr-current-head'>")
    html.append(f"<strong>{html_lib.escape(chunk.get('doc_name', t('unknown_doc', lang)))}</strong>")
    if title:
        html.append(f"<span>{html_lib.escape(title)}</span>")
    html.append("</div>")
    html.append("<div class='mr-current-body'>")
    html.append(_render_content_html(chunk.get("content", ""), images, file_dir, show_placeholder_tags=True))
    html.append("</div>")
    if images:
        html.append("<div class='mr-current-images'>")
        for idx, img_path in enumerate(images):
            b64 = _image_to_base64(img_path)
            if not b64:
                continue
            html.append(_render_zoomable_image(b64, f"图片{idx}", img_path, idx, "mr-thumb"))
        html.append("</div>")
    html.append("</div>")
    return "".join(html)


def _render_chunk_images_html(chunk, lang="zh"):
    if not chunk:
        return _empty_images_html(lang)
    cfg = get_config()
    images = [cfg.to_absolute_path(p) for p in chunk.get("images", [])]
    valid_images = [(idx, img_path, _image_to_base64(img_path)) for idx, img_path in enumerate(images)]
    valid_images = [(idx, img_path, b64) for idx, img_path, b64 in valid_images if b64]
    if not valid_images:
        return _empty_images_html(lang)
    html = ["<div class='mr-current-images'>"]
    for idx, img_path, b64 in valid_images:
        name = html_lib.escape(os.path.basename(img_path))
        html.append(_render_zoomable_image(b64, f"{_image_choice(idx, lang)} {name}", img_path, idx, "mr-thumb"))
    html.append("</div>")
    return "".join(html)


def preview_chunks(table_data, chunk_strategy, chunk_size, overlap_ratio, lang):
    global _pending_chunks
    file_paths = _get_new_paths_from_table(table_data)
    if not file_paths:
        return _muted_html(t("scan_files", lang)), gr.update(visible=False), gr.update(visible=False), gr.update(choices=[], value=None), "", _empty_images_html(lang), json.dumps([])

    processor = _get_processor()
    processor.chunk_strategy = chunk_strategy
    processor.chunk_size = int(chunk_size) if chunk_size else 512
    processor.overlap_ratio = float(overlap_ratio) if overlap_ratio else 0.1

    if processor.append_mode:
        processor.load_existing_index()

    _pending_chunks = []

    for file_path in file_paths:
        doc_name = os.path.basename(file_path)
        try:
            content, doc_format, images, image_map = processor.read_file(file_path)
            if not content.strip():
                continue

            if chunk_strategy == "length":
                chunks_content = processor.split_by_length(content, processor.chunk_size, processor.overlap_ratio)
                sections = []
                for idx, chunk_content in enumerate(chunks_content):
                    chunk_images = processor._extract_images_from_content(chunk_content, file_path, images, doc_format, image_map)
                    sections.append({
                        "title": t("chunk_label", lang, index=idx + 1),
                        "title_level": 1,
                        "section_level": 1,
                        "content": chunk_content,
                        "images": chunk_images,
                        "title_path": ""
                    })
            else:
                sections = processor.parse_sections(content, doc_format, file_path, images, image_map)

            if not sections:
                continue

            for section in sections:
                chunk_text = section.get("content", "")
                if not chunk_text.strip():
                    continue
                _pending_chunks.append({
                    "doc_name": doc_name,
                    "file_path": file_path,
                    "title": section.get("title", ""),
                    "title_level": section.get("title_level", 0),
                    "content": chunk_text,
                    "original_content": chunk_text,
                    "images": section.get("images", []),
                    "original_images": list(section.get("images", [])),
                    "title_path": section.get("title_path", ""),
                })
        except Exception as e:
            print(f"  [预览] 读取 {doc_name} 失败: {e}")

    if not _pending_chunks:
        return _muted_html(t("no_generated_chunks", lang)), gr.update(visible=False), gr.update(visible=False), gr.update(choices=[], value=None), "", _empty_images_html(lang), json.dumps([])

    preview_html = _render_preview_html(_pending_chunks, lang)
    chunk_choices = [_chunk_option_label(chunk, i, lang) for i, chunk in enumerate(_pending_chunks)]

    return (
        preview_html,
        gr.update(visible=True),
        gr.update(visible=True),
        gr.update(choices=chunk_choices, value=chunk_choices[0] if chunk_choices else None),
        _pending_chunks[0]["content"] if _pending_chunks else "",
        _render_chunk_images_html(_pending_chunks[0] if _pending_chunks else None, lang),
        json.dumps(_pending_chunks, ensure_ascii=False),
    )


def _parse_chunk_idx(chunk_selection):
    if not chunk_selection:
        return -1
    match = re.search(r'(?:分片|chunk)\s*(\d+)', chunk_selection, flags=re.IGNORECASE)
    if match:
        return int(match.group(1)) - 1
    prefix = str(chunk_selection).split(":", 1)[0]
    nums = re.findall(r'(\d+)', prefix)
    if nums:
        return int(nums[-1]) - 1
    return -1


def _abs_images(image_list):
    cfg = get_config()
    return [cfg.to_absolute_path(p) for p in (image_list or [])]


def _sync_images_after_text_edit(chunk, new_content):
    old_content = chunk.get("content", "")
    old_images = list(chunk.get("images", []) or [])
    old_ph = [m.group(0) for m in _PLACEHOLDER_PATTERN.finditer(old_content)]
    new_ph = [m.group(0) for m in _PLACEHOLDER_PATTERN.finditer(new_content)]

    if new_ph:
        by_placeholder = {}
        for idx, ph in enumerate(old_ph):
            if idx < len(old_images):
                by_placeholder[ph] = old_images[idx]
        next_images = []
        for idx, ph in enumerate(new_ph):
            img = by_placeholder.get(ph)
            if img is None and idx < len(old_images):
                img = old_images[idx]
            if img and img not in next_images:
                next_images.append(img)
        chunk["images"] = next_images
        return

    inline_images = sorted(_iter_inline_image_matches(new_content), key=lambda item: item[1])
    if inline_images:
        cfg = get_config()
        file_dir = os.path.dirname(chunk.get("file_path", "")) if chunk.get("file_path") else ""
        next_images = []
        for _kind, _start, _end, _match, img_path, _label in inline_images:
            abs_path = _resolve_image_ref(img_path, file_dir)
            rel = cfg.to_relative_path(abs_path)
            if rel not in next_images:
                next_images.append(rel)
        chunk["images"] = next_images
        return

    chunk["images"] = []


def _on_chunk_selected(chunk_selection, chunks_json, lang):
    try:
        chunks_data = json.loads(chunks_json)
    except Exception:
        return "", _empty_images_html(lang), gr.update(choices=[], value=None)
    if not chunk_selection or not chunks_data:
        return "", _empty_images_html(lang), gr.update(choices=[], value=None)
    try:
        idx = _parse_chunk_idx(chunk_selection)
    except (ValueError, IndexError):
        return "", _empty_images_html(lang), gr.update(choices=[], value=None)
    if 0 <= idx < len(chunks_data):
        chunk = chunks_data[idx]
        img_choices = [_image_choice(i, lang) for i in range(len(chunk.get("images", [])))]
        return chunk.get("content", ""), _render_chunk_images_html(chunk, lang), gr.update(choices=img_choices, value=img_choices[0] if img_choices else None)
    return "", _empty_images_html(lang), gr.update(choices=[], value=None)


def _on_next_chunk(chunk_selection, chunks_json, lang):
    try:
        chunks_data = json.loads(chunks_json)
    except Exception:
        return gr.update(), "", _empty_images_html(lang), gr.update(choices=[], value=None)
    if not chunks_data:
        return gr.update(), "", _empty_images_html(lang), gr.update(choices=[], value=None)
    idx = _parse_chunk_idx(chunk_selection)
    next_idx = min(max(idx, -1) + 1, len(chunks_data) - 1)
    chunk = chunks_data[next_idx]
    label = _chunk_option_label(chunk, next_idx, lang)
    img_choices = [_image_choice(i, lang) for i in range(len(chunk.get("images", [])))]
    return gr.update(value=label), chunk.get("content", ""), _render_chunk_images_html(chunk, lang), gr.update(choices=img_choices, value=img_choices[0] if img_choices else None)


def _on_update_chunk(chunk_selection, new_content, chunks_json, lang):
    try:
        chunks_data = json.loads(chunks_json)
    except Exception:
        return chunks_json, _muted_html(t("update_failed", lang)), _empty_images_html(lang), gr.update(choices=[], value=None)
    if not chunk_selection or not chunks_data:
        return chunks_json, _muted_html(t("update_failed", lang)), _empty_images_html(lang), gr.update(choices=[], value=None)
    try:
        idx = _parse_chunk_idx(chunk_selection)
    except (ValueError, IndexError):
        return chunks_json, _muted_html(t("update_failed", lang)), _empty_images_html(lang), gr.update(choices=[], value=None)
    if 0 <= idx < len(chunks_data):
        _sync_images_after_text_edit(chunks_data[idx], new_content)
        chunks_data[idx]["content"] = new_content
        preview_html = _render_preview_html(chunks_data, lang)
        img_choices = [_image_choice(i, lang) for i in range(len(chunks_data[idx].get("images", [])))]
        return json.dumps(chunks_data, ensure_ascii=False), preview_html, _render_chunk_images_html(chunks_data[idx], lang), gr.update(choices=img_choices, value=img_choices[0] if img_choices else None)
    return chunks_json, _muted_html(t("update_failed", lang)), _empty_images_html(lang), gr.update(choices=[], value=None)


def _on_revert_chunk(chunk_selection, chunks_json, lang):
    try:
        chunks_data = json.loads(chunks_json)
    except Exception:
        return chunks_json, _muted_html(t("revert_failed", lang)), "", _empty_images_html(lang), gr.update(choices=[], value=None)
    if not chunk_selection or not chunks_data:
        return chunks_json, _muted_html(t("revert_failed", lang)), "", _empty_images_html(lang), gr.update(choices=[], value=None)
    try:
        idx = _parse_chunk_idx(chunk_selection)
    except (ValueError, IndexError):
        return chunks_json, _muted_html(t("revert_failed", lang)), "", _empty_images_html(lang), gr.update(choices=[], value=None)
    if 0 <= idx < len(chunks_data):
        original = chunks_data[idx].get("original_content")
        if original is not None:
            chunks_data[idx]["content"] = original
        original_images = chunks_data[idx].get("original_images")
        if original_images is not None:
            chunks_data[idx]["images"] = list(original_images)
        preview_html = _render_preview_html(chunks_data, lang)
        img_choices = [_image_choice(i, lang) for i in range(len(chunks_data[idx].get("images", [])))]
        return json.dumps(chunks_data, ensure_ascii=False), preview_html, chunks_data[idx]["content"], _render_chunk_images_html(chunks_data[idx], lang), gr.update(choices=img_choices, value=img_choices[0] if img_choices else None)
    return chunks_json, _muted_html(t("revert_failed", lang)), "", _empty_images_html(lang), gr.update(choices=[], value=None)


def _on_delete_chunk_image(chunk_selection, image_index, chunks_json, lang):
    try:
        chunks_data = json.loads(chunks_json)
    except Exception:
        return chunks_json, _muted_html(t("delete_failed", lang)), "", _empty_images_html(lang), gr.update(choices=[], value=None)
    if not chunk_selection or not chunks_data:
        return chunks_json, _muted_html(t("delete_failed", lang)), "", _empty_images_html(lang), gr.update(choices=[], value=None)
    try:
        idx = _parse_chunk_idx(chunk_selection)
    except (ValueError, IndexError):
        return chunks_json, _muted_html(t("delete_failed", lang)), "", _empty_images_html(lang), gr.update(choices=[], value=None)
    if 0 <= idx < len(chunks_data):
        images = chunks_data[idx].get("images", [])
        content = chunks_data[idx].get("content", "")
        img_idx = -1
        if isinstance(image_index, str) and (image_index.startswith("图片") or image_index.startswith("Image")):
            try:
                nums = re.findall(r'\d+', image_index)
                img_idx = int(nums[-1]) if nums else -1
            except ValueError:
                img_idx = -1
        elif isinstance(image_index, str):
            nums = re.findall(r'\d+', image_index)
            img_idx = int(nums[-1]) if nums else -1
        elif isinstance(image_index, (int, float)):
            img_idx = int(image_index)
        if 0 <= img_idx < len(images):
            images.pop(img_idx)
            chunks_data[idx]["images"] = images

            if _PLACEHOLDER_PATTERN.search(content):
                placeholders = list(_PLACEHOLDER_PATTERN.finditer(content))
                if img_idx < len(placeholders):
                    target_ph = placeholders[img_idx].group(0)
                    chunks_data[idx]["content"] = content.replace(target_ph, "")
            else:
                inline_imgs = sorted(_iter_inline_image_matches(content), key=lambda item: item[1])
                if img_idx < len(inline_imgs):
                    _kind, start, end, _match, _img_path, _label = inline_imgs[img_idx]
                    content = content[:start] + content[end:]
                    chunks_data[idx]["content"] = content

        preview_html = _render_preview_html(chunks_data, lang)
        img_choices = [_image_choice(i, lang) for i in range(len(chunks_data[idx].get("images", [])))]
        return json.dumps(chunks_data, ensure_ascii=False), preview_html, chunks_data[idx]["content"], _render_chunk_images_html(chunks_data[idx], lang), gr.update(choices=img_choices, value=img_choices[0] if img_choices else None)
    return chunks_json, _muted_html(t("delete_failed", lang)), "", _empty_images_html(lang), gr.update(choices=[], value=None)


def confirm_import(chunks_json, chunk_strategy, chunk_size, overlap_ratio, lang):
    global _pending_chunks
    try:
        chunks_data = json.loads(chunks_json)
    except Exception:
        return t("no_importable_chunks", lang)
    if not chunks_data:
        return t("no_importable_chunks", lang)

    processor = _get_processor()
    processor.chunk_strategy = chunk_strategy
    processor.chunk_size = int(chunk_size) if chunk_size else 512
    processor.overlap_ratio = float(overlap_ratio) if overlap_ratio else 0.1

    if processor.append_mode:
        processor.load_existing_index()

    results = []
    all_chunks = []
    docs_added = {}
    config = get_config()

    for chunk in chunks_data:
        file_path = chunk["file_path"]
        doc_name = chunk["doc_name"]
        doc_key = os.path.normcase(os.path.abspath(file_path))

        if doc_key not in docs_added:
            if processor._is_document_exists(file_path):
                results.append(t("doc_exists_skip", lang, doc_name=doc_name))
                continue
            corpus = Corpus(
                file_path=file_path,
                name=doc_name,
                type=t("doc_type", lang),
                data_summary=chunk.get("content", "")[:500],
                source=t("web_review_source", lang),
                relative_path=config.to_relative_path(file_path),
                chunk_strategy=chunk_strategy,
            )
            corpus_id = processor.db.add_corpus(corpus)
            docs_added[doc_key] = {"corpus_id": corpus_id, "chunk_count": 0}
        else:
            corpus_id = docs_added[doc_key]["corpus_id"]

        docs_added[doc_key]["chunk_count"] += 1
        chunk_index = docs_added[doc_key]["chunk_count"] - 1

        title_path = chunk.get("title_path", "")
        title = chunk.get("title", "")
        if title_path:
            chunk_text = f"{doc_name} > {title_path} > {title}\n{chunk['content']}"
        elif title:
            chunk_text = f"{doc_name} > {title}\n{chunk['content']}"
        else:
            chunk_text = f"{doc_name}\n{chunk['content']}"

        all_chunks.append({
            "corpus_id": corpus_id,
            "chunk_index": chunk_index,
            "content": chunk["content"],
            "title": chunk.get("title", ""),
            "title_level": chunk.get("title_level", 0),
            "images": chunk.get("images", []),
            "title_path": title_path,
            "chunk_text": chunk_text,
            "original_content": chunk.get("original_content", chunk["content"]),
        })

    for info in docs_added.values():
        processor.db.update_corpus_chunk_count(info["corpus_id"], info["chunk_count"])

    if not all_chunks:
        return t("no_valid_chunks", lang)

    try:
        chunk_texts = [c["chunk_text"] for c in all_chunks]
        dense_vecs, sparse_vecs = processor.generate_embeddings(chunk_texts)

        vector_id = processor.existing_vector_count

        for chunk in tqdm(all_chunks, desc=t("saving_chunks", lang)):
            chunk_record = Chunk(
                corpus_id=chunk["corpus_id"],
                chunk_index=chunk["chunk_index"],
                content=chunk["content"],
                title=chunk["title"],
                title_level=chunk["title_level"],
                images=chunk["images"],
                vector_id=vector_id,
                original_content=chunk.get("original_content"),
            )
            processor.db.add_chunk(chunk_record)
            corpus_info = processor.db.get_corpus_by_id(chunk["corpus_id"])
            processor.chunks_meta.append({
                "corpus_id": chunk["corpus_id"],
                "doc_name": os.path.basename(corpus_info.file_path) if corpus_info else "unknown",
                "title": chunk["title"],
                "title_level": chunk["title_level"],
                "images": chunk["images"],
            })
            processor.chunk_contents.append(chunk["chunk_text"])
            processor.chunk_images.append(chunk["images"])
            vector_id += 1

        if processor.append_mode and processor.existing_vector_count > 0:
            processor.dense_vectors = np.vstack([
                processor.faiss_index.reconstruct_n(0, processor.existing_vector_count),
                dense_vecs
            ])
            processor.sparse_vectors = processor.sparse_vectors + sparse_vecs
        else:
            processor.dense_vectors = dense_vecs
            processor.sparse_vectors = sparse_vecs

        processor.sparse_index = processor.build_sparse_index(processor.sparse_vectors)

        print(t("indexing_bm25", lang))
        if processor.append_mode and processor.existing_vector_count > 0:
            existing_bm25 = BM25Indexer(processor.faiss_index_path)
            if existing_bm25.load():
                new_ids = list(range(processor.existing_vector_count, processor.existing_vector_count + len(all_chunks)))
                existing_bm25.append_documents(chunk_texts, new_ids)
                processor.bm25_indexer = existing_bm25
            else:
                all_ids = list(range(len(processor.chunk_contents)))
                processor.bm25_indexer.build_index(processor.chunk_contents, all_ids)
        else:
            all_ids = list(range(len(processor.chunk_contents)))
            processor.bm25_indexer.build_index(processor.chunk_contents, all_ids)

        dimension = processor.dense_vectors.shape[1]
        processor.faiss_index = faiss.IndexFlatIP(dimension)
        processor.faiss_index.add(processor.dense_vectors)
        processor.save_faiss_index()
        _reset_retriever()

        results.append(t("import_done", lang, chunks=len(all_chunks), docs=len(docs_added), vectors=processor.faiss_index.ntotal))
    except Exception as e:
        for info in docs_added.values():
            try:
                processor.db.delete_corpus(info["corpus_id"])
            except Exception:
                pass
        results.append(t("index_update_failed", lang, error=str(e)))

    _pending_chunks = []
    return "\n".join(results)


def cancel_import(lang):
    global _pending_chunks
    _pending_chunks = []
    return (
        _muted_html(t("import_cancelled", lang)),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(choices=[], value=None),
        "",
        _empty_images_html(lang),
        json.dumps([]),
    )


def do_import(table_data, chunk_strategy, chunk_size, overlap_ratio, lang):
    file_paths = _get_new_paths_from_table(table_data)
    if not file_paths:
        return t("scan_files_first", lang)
    print(f"[WebUI] 入库: {len(file_paths)} 个文件")

    processor = _get_processor()
    processor.chunk_strategy = chunk_strategy
    processor.chunk_size = int(chunk_size) if chunk_size else 512
    processor.overlap_ratio = float(overlap_ratio) if overlap_ratio else 0.1

    if processor.append_mode:
        processor.load_existing_index()

    results = []
    all_chunks = []

    for file_path in file_paths:
        doc_name = os.path.basename(file_path)
        try:
            result = processor.process_document_web(
                file_path=file_path,
                tags=None,
            )
            if result["success"]:
                results.append(f"✅ {result['message']}")
                if result.get("chunks"):
                    all_chunks.extend(result["chunks"])
            else:
                results.append(f"⏭ {result['message']}")
        except Exception as e:
            results.append(f"❌ {doc_name}: {str(e)}")

    if all_chunks:
        try:
            chunk_texts = [c["chunk_text"] for c in all_chunks]
            dense_vecs, sparse_vecs = processor.generate_embeddings(chunk_texts)

            vector_id = processor.existing_vector_count

            for chunk in tqdm(all_chunks, desc="保存分片"):
                chunk_record = Chunk(
                    corpus_id=chunk["corpus_id"],
                    chunk_index=chunk["chunk_index"],
                    content=chunk["content"],
                    title=chunk["title"],
                    title_level=chunk["title_level"],
                    images=chunk["images"],
                    vector_id=vector_id,
                )

                processor.db.add_chunk(chunk_record)
                corpus_info = processor.db.get_corpus_by_id(chunk["corpus_id"])

                processor.chunks_meta.append({
                    "corpus_id": chunk["corpus_id"],
                    "doc_name": os.path.basename(corpus_info.file_path) if corpus_info else "unknown",
                    "title": chunk["title"],
                    "title_level": chunk["title_level"],
                    "images": chunk["images"],
                })
                processor.chunk_contents.append(chunk["chunk_text"])
                processor.chunk_images.append(chunk["images"])
                vector_id += 1

            if processor.append_mode and processor.existing_vector_count > 0:
                processor.dense_vectors = np.vstack([
                    processor.faiss_index.reconstruct_n(0, processor.existing_vector_count),
                    dense_vecs
                ])
                processor.sparse_vectors = processor.sparse_vectors + sparse_vecs
            else:
                processor.dense_vectors = dense_vecs
                processor.sparse_vectors = sparse_vecs

            processor.sparse_index = processor.build_sparse_index(processor.sparse_vectors)

            print(t("indexing_bm25", lang))
            if processor.append_mode and processor.existing_vector_count > 0:
                existing_bm25 = BM25Indexer(processor.faiss_index_path)
                if existing_bm25.load():
                    new_ids = list(range(processor.existing_vector_count, processor.existing_vector_count + len(all_chunks)))
                    existing_bm25.append_documents(chunk_texts, new_ids)
                    processor.bm25_indexer = existing_bm25
                else:
                    all_ids = list(range(len(processor.chunk_contents)))
                    processor.bm25_indexer.build_index(processor.chunk_contents, all_ids)
            else:
                all_ids = list(range(len(processor.chunk_contents)))
                processor.bm25_indexer.build_index(processor.chunk_contents, all_ids)

            dimension = processor.dense_vectors.shape[1]
            processor.faiss_index = faiss.IndexFlatIP(dimension)
            processor.faiss_index.add(processor.dense_vectors)
            processor.save_faiss_index()
            _reset_retriever()

            results.append("\n" + t("index_updated", lang, chunks=len(all_chunks), vectors=processor.faiss_index.ntotal))
        except Exception as e:
            for chunk in all_chunks:
                try:
                    processor.db.delete_corpus(chunk["corpus_id"])
                except Exception:
                    pass
            results.append("\n" + t("index_update_failed", lang, error=str(e)))

    return "\n".join(results)


def load_documents(keyword="", status_filter="全部", lang="zh"):
    global _cached_docs_data
    try:
        _, dm = _get_managers()
    except Exception as e:
        return [[f"{t('db_conn_fail', lang)}: {e}", "", ""]]
    docs = dm.list_documents(limit=500)
    if keyword:
        docs = [d for d in docs if keyword.lower() in d.get("name", "").lower()]

    filter_active = status_filter in ("启用", "Active")
    filter_inactive = status_filter in ("停用", "Inactive")

    rows = []
    for doc in docs:
        is_active = doc.get("is_active", True)
        if filter_active and not is_active:
            continue
        if filter_inactive and is_active:
            continue
        rows.append([
            doc["id"],
            doc["name"][:80],
            t("active_mark", lang) if is_active else t("inactive_mark", lang),
        ])
    _cached_docs_data = rows
    return rows


def delete_doc(corpus_id, lang):
    if not corpus_id:
        return t("enter_corpus_id", lang)
    try:
        _, dm = _get_managers()
    except Exception as e:
        return f"{t('db_conn_fail', lang)}: {e}"
    faiss_path = get_config().faiss_index_path
    success = dm.delete_document(corpus_id, confirm=False, faiss_index_path=faiss_path)
    if success:
        _reset_retriever()
    return f"{t('deleted', lang)}: {corpus_id}" if success else f"{t('delete_fail', lang)}: {corpus_id}"


def toggle_doc_status(corpus_id, lang):
    if not corpus_id:
        return t("enter_corpus_id", lang)
    try:
        db, dm = _get_managers()
    except Exception as e:
        return f"{t('db_conn_fail', lang)}: {e}"
    doc = dm.get_document_detail(corpus_id)
    if not doc:
        return f"{t('doc_not_found', lang)}: {corpus_id}"
    new_status = not doc.get("is_active", True)
    db.toggle_corpus_active(corpus_id)
    status_text = t("enabled", lang) if new_status else t("disabled", lang)
    return f"{status_text}: {corpus_id}"


def load_stats(lang):
    try:
        _, dm = _get_managers()
    except Exception as e:
        return f"{t('db_conn_fail', lang)}: {e}"
    stats = dm.get_statistics()
    lines = [
        f"{t('total_docs', lang)}: {stats.get('corpus', 0)}",
        f"{t('total_chunks', lang)}: {stats.get('chunks', 0)}",
    ]
    return "\n".join(lines)


_retriever_lock = threading.Lock()
_cached_docs_data = []


def _get_retriever():
    global _retriever
    with _retriever_lock:
        if _retriever is None:
            from scripts.retrieval_pipeline import RetrievalPipeline
            _retriever = RetrievalPipeline()
    return _retriever


def _image_to_base64(img_path):
    if _is_remote_image_path(img_path):
        return img_path.strip()
    if not img_path or not os.path.isfile(img_path):
        return None
    mime_type, _ = mimetypes.guess_type(img_path)
    if not mime_type:
        mime_type = "image/png"
    try:
        with open(img_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime_type};base64,{data}"
    except Exception:
        return None


def _image_lightbox_id(source_key, idx):
    raw = f"{source_key}:{idx}".encode("utf-8", errors="ignore")
    return "mr-img-" + hashlib.md5(raw).hexdigest()[:12]


def _render_zoomable_image(b64, label, source_key, idx, link_class):
    safe_label = html_lib.escape(label)
    safe_src = html_lib.escape(b64, quote=True)
    box_id = _image_lightbox_id(source_key, idx)
    return (
        f"<a href='#{box_id}' class='{link_class}' title='点击放大'>"
        f"<img src='{safe_src}' alt='{safe_label}' />"
        f"{f'<span>{safe_label}</span>' if link_class == 'mr-thumb' else ''}"
        f"</a>"
        f"<a href='#' id='{box_id}' class='mr-lightbox' title='点击关闭'>"
        f"<span class='mr-lightbox-close'>×</span>"
        f"<img src='{safe_src}' alt='{safe_label}' />"
        f"</a>"
    )


_IMG_PATTERN = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
_HTML_IMG_PATTERN = re.compile(r'<img\b[^>]*\bsrc=["\']?([^"\'\s>]+)[^>]*>', re.IGNORECASE)
_PLACEHOLDER_PATTERN = re.compile(r'<<IMAGE:([0-9a-f]+)>>')


def _is_remote_image_path(path):
    parsed = urlparse((path or "").strip())
    return parsed.scheme in {"http", "https", "data"}


def _clean_image_ref(img_ref):
    img_ref = (img_ref or "").strip()
    if img_ref.startswith("<") and img_ref.endswith(">"):
        img_ref = img_ref[1:-1].strip()
    return img_ref


def _resolve_image_ref(img_path, file_dir=None):
    img_path = _clean_image_ref(img_path)
    if _is_remote_image_path(img_path):
        return img_path
    if not os.path.isabs(img_path) and file_dir:
        return os.path.normpath(os.path.join(file_dir, img_path))
    return img_path


def _iter_inline_image_matches(content):
    for m in _IMG_PATTERN.finditer(content):
        yield ("md_img", m.start(), m.end(), m, m.group(2), m.group(1) or m.group(2))
    for m in _HTML_IMG_PATTERN.finditer(content):
        yield ("html_img", m.start(), m.end(), m, m.group(1), m.group(1))


def _render_content_html(content, images=None, file_dir=None, show_placeholder_tags=False):
    parts = []
    last_end = 0

    combined = []
    ph_counter = 0
    for m in _PLACEHOLDER_PATTERN.finditer(content):
        combined.append(('placeholder', m.start(), m.end(), m, ph_counter))
        ph_counter += 1
    md_img_counter = 0
    for kind, start, end, m, _img_path, _label in _iter_inline_image_matches(content):
        combined.append((kind, start, end, m, md_img_counter))
        md_img_counter += 1
    combined.sort(key=lambda x: x[1])

    for item in combined:
        kind, start, end, match, idx = item
        if start < last_end:
            continue
        text_before = content[last_end:start]
        if text_before:
            escaped = html_lib.escape(text_before).replace("\n", "<br>")
            parts.append(escaped)

        if kind == 'placeholder':
            ph_text = match.group(0)
            if show_placeholder_tags:
                parts.append(
                    f'<span class="mr-ph-token" title="{html_lib.escape(ph_text)}">图片{idx}</span>'
                )
            elif images is not None and 0 <= idx < len(images):
                b64 = _image_to_base64(images[idx])
                if b64:
                    parts.append(_render_zoomable_image(b64, f"图片{idx}", images[idx], idx, "mr-inline-image"))
                else:
                    parts.append(
                        f'<span class="mr-missing-image">{html_lib.escape(ph_text)}(缺失)</span>'
                    )
            elif images is not None:
                parts.append(
                    f'<span class="mr-missing-image">{html_lib.escape(ph_text)}(越界)</span>'
                )
            else:
                parts.append(
                    f'<span class="mr-ph-token">{html_lib.escape(ph_text)}</span>'
                )
        elif kind in ('md_img', 'html_img'):
            if kind == 'md_img':
                alt_text = match.group(1)
                img_path = match.group(2)
            else:
                alt_text = ""
                img_path = match.group(1)
            abs_path = _resolve_image_ref(img_path, file_dir)
            if not _is_remote_image_path(abs_path) and not os.path.isabs(abs_path) and images is not None and idx < len(images):
                abs_path = images[idx]
            b64 = _image_to_base64(abs_path)
            if b64:
                label = html_lib.escape(alt_text or img_path)
                if show_placeholder_tags:
                    parts.append(f"<span class='mr-ph-token' title='{html_lib.escape(img_path)}'>图片{idx}: {label}</span>")
                else:
                    parts.append(_render_zoomable_image(b64, label, abs_path, idx, "mr-inline-image"))
            else:
                parts.append(
                    f'<span class="mr-missing-image">{html_lib.escape(alt_text or img_path)}</span>'
                )

        last_end = end

    remaining = content[last_end:]
    if remaining:
        escaped = html_lib.escape(remaining).replace("\n", "<br>")
        parts.append(escaped)
    return "".join(parts)


def do_retrieve(query, top_k, use_rerank, lang):
    if not query or not query.strip():
        return t("enter_query", lang)
    query = query.strip()
    try:
        top_k = int(top_k) if top_k else 5
    except (ValueError, TypeError):
        top_k = 5

    use_rerank = (use_rerank in (t("yes", lang), "是", "Yes"))

    try:
        retriever = _get_retriever()
        result = retriever.retrieve(
            query=query,
            top_k=top_k,
            use_rerank=use_rerank,
            verbose=False,
        )

        docs = result.docs
        if not docs:
            return _muted_html(t("no_results", lang))

        html_parts = []
        for i, doc in enumerate(docs, 1):
            meta = doc.get("meta", {})
            doc_name = meta.get("doc_name", "Unknown")
            title = meta.get("title", "")
            content = doc.get("content", "")
            images = meta.get("images", [])
            score_info = ""
            if "rerank_score" in doc:
                score_info = f" <span style='color:#888;font-size:0.85em;'>(Rerank: {doc['rerank_score']:.4f})</span>"

            html_parts.append(f"<div class='mr-result-card'>")
            html_parts.append(f"<div class='mr-result-head'><span>{i}. {html_lib.escape(doc_name)}</span>{score_info}</div>")
            if title:
                html_parts.append(f"<div class='mr-result-title'>{t('result_title', lang)}: {html_lib.escape(title)}</div>")
            html_parts.append(f"<div class='mr-result-body'>")
            html_parts.append(_render_content_html(content, images))
            html_parts.append("</div>")
            html_parts.append("</div>")

        return "".join(html_parts)
    except Exception as e:
        import traceback
        return f"<p style='color:red;'>[ERROR] {html_lib.escape(str(e))}</p><pre>{html_lib.escape(traceback.format_exc())}</pre>"


def _on_doc_table_select(evt: gr.SelectData):
    try:
        if evt.index:
            row_idx = evt.index[0]
            docs_data = _cached_docs_data
            if docs_data and row_idx < len(docs_data):
                return str(docs_data[row_idx][0])
    except Exception:
        pass
    return ""


def reset_database_step1(lang):
    global _reset_code
    import secrets
    _reset_code = secrets.token_hex(4).upper()
    warn_text = t("reset_warning_text", lang, code=_reset_code)
    return warn_text, gr.update(visible=True)


def reset_database_step2(confirm_text, lang):
    global _reset_code
    confirm_value = (confirm_text or "").strip().upper()
    expected_code = globals().get("_reset_code", "")
    if not expected_code or confirm_value != expected_code:
        _reset_code = ""
        return t("confirm_wrong", lang), gr.update(visible=False)

    _reset_code = ""
    _reset_managers()

    try:
        import subprocess
        script_path = os.path.join(WORKSPACE_ROOT, "scripts", "reset_database.py")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
            cwd=WORKSPACE_ROOT,
            env=env,
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            error = result.stderr.strip()
            return f"[ERROR] Reset failed (exit code {result.returncode})\n\n{output}\n\n{error}", gr.update(visible=False)
        return output + f"\n\n{t('reset_done', lang)}", gr.update(visible=False)
    except subprocess.TimeoutExpired:
        return t("reset_timeout", lang), gr.update(visible=False)
    except Exception as e:
        return f"[ERROR] {e}", gr.update(visible=False)


with gr.Blocks(title="RAG 知识库管理", analytics_enabled=False) as app:
    ui_lang = gr.State("zh")
    with gr.Row(elem_classes=["mr-header-row"]):
        with gr.Column(scale=1, min_width=320):
            app_title_md = gr.Markdown(t("app_title"), elem_classes=["mr-app-title"])
        with gr.Column(scale=0, min_width=260, elem_classes=["mr-language-box"]):
            language_select = gr.Dropdown(
                choices=LANGUAGE_CHOICES,
                value="zh",
                label=t("language"),
            )

    with gr.Tabs():
        with gr.TabItem(t("tab_import")) as tab_import:
            import_desc_md = gr.Markdown(t("import_desc"))

            with gr.Row():
                server_folder = gr.Textbox(
                    label=t("folder_path"),
                    placeholder=t("folder_placeholder"),
                    scale=4,
                )
                scan_btn = gr.Button(t("scan_btn"), variant="secondary", scale=1)

            scan_info = gr.Textbox(label=t("scan_result"), interactive=False)
            server_file_table = gr.Dataframe(
                headers=[t("col_full_path"), t("col_rel_path"), t("col_status")],
                datatype=["str", "str", "str"],
                interactive=False,
                wrap=True,
                label=t("file_list"),
            )

            import_settings_md = gr.Markdown(t("import_settings"))
            with gr.Row():
                chunk_strategy = gr.Dropdown(
                    choices=["title", "length"],
                    value="length",
                    label=t("chunk_strategy"),
                    info=t("chunk_strategy_info")
                )
                with gr.Column(visible=True, scale=1) as length_params_col:
                    chunk_size = gr.Number(
                        value=512,
                        label=t("chunk_size"),
                        info=t("chunk_size_info"),
                    )
                    overlap_ratio = gr.Number(
                        value=0.1,
                        label=t("overlap_ratio"),
                        info=t("overlap_ratio_info"),
                    )

            def on_chunk_strategy_change(strategy):
                return gr.update(visible=(strategy == "length"))

            chunk_strategy.change(
                fn=on_chunk_strategy_change,
                inputs=chunk_strategy,
                outputs=[length_params_col],
            )

            import_btn = gr.Button(t("preview_btn"), variant="primary")
            preview_html = gr.HTML(visible=False)
            chunks_state = gr.State("[]")

            with gr.Column(visible=False) as edit_col:
                edit_panel_md = gr.Markdown(t("edit_panel"))
                with gr.Row():
                    chunk_selector = gr.Dropdown(label=t("chunk_select"), choices=[], scale=3)
                    btn_next_chunk = gr.Button(t("next_chunk"), variant="secondary", scale=1)
                with gr.Row():
                    edit_content = gr.Textbox(label=t("edit_content"), lines=14, scale=3)
                with gr.Row():
                    edit_images_html = gr.HTML(label=t("current_chunk_images"))
                with gr.Row():
                    img_delete_idx = gr.Dropdown(label=t("delete_image_index"), choices=[], scale=1)
                    btn_delete_img = gr.Button(t("delete_image_btn"), variant="secondary", scale=1)
                    btn_update_chunk = gr.Button(t("save_chunk"), variant="primary", scale=1)
                    btn_revert_chunk = gr.Button(t("revert_chunk"), variant="secondary", scale=1)

            with gr.Row(visible=False) as confirm_row:
                btn_confirm_import = gr.Button(t("confirm_import"), variant="primary")
                btn_cancel_import = gr.Button(t("cancel"), variant="secondary")
            import_log = gr.Textbox(label=t("import_log"), interactive=False, lines=6)

            scan_btn.click(
                fn=scan_server_folder,
                inputs=[server_folder, ui_lang],
                outputs=[scan_info, server_file_table],
            )

            import_btn.click(
                fn=preview_chunks,
                inputs=[server_file_table, chunk_strategy, chunk_size, overlap_ratio, ui_lang],
                outputs=[preview_html, edit_col, confirm_row, chunk_selector, edit_content, edit_images_html, chunks_state],
            )

            chunk_selector.change(
                fn=_on_chunk_selected,
                inputs=[chunk_selector, chunks_state, ui_lang],
                outputs=[edit_content, edit_images_html, img_delete_idx],
            )

            btn_next_chunk.click(
                fn=_on_next_chunk,
                inputs=[chunk_selector, chunks_state, ui_lang],
                outputs=[chunk_selector, edit_content, edit_images_html, img_delete_idx],
            )

            btn_update_chunk.click(
                fn=_on_update_chunk,
                inputs=[chunk_selector, edit_content, chunks_state, ui_lang],
                outputs=[chunks_state, preview_html, edit_images_html, img_delete_idx],
            )

            btn_delete_img.click(
                fn=_on_delete_chunk_image,
                inputs=[chunk_selector, img_delete_idx, chunks_state, ui_lang],
                outputs=[chunks_state, preview_html, edit_content, edit_images_html, img_delete_idx],
            )

            btn_revert_chunk.click(
                fn=_on_revert_chunk,
                inputs=[chunk_selector, chunks_state, ui_lang],
                outputs=[chunks_state, preview_html, edit_content, edit_images_html, img_delete_idx],
            )

            btn_confirm_import.click(
                fn=confirm_import,
                inputs=[chunks_state, chunk_strategy, chunk_size, overlap_ratio, ui_lang],
                outputs=import_log,
            )

            btn_cancel_import.click(
                fn=cancel_import,
                inputs=ui_lang,
                outputs=[preview_html, edit_col, confirm_row, chunk_selector, edit_content, edit_images_html, chunks_state],
            )

        with gr.TabItem(t("tab_docs")) as tab_docs:
            with gr.Row():
                doc_keyword = gr.Textbox(label=t("keyword_search"), placeholder=t("keyword_placeholder"))
                doc_status = gr.Dropdown(
                    choices=[t("all"), t("active"), t("inactive")],
                    value=t("all"), label=t("status_filter")
                )
                doc_refresh = gr.Button(t("refresh"), variant="secondary")

            doc_table = gr.Dataframe(
                headers=[t("col_id"), t("col_name"), t("col_state")],
                datatype=["str", "str", "str"],
                interactive=False,
                wrap=True,
            )

            with gr.Row():
                doc_id_input = gr.Textbox(label=t("doc_id"), placeholder=t("doc_id_placeholder"))
                btn_toggle = gr.Button(t("toggle_btn"), variant="secondary")
                btn_delete = gr.Button(t("delete_btn"), variant="stop")

            doc_action_msg = gr.Textbox(label=t("action_result"), interactive=False)

            doc_table.select(
                fn=_on_doc_table_select,
                inputs=None,
                outputs=doc_id_input,
            )
            doc_refresh.click(
                fn=load_documents,
                inputs=[doc_keyword, doc_status, ui_lang],
                outputs=doc_table,
            )
            doc_keyword.submit(
                fn=load_documents,
                inputs=[doc_keyword, doc_status, ui_lang],
                outputs=doc_table,
            )
            btn_delete.click(
                fn=delete_doc,
                inputs=[doc_id_input, ui_lang],
                outputs=doc_action_msg,
            )
            btn_toggle.click(
                fn=toggle_doc_status,
                inputs=[doc_id_input, ui_lang],
                outputs=doc_action_msg,
            )

        with gr.TabItem(t("tab_search")) as tab_search:
            search_desc_md = gr.Markdown(t("search_title"))
            with gr.Row():
                retrieve_query = gr.Textbox(
                    label=t("query_label"),
                    placeholder=t("query_placeholder"),
                    scale=4,
                )
            with gr.Row():
                retrieve_topk = gr.Slider(minimum=1, maximum=20, value=5, step=1, label=t("top_k"))
                retrieve_rerank = gr.Radio(choices=[t("yes"), t("no")], value=t("yes"), label=t("use_rerank"))
            with gr.Row():
                retrieve_btn = gr.Button(t("search_btn"), variant="primary")
                btn_clear_retrieve = gr.Button(t("clear_btn"), variant="secondary")
            retrieve_result = gr.HTML(label=t("search_result"))

            retrieve_btn.click(
                fn=do_retrieve,
                inputs=[retrieve_query, retrieve_topk, retrieve_rerank, ui_lang],
                outputs=retrieve_result,
            )
            btn_clear_retrieve.click(
                fn=lambda: ("", ""),
                outputs=[retrieve_query, retrieve_result],
            )

        with gr.TabItem(t("tab_system")) as tab_system:
            with gr.Tabs():
                with gr.TabItem(t("stats_tab")) as tab_stats:
                    stats_refresh = gr.Button(t("stats_refresh"), variant="secondary")
                    stats_text = gr.Textbox(label=t("stats_info"), interactive=False, lines=10)
                    stats_refresh.click(fn=load_stats, inputs=ui_lang, outputs=stats_text)

                with gr.TabItem(t("reset_tab")) as tab_reset:
                    reset_desc_md = gr.Markdown(t("reset_desc"))
                    btn_reset_step1 = gr.Button(t("reset_step1"), variant="stop")
                    reset_warning = gr.Textbox(label=t("reset_warning"), interactive=False)
                    with gr.Row(visible=False) as reset_confirm_row:
                        reset_confirm_text = gr.Textbox(label=t("confirm_code"), placeholder=t("confirm_placeholder"))
                        btn_reset_step2 = gr.Button(t("reset_step2"), variant="stop")
                    reset_result = gr.Textbox(label=t("reset_result"), interactive=False)

                    btn_reset_step1.click(
                        fn=reset_database_step1,
                        inputs=ui_lang,
                        outputs=[reset_warning, reset_confirm_row],
                    )
                    btn_reset_step2.click(
                        fn=reset_database_step2,
                        inputs=[reset_confirm_text, ui_lang],
                        outputs=[reset_result, reset_confirm_row],
                    )

    def on_language_change(lang, scan_table_data, doc_keyword_value, doc_status_value):
        lang = normalize_lang(lang)
        scan_rows = _localize_scan_rows(scan_table_data, lang)
        doc_rows = load_documents(doc_keyword_value or "", doc_status_value or t("all", lang), lang)
        return (
            lang,
            gr.update(value=t("app_title", lang)),
            gr.update(label=t("language", lang), value=lang),
            gr.update(label=t("tab_import", lang)),
            gr.update(label=t("tab_docs", lang)),
            gr.update(label=t("tab_search", lang)),
            gr.update(label=t("tab_system", lang)),
            gr.update(label=t("stats_tab", lang)),
            gr.update(label=t("reset_tab", lang)),
            gr.update(value=t("import_desc", lang)),
            gr.update(label=t("folder_path", lang), placeholder=t("folder_placeholder", lang)),
            gr.update(value=t("scan_btn", lang)),
            gr.update(label=t("scan_result", lang)),
            gr.update(
                value=scan_rows,
                headers=[t("col_full_path", lang), t("col_rel_path", lang), t("col_status", lang)],
                label=t("file_list", lang),
            ),
            gr.update(value=t("import_settings", lang)),
            gr.update(label=t("chunk_strategy", lang), info=t("chunk_strategy_info", lang)),
            gr.update(label=t("chunk_size", lang), info=t("chunk_size_info", lang)),
            gr.update(label=t("overlap_ratio", lang), info=t("overlap_ratio_info", lang)),
            gr.update(value=t("preview_btn", lang)),
            gr.update(value=t("edit_panel", lang)),
            gr.update(label=t("chunk_select", lang)),
            gr.update(value=t("next_chunk", lang)),
            gr.update(label=t("edit_content", lang)),
            gr.update(label=t("current_chunk_images", lang)),
            gr.update(label=t("delete_image_index", lang)),
            gr.update(value=t("delete_image_btn", lang)),
            gr.update(value=t("save_chunk", lang)),
            gr.update(value=t("revert_chunk", lang)),
            gr.update(value=t("confirm_import", lang)),
            gr.update(value=t("cancel", lang)),
            gr.update(label=t("import_log", lang)),
            gr.update(label=t("keyword_search", lang), placeholder=t("keyword_placeholder", lang)),
            gr.update(choices=[t("all", lang), t("active", lang), t("inactive", lang)], value=t("all", lang), label=t("status_filter", lang)),
            gr.update(value=t("refresh", lang)),
            gr.update(
                value=doc_rows,
                headers=[t("col_id", lang), t("col_name", lang), t("col_state", lang)],
            ),
            gr.update(label=t("doc_id", lang), placeholder=t("doc_id_placeholder", lang)),
            gr.update(value=t("toggle_btn", lang)),
            gr.update(value=t("delete_btn", lang)),
            gr.update(label=t("action_result", lang)),
            gr.update(value=t("search_title", lang)),
            gr.update(label=t("query_label", lang), placeholder=t("query_placeholder", lang)),
            gr.update(label=t("top_k", lang)),
            gr.update(choices=[t("yes", lang), t("no", lang)], value=t("yes", lang), label=t("use_rerank", lang)),
            gr.update(value=t("search_btn", lang)),
            gr.update(value=t("clear_btn", lang)),
            gr.update(label=t("search_result", lang)),
            gr.update(value=t("stats_refresh", lang)),
            gr.update(label=t("stats_info", lang)),
            gr.update(value=t("reset_desc", lang)),
            gr.update(value=t("reset_step1", lang)),
            gr.update(label=t("reset_warning", lang)),
            gr.update(label=t("confirm_code", lang), placeholder=t("confirm_placeholder", lang)),
            gr.update(value=t("reset_step2", lang)),
            gr.update(label=t("reset_result", lang)),
        )

    language_select.change(
        fn=on_language_change,
        inputs=[language_select, server_file_table, doc_keyword, doc_status],
        outputs=[
            ui_lang,
            app_title_md,
            language_select,
            tab_import,
            tab_docs,
            tab_search,
            tab_system,
            tab_stats,
            tab_reset,
            import_desc_md,
            server_folder,
            scan_btn,
            scan_info,
            server_file_table,
            import_settings_md,
            chunk_strategy,
            chunk_size,
            overlap_ratio,
            import_btn,
            edit_panel_md,
            chunk_selector,
            btn_next_chunk,
            edit_content,
            edit_images_html,
            img_delete_idx,
            btn_delete_img,
            btn_update_chunk,
            btn_revert_chunk,
            btn_confirm_import,
            btn_cancel_import,
            import_log,
            doc_keyword,
            doc_status,
            doc_refresh,
            doc_table,
            doc_id_input,
            btn_toggle,
            btn_delete,
            doc_action_msg,
            search_desc_md,
            retrieve_query,
            retrieve_topk,
            retrieve_rerank,
            retrieve_btn,
            btn_clear_retrieve,
            retrieve_result,
            stats_refresh,
            stats_text,
            reset_desc_md,
            btn_reset_step1,
            reset_warning,
            reset_confirm_text,
            btn_reset_step2,
            reset_result,
        ],
    )



ACADEMIC_PRIMARY = gr.themes.Color(
    name="minir_blue",
    c50="#EFF6FF", c100="#DBEAFE", c200="#BFDBFE",
    c300="#93C5FD", c400="#60A5FA", c500="#3B82F6",
    c600="#2563EB", c700="#1D4ED8", c800="#1E40AF",
    c900="#1E3A8A", c950="#172554",
)

ACADEMIC_THEME = gr.themes.Default(
    primary_hue=ACADEMIC_PRIMARY,
    secondary_hue="stone",
).set(
    body_background_fill="#F6F8FB",
    body_background_fill_dark="#111827",
    background_fill_primary="#FFFFFF",
    background_fill_secondary="#F3F6FA",
    border_color_accent="#D6DEE8",
    shadow_spread="0",
)

ACADEMIC_CSS = """
.gradio-container { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif !important; }
h1, h2, h3, h4 { color: #111827; letter-spacing: 0; }
h1 { font-size: 1.8rem !important; font-weight: 700 !important; }
h2 { font-size: 1.3rem !important; font-weight: 600 !important; }
h3 { font-size: 1.1rem !important; }
.markdown h1 { border-bottom: 1px solid #E5E7EB; padding-bottom: 8px; }
.tab-nav button { font-weight: 600 !important; }
.mr-header-row { align-items: start !important; gap: 16px !important; margin-bottom: 8px !important; }
.mr-app-title h1 { border-bottom: 0 !important; padding-bottom: 0 !important; margin: 0 !important; }
.mr-language-box { width: 260px !important; min-width: 240px !important; max-width: 280px !important; flex: 0 0 260px !important; margin-left: auto !important; }
.mr-language-box .form { padding: 10px 12px !important; }
table thead th { background-color: #F3F6FA !important; color: #111827 !important; font-weight: 600; }
.mr-overview { display: grid; gap: 12px; }
.mr-doc-group { border: 1px solid #D6DEE8; border-radius: 8px; overflow: hidden; background: #fff; }
.mr-doc-head { display: flex; justify-content: space-between; gap: 12px; padding: 10px 12px; background: #F3F6FA; border-bottom: 1px solid #D6DEE8; font-weight: 700; color: #111827; }
.mr-chunk-row { padding: 9px 12px; border-bottom: 1px solid #EEF2F7; }
.mr-chunk-row:last-child { border-bottom: 0; }
.mr-chunk-title { display: flex; align-items: center; justify-content: space-between; gap: 10px; color: #111827; font-weight: 650; }
.mr-chunk-title small { color: #64748B; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mr-status { background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; border-radius: 4px; padding: 1px 6px; font-size: 12px; }
.mr-chunk-meta { margin-top: 4px; color: #2563EB; font-size: 12px; }
.mr-snippet { margin-top: 4px; color: #475569; font-size: 13px; line-height: 1.5; }
.mr-current-preview, .mr-result-card { border: 1px solid var(--border-color-primary); border-radius: 8px; background: var(--background-fill-primary); overflow: hidden; margin-bottom: 12px; }
.mr-current-head, .mr-result-head { display: flex; justify-content: space-between; gap: 10px; padding: 10px 12px; background: var(--background-fill-secondary); border-bottom: 1px solid var(--border-color-primary); color: var(--body-text-color); font-weight: 700; }
.mr-current-head span, .mr-result-title { color: var(--body-text-color-subdued); font-size: 13px; font-weight: 500; }
.mr-current-body, .mr-result-body { padding: 12px; max-height: 420px; overflow: auto; background: var(--background-fill-primary); color: var(--body-text-color); font-size: 14px; line-height: 1.7; }
.mr-current-images { display: flex; flex-wrap: wrap; gap: 8px; padding: 10px 12px; border-top: 1px solid #E5E7EB; background: #F8FAFC; }
.mr-empty-images { color: #64748B; font-size: 13px; border: 1px solid #E5E7EB; border-radius: 8px; }
.mr-thumb { width: 104px; text-decoration: none; color: #475569; font-size: 12px; }
.mr-thumb img { width: 104px; height: 76px; object-fit: contain; display: block; border: 1px solid #D6DEE8; border-radius: 6px; background: #fff; }
.mr-thumb span { display: block; margin-top: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mr-ph-token { display: inline-block; padding: 1px 7px; margin: 0 2px; border-radius: 4px; background: #DBEAFE; border: 1px solid #93C5FD; color: #1D4ED8; font-size: 12px; font-weight: 650; white-space: nowrap; vertical-align: baseline; }
.mr-missing-image { display: inline-block; padding: 1px 7px; border-radius: 4px; background: #FEE2E2; color: #B91C1C; font-size: 12px; }
.mr-inline-image { display: block; width: fit-content; max-width: 100%; margin: 8px 0; cursor: zoom-in; }
.mr-inline-image img { display: block; max-width: min(100%, 720px); max-height: 420px; object-fit: contain; border: 1px solid #D6DEE8; border-radius: 6px; background: #fff; }
.mr-lightbox { display: none; position: fixed; inset: 0; z-index: 9999; background: rgba(15, 23, 42, 0.86); align-items: center; justify-content: center; padding: 24px; cursor: zoom-out; }
.mr-lightbox:target { display: flex; }
.mr-lightbox img { max-width: 92vw; max-height: 88vh; width: auto; height: auto; object-fit: contain; border-radius: 8px; background: #fff; box-shadow: 0 20px 60px rgba(0,0,0,0.35); }
.mr-lightbox-close { position: fixed; top: 18px; right: 24px; color: #fff; font-size: 32px; line-height: 1; font-weight: 700; }
.mr-result-head span { font-size: 15px; }
.mr-result-title { padding: 7px 12px; border-bottom: 1px solid #E5E7EB; }
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #EEF2F7; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #94A3B8; }
"""


def main():
    print("=" * 60)
    print("RAG 知识库管理界面")
    print("=" * 60)
    print("访问地址: http://localhost:8001")
    print("=" * 60)
    app.launch(
        server_name="127.0.0.1",
        server_port=8001,
        share=False,
        inbrowser=False,
        theme=ACADEMIC_THEME,
        css=ACADEMIC_CSS,
    )


if __name__ == "__main__":
    main()
