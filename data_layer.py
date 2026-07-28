"""Data loading and indexing for the Food Safety MS Knowledge Base.

The Schema v2 data is intentionally kept in its source shape on disk.  This
module creates lightweight indexes and tabular projections for the Streamlit
application without mutating the source records.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import html
import json
import re

import pandas as pd


DATA_FILES = {
    "documents": "documents.json",
    "methods": "methods.json",
    "detections": "detections.json",
    "compounds": "compounds.json",
    "report": "data_report.json",
    "corrections": "corrections.json",
}


def field_value(field: Any) -> Any:
    """Return the value from a Schema v2 value/evidence object."""
    if isinstance(field, dict) and "value" in field:
        return field.get("value")
    return field


def field_evidence(field: Any) -> Any:
    """Return evidence text from a Schema v2 value/evidence object."""
    if isinstance(field, dict):
        return field.get("evidence")
    return None


def field_unit(field: Any) -> Any:
    """Return a unit from a Schema v2 measurement object."""
    if isinstance(field, dict):
        return field.get("unit")
    return None


def display_value(field: Any, default: str = "—") -> str:
    """Format a scalar or measurement object for compact display."""
    value = field_value(field)
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        text = "是" if value else "否"
    elif isinstance(value, (list, tuple, set)):
        text = "；".join(str(item) for item in value if item not in (None, ""))
    elif isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=False)
    elif isinstance(value, float):
        text = f"{value:g}"
    else:
        text = str(value)
    unit = field_unit(field)
    return f"{text} {unit}".strip() if unit else text


def plain_formula(formula: Any) -> str:
    """Convert CAS HTML formula markup into a plain chemical formula."""
    if not formula:
        return "—"
    text = re.sub(r"<[^>]+>", "", str(formula))
    return html.unescape(text).strip() or "—"


def normalize_region(country: Any, document_id: str = "") -> str:
    """Normalize heterogeneous source labels into useful browsing regions."""
    raw = str(country or "").strip()
    key = f"{raw} {document_id}".lower()
    if any(token in key for token in ("中国", "中华人民共和国", " china", "gb_")) or document_id.startswith("GB"):
        return "中国"
    if (
        any(token in key for token in ("日本", " japan", "jp_"))
        or document_id.startswith("JP_")
        or any(token in document_id for token in ("食安", "環境", "告示", "厚生", "平成", "試験法"))
    ):
        return "日本"
    if any(token in key for token in ("europe", "european union", "欧盟")) or document_id.startswith(("EN_", "CEN_")):
        return "欧盟/欧洲"
    if any(token in key for token in ("united states", " usa", "u.s.")) or document_id.startswith(("CLG-", "C-")):
        return "美国"
    if "australia" in key or "澳大利亚" in key:
        return "澳大利亚"
    return "其他/未标注"


def classify_platform(instrument: Any) -> str:
    """Collapse multilingual instrument descriptions into platform families."""
    text = str(instrument or "").strip()
    if not text:
        return "未标注"
    upper = text.upper()
    tandem = any(
        token in upper
        for token in ("MS/MS", "MS-MS", "MS2", "TANDEM", "QTRAP", "TRIPLE QUAD")
    ) or any(token in text for token in ("串联", "质谱/质谱", "タンデム"))
    has_ms = "MS" in upper or any(token in text for token in ("质谱", "質量分析"))
    is_gc = "GC" in upper or any(token in text for token in ("气相", "氣相", "ガスクロ"))
    is_lc = any(token in upper for token in ("LC", "HPLC", "UPLC", "UHPLC")) or any(
        token in text for token in ("液相", "液体クロマト", "高速液体")
    )
    is_ultra = any(token in upper for token in ("UPLC", "UHPLC"))

    if is_gc:
        if has_ms and tandem:
            return "GC-MS/MS"
        if has_ms:
            return "GC-MS"
        return "GC"
    if is_lc:
        if has_ms and tandem:
            return "UHPLC-MS/MS" if is_ultra else "LC-MS/MS"
        if has_ms:
            return "UHPLC-MS" if is_ultra else "LC-MS"
        return "HPLC/LC"
    if has_ms:
        return "其他 MS"
    return "其他分析平台"


def normalize_ms_level(level: Any) -> str:
    """Normalize the most common acquisition-level labels."""
    text = str(level or "").strip()
    if not text:
        return "未标注"
    upper = text.upper()
    if any(token in upper for token in ("MS2", "MS/MS", "MRM", "SRM")):
        return "MS/MS"
    if any(token in upper for token in ("MS1", "SIM")):
        return "MS / SIM"
    if upper in {"GC", "LC", "GC-ECD", "ECD"}:
        return "非 MS/其他"
    return "其他"


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_collection(data_dir: Path, name: str) -> list[dict[str, Any]]:
    payload = _load_json(data_dir / DATA_FILES[name])
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get(name), list):
        return payload[name]
    raise ValueError(f"{DATA_FILES[name]} 中未找到列表字段 {name!r}")


def _apply_document_corrections(
    documents: list[dict[str, Any]],
    corrections: dict[str, Any],
) -> None:
    """Apply reviewed metadata corrections while preserving raw JSON files."""
    documents_by_id = {record.get("document_id"): record for record in documents}
    for document_id, correction in (corrections.get("documents") or {}).items():
        document = documents_by_id.get(document_id)
        if document is None:
            raise ValueError(f"校正记录引用了不存在的文档 ID：{document_id}")
        for field, value in (correction.get("overrides") or {}).items():
            document[field] = value
        document["_correction"] = {
            key: value
            for key, value in correction.items()
            if key != "overrides"
        }


def data_signature(data_dir: str | Path) -> tuple[tuple[str, int, int], ...]:
    """Return a cache key that changes when any source file changes."""
    root = Path(data_dir)
    signature = []
    for filename in DATA_FILES.values():
        path = root / filename
        stat = path.stat()
        signature.append((filename, stat.st_size, stat.st_mtime_ns))
    return tuple(signature)


def build_knowledge_base(
    data_dir: str | Path,
    _signature: tuple[tuple[str, int, int], ...] | None = None,
) -> dict[str, Any]:
    """Load Schema v2 data and build indexes used by the application."""
    root = Path(data_dir)
    documents = _load_collection(root, "documents")
    methods = _load_collection(root, "methods")
    detections = _load_collection(root, "detections")
    compounds = _load_collection(root, "compounds")
    report = _load_json(root / DATA_FILES["report"])
    corrections = _load_json(root / DATA_FILES["corrections"])
    _apply_document_corrections(documents, corrections)

    documents_by_id = {record["document_id"]: record for record in documents}
    compounds_by_cas = {
        str(record["cas_number"]): record
        for record in compounds
        if record.get("cas_number")
    }

    method_meta: dict[tuple[str, str], dict[str, Any]] = {}
    for method in methods:
        document_id = str(method.get("document_id") or "")
        method_id = str(method.get("method_id") or method.get("run_config_id") or "")
        document = documents_by_id.get(document_id, {})
        country = field_value(document.get("issuing_country"))
        sample_info = method.get("sample_information") or {}
        ms_conditions = method.get("mass_spectrometry_conditions") or {}
        chromatography = method.get("chromatography_conditions") or {}
        matrix = (
            method.get("anchor_matrix")
            or field_value(sample_info.get("source"))
            or field_value(sample_info.get("partNature"))
            or "未标注"
        )
        instrument = (
            method.get("anchor_instrument")
            or field_value(ms_conditions.get("ms_instrument_model"))
            or field_value(chromatography.get("instrument_model"))
            or "未标注"
        )
        method_meta[(document_id, method_id)] = {
            "record": method,
            "region": normalize_region(country, document_id),
            "matrix": str(matrix),
            "instrument": str(instrument),
            "platform": classify_platform(instrument),
        }

    rows: list[dict[str, Any]] = []
    detection_lookup: dict[int, dict[str, Any]] = {}
    document_detection_counts: Counter[str] = Counter()
    method_detection_counts: Counter[tuple[str, str]] = Counter()
    document_compounds: defaultdict[str, set[str]] = defaultdict(set)

    row_id = 0
    for block in detections:
        document_id = str(block.get("document_id") or "")
        method_id = str(block.get("method_id") or "")
        document = documents_by_id.get(document_id, {})
        meta = method_meta.get((document_id, method_id), {})
        method = meta.get("record", {})
        document_name = (
            field_value(document.get("document_name"))
            or block.get("document_name")
            or document_id
        )
        original_document_id = (
            (document.get("_correction") or {}).get("display_id")
            or field_value(document.get("document_original_id"))
            or document_id
        )
        method_ms = method.get("mass_spectrometry_conditions") or {}

        for item in block.get("compound_detections") or []:
            cas_number = str(field_value(item.get("cas_number")) or "")
            english_name = str(item.get("canonical_english_name") or "")
            compound_name = str(field_value(item.get("compound_name")) or "")
            ms_level_raw = field_value(item.get("ms_level"))
            polarity = (
                field_value(item.get("polarity"))
                or field_value(method_ms.get("ionization_polarity"))
                or "未标注"
            )
            loq = display_value(item.get("limit_of_quantification"))
            retention_time = display_value(item.get("retention_time"))
            row = {
                "row_id": row_id,
                "化合物": english_name,
                "来源名称": compound_name,
                "CAS": cas_number,
                "document_id": document_id,
                "标准编号": str(original_document_id),
                "标准名称": str(document_name),
                "方法": method_id,
                "地区": meta.get("region", normalize_region(None, document_id)),
                "基质": meta.get("matrix", "未标注"),
                "平台": meta.get("platform", "未标注"),
                "仪器描述": meta.get("instrument", "未标注"),
                "MS 层级": normalize_ms_level(ms_level_raw),
                "MS 层级（原始）": str(ms_level_raw or "未标注"),
                "极性": str(polarity),
                "定量限": loq,
                "保留时间": retention_time,
            }
            row["search_blob"] = " ".join(
                str(row[key]).lower()
                for key in (
                    "化合物",
                    "来源名称",
                    "CAS",
                    "document_id",
                    "标准编号",
                    "标准名称",
                    "方法",
                    "基质",
                    "仪器描述",
                )
            )
            rows.append(row)
            detection_lookup[row_id] = {
                "item": item,
                "block": block,
                "method": method,
                "document": document,
                "compound": compounds_by_cas.get(cas_number, {}),
                "row": row,
            }
            document_detection_counts[document_id] += 1
            method_detection_counts[(document_id, method_id)] += 1
            if cas_number:
                document_compounds[document_id].add(cas_number)
            row_id += 1

    detections_df = pd.DataFrame(rows)

    document_method_counts = Counter(str(method.get("document_id") or "") for method in methods)
    document_rows = []
    for document in documents:
        document_id = str(document.get("document_id") or "")
        name = field_value(document.get("document_name")) or document_id
        original_id = (
            (document.get("_correction") or {}).get("display_id")
            or field_value(document.get("document_original_id"))
            or document_id
        )
        agency = field_value(document.get("issuing_agency")) or "未标注"
        country = field_value(document.get("issuing_country"))
        row = {
            "document_id": document_id,
            "标准编号": str(original_id),
            "标准名称": str(name),
            "地区": normalize_region(country, document_id),
            "发布机构": str(agency),
            "发布日期": display_value(document.get("publication_date")),
            "实施日期": display_value(document.get("implementation_date")),
            "类型": display_value(document.get("document_type")),
            "方法数": document_method_counts[document_id],
            "检测记录": document_detection_counts[document_id],
            "化合物数": len(document_compounds[document_id]),
        }
        row["search_blob"] = " ".join(
            str(row[key]).lower()
            for key in ("标准编号", "标准名称", "地区", "发布机构", "类型")
        )
        document_rows.append(row)
    documents_df = pd.DataFrame(document_rows)

    method_rows = []
    for (document_id, method_id), meta in method_meta.items():
        method = meta["record"]
        document = documents_by_id.get(document_id, {})
        method_rows.append(
            {
                "document_id": document_id,
                "标准编号": field_value(document.get("document_original_id")) or document_id,
                "方法": method_id,
                "基质": meta["matrix"],
                "平台": meta["platform"],
                "仪器描述": meta["instrument"],
                "检测记录": method_detection_counts[(document_id, method_id)],
            }
        )
    methods_df = pd.DataFrame(method_rows)

    return {
        "documents": documents,
        "methods": methods,
        "detections": detections,
        "compounds": compounds,
        "report": report,
        "corrections": corrections,
        "documents_by_id": documents_by_id,
        "compounds_by_cas": compounds_by_cas,
        "methods_by_key": {
            key: meta["record"] for key, meta in method_meta.items()
        },
        "method_meta": method_meta,
        "detection_lookup": detection_lookup,
        "detections_df": detections_df,
        "documents_df": documents_df,
        "methods_df": methods_df,
        "overview": {
            "regions": Counter(documents_df["地区"]),
            "platforms": Counter(methods_df["平台"]),
            "ms_levels": Counter(detections_df["MS 层级"]),
            "top_compounds": Counter(detections_df["化合物"]).most_common(12),
        },
    }
