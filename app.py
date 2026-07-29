from __future__ import annotations

from pathlib import Path
from typing import Any
import base64
import html
import json

import pandas as pd
import streamlit as st

from data_layer import (
    build_knowledge_base,
    data_signature,
    display_value,
    field_evidence,
    field_value,
    plain_formula,
)


st.set_page_config(
    page_title="Food Safety MS Knowledge Base",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)


DATA_DIR = Path(__file__).resolve().parent / "data"


@st.cache_resource(show_spinner=False)
def load_knowledge_base(
    data_dir: str,
    signature: tuple[tuple[str, int, int], ...],
) -> dict[str, Any]:
    return build_knowledge_base(data_dir, signature)


def safe(value: Any) -> str:
    return html.escape(str(value if value not in (None, "") else "—"))


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #102a2f;
            --muted: #60777b;
            --line: #dbe7e4;
            --paper: #f5f8f6;
            --white: #ffffff;
            --green: #087f6a;
            --green-dark: #07584d;
            --lime: #d9f06b;
            --amber: #f4b942;
        }
        .stApp {
            background:
                radial-gradient(circle at 90% -10%, rgba(217, 240, 107, .16), transparent 28rem),
                #f7faf8;
            color: var(--ink);
        }
        [data-testid="stSidebar"] {
            background: #0b272b;
            border-right: 0;
        }
        [data-testid="stSidebar"] * {
            color: #edf7f3;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label {
            border: 1px solid rgba(255,255,255,.09);
            border-radius: 12px;
            padding: .55rem .7rem;
            margin-bottom: .4rem;
            transition: background .15s ease, border-color .15s ease;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: rgba(255,255,255,.07);
            border-color: rgba(217,240,107,.35);
        }
        [data-testid="stSidebar"] hr {
            border-color: rgba(255,255,255,.12);
        }
        .block-container {
            max-width: 1500px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        h1, h2, h3 {
            letter-spacing: -.025em;
            color: var(--ink);
        }
        .brand {
            padding: .75rem .15rem 1.15rem;
        }
        .brand-mark {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 42px;
            height: 42px;
            border-radius: 13px;
            background: var(--lime);
            color: #0b272b !important;
            font-weight: 900;
            margin-bottom: .8rem;
        }
        .brand-name {
            color: #ffffff !important;
            font-size: 1.07rem;
            line-height: 1.35;
            font-weight: 760;
        }
        .brand-sub {
            color: #9fb5b4 !important;
            font-size: .78rem;
            margin-top: .35rem;
        }
        .side-status {
            margin-top: 1.25rem;
            padding: .85rem;
            border: 1px solid rgba(217,240,107,.22);
            background: rgba(217,240,107,.06);
            border-radius: 13px;
            font-size: .78rem;
            line-height: 1.55;
            color: #c9d9d6 !important;
        }
        .status-dot {
            display: inline-block;
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--amber);
            margin-right: 7px;
            box-shadow: 0 0 0 4px rgba(244,185,66,.12);
        }
        .hero {
            position: relative;
            overflow: hidden;
            background: #0d3034;
            color: #f5fffb;
            border-radius: 24px;
            padding: 2.25rem 2.4rem 2.1rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 18px 50px rgba(20,55,55,.12);
        }
        .hero:after {
            content: "";
            position: absolute;
            width: 290px;
            height: 290px;
            right: -75px;
            top: -100px;
            border-radius: 50%;
            border: 45px solid rgba(217,240,107,.13);
        }
        .hero-kicker {
            position: relative;
            z-index: 1;
            color: var(--lime);
            font-size: .75rem;
            font-weight: 800;
            letter-spacing: .14em;
            text-transform: uppercase;
            margin-bottom: .8rem;
        }
        .hero h1 {
            position: relative;
            z-index: 1;
            max-width: 940px;
            color: #ffffff;
            font-size: clamp(2rem, 4vw, 3.65rem);
            line-height: 1.02;
            margin: 0 0 .85rem;
        }
        .hero p {
            position: relative;
            z-index: 1;
            color: #bed0ce;
            max-width: 790px;
            font-size: 1rem;
            line-height: 1.7;
            margin: 0;
        }
        .hero-badge {
            position: relative;
            z-index: 1;
            display: inline-block;
            margin-top: 1.15rem;
            border: 1px solid rgba(255,255,255,.15);
            background: rgba(255,255,255,.06);
            border-radius: 999px;
            padding: .38rem .72rem;
            color: #e4efed;
            font-size: .74rem;
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: .8rem;
            margin: 1rem 0 1.8rem;
        }
        .metric-card {
            background: var(--white);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 1rem 1.05rem;
            min-height: 105px;
            box-shadow: 0 6px 18px rgba(31,70,65,.035);
        }
        .metric-value {
            font-size: 1.75rem;
            line-height: 1.1;
            font-weight: 820;
            color: var(--green-dark);
        }
        .metric-label {
            margin-top: .42rem;
            color: var(--muted);
            font-size: .78rem;
        }
        .section-note {
            color: var(--muted);
            font-size: .87rem;
            margin-top: -.5rem;
            margin-bottom: .9rem;
        }
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: .85rem;
            margin: 1rem 0;
        }
        .feature-card {
            border: 1px solid var(--line);
            background: rgba(255,255,255,.72);
            border-radius: 16px;
            padding: 1.1rem;
        }
        .feature-no {
            color: var(--green);
            font-size: .72rem;
            font-weight: 850;
            letter-spacing: .08em;
        }
        .feature-card h4 {
            color: var(--ink);
            margin: .45rem 0 .35rem;
            font-size: 1rem;
        }
        .feature-card p {
            color: var(--muted);
            font-size: .82rem;
            line-height: 1.6;
            margin: 0;
        }
        .detail-head {
            background: #ffffff;
            border: 1px solid var(--line);
            border-left: 5px solid var(--green);
            border-radius: 16px;
            padding: 1.15rem 1.25rem;
            margin: 1rem 0;
        }
        .detail-head h2 {
            font-size: 1.55rem;
            margin: 0 0 .3rem;
        }
        .detail-head p {
            margin: 0;
            color: var(--muted);
            font-size: .85rem;
        }
        .info-panel {
            height: 100%;
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 15px;
            padding: 1rem 1.05rem;
        }
        .info-panel .eyebrow {
            color: var(--green);
            font-size: .7rem;
            font-weight: 850;
            text-transform: uppercase;
            letter-spacing: .09em;
        }
        .info-panel .primary {
            color: var(--ink);
            font-size: 1.02rem;
            font-weight: 760;
            line-height: 1.35;
            margin: .4rem 0 .55rem;
        }
        .info-panel .secondary {
            color: var(--muted);
            font-size: .78rem;
            line-height: 1.55;
        }
        .tag {
            display: inline-block;
            border-radius: 999px;
            padding: .25rem .55rem;
            margin: .25rem .22rem .1rem 0;
            background: #edf5f1;
            color: var(--green-dark);
            font-size: .71rem;
            font-weight: 720;
        }
        .param-card {
            min-height: 77px;
            border: 1px solid var(--line);
            border-radius: 13px;
            background: #ffffff;
            padding: .72rem .82rem;
            margin-bottom: .65rem;
        }
        .param-label {
            display: block;
            color: var(--muted);
            font-size: .7rem;
            margin-bottom: .3rem;
        }
        .param-value {
            color: var(--ink);
            font-size: .88rem;
            line-height: 1.45;
            font-weight: 660;
            word-break: break-word;
        }
        .draft-alert {
            border: 1px solid #ecd9ad;
            border-left: 5px solid var(--amber);
            border-radius: 14px;
            background: #fffaf0;
            padding: 1rem 1.1rem;
            color: #644c1e;
            line-height: 1.65;
            margin: .85rem 0 1.2rem;
        }
        .footer {
            margin-top: 2.8rem;
            padding-top: 1rem;
            border-top: 1px solid var(--line);
            color: #7a8d8e;
            font-size: .73rem;
        }
        [data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 13px;
            overflow: hidden;
        }
        [data-testid="stMetric"] {
            border: 1px solid var(--line);
            border-radius: 13px;
            padding: .8rem;
            background: white;
        }
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div {
            border-color: #ccdcda;
            background: #ffffff;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: .35rem;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px 10px 0 0;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        @media (max-width: 900px) {
            .metric-grid { grid-template-columns: repeat(2, 1fr); }
            .feature-grid { grid-template-columns: 1fr; }
            .hero { padding: 1.65rem 1.35rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(kicker: str, title: str, description: str, badge: str) -> None:
    st.markdown(
        f"""
        <section class="hero">
            <div class="hero-kicker">{safe(kicker)}</div>
            <h1>{safe(title)}</h1>
            <p>{safe(description)}</p>
            <span class="hero-badge">{safe(badge)}</span>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_metric_cards(cards: list[tuple[str, str]]) -> None:
    # Keep the fragment compact: indented HTML after a blank line is Markdown code.
    markup = "".join(
        (
            '<div class="metric-card">'
            f'<div class="metric-value">{safe(value)}</div>'
            f'<div class="metric-label">{safe(label)}</div>'
            "</div>"
        )
        for value, label in cards
    )
    st.markdown(f'<div class="metric-grid">{markup}</div>', unsafe_allow_html=True)


def render_panel(eyebrow: str, primary: str, secondary: str, tags: list[str] | None = None) -> None:
    tag_markup = "".join(f'<span class="tag">{safe(tag)}</span>' for tag in (tags or []) if tag)
    st.markdown(
        f"""
        <div class="info-panel">
            <div class="eyebrow">{safe(eyebrow)}</div>
            <div class="primary">{safe(primary)}</div>
            <div class="secondary">{safe(secondary)}</div>
            <div>{tag_markup}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_correction_notice(document: dict[str, Any]) -> None:
    correction = document.get("_correction") or {}
    if not correction:
        return
    st.info(
        f"人工复核校正：{correction.get('reason', '该文档元数据已人工复核。')} "
        f"源文件：{correction.get('source_file', '未记录')}"
    )


def value_exists(field: Any) -> bool:
    value = field_value(field)
    return value not in (None, "", [], {})


def render_parameter_section(
    record: dict[str, Any],
    fields: list[tuple[str, str]],
    show_evidence: bool,
) -> None:
    available = [(key, label, record.get(key)) for key, label in fields if value_exists(record.get(key))]
    if not available:
        st.info("这一部分暂无结构化参数。")
        return
    columns = st.columns(2)
    for index, (_, label, field) in enumerate(available):
        with columns[index % 2]:
            st.markdown(
                f"""
                <div class="param-card">
                    <span class="param-label">{safe(label)}</span>
                    <div class="param-value">{safe(display_value(field))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            evidence = field_evidence(field)
            if show_evidence and evidence:
                st.caption(f"原文：{evidence}")


SAMPLE_FIELDS = [
    ("source", "样品来源"),
    ("partNature", "样品/组织类型"),
    ("other_information", "样品补充信息"),
]

PREP_FIELDS = [
    ("homogenization_method", "均质方法"),
    ("pre_extraction_storage_temp", "提取前储存温度"),
    ("pre_extraction_storage_duration", "提取前储存时间"),
    ("extraction_solvent", "提取溶剂"),
    ("extraction_solvent_volume", "提取溶剂体积"),
    ("extraction_replicates", "提取次数"),
    ("extraction_time", "提取时间"),
    ("centrifugation_conditions", "离心条件"),
    ("cleanup_method", "净化方法"),
    ("spe_details", "SPE 条件"),
    ("enrichment_method", "富集方法"),
    ("concentration_process", "浓缩过程"),
    ("resolubilization_solvent", "复溶溶剂"),
    ("other_information", "前处理补充信息"),
]

CHROM_FIELDS = [
    ("instrument_manufacturer", "色谱仪厂商"),
    ("instrument_model", "色谱仪型号"),
    ("column_type", "色谱柱类型"),
    ("column_manufacturer", "色谱柱厂商"),
    ("column_model", "色谱柱型号"),
    ("column_length", "柱长"),
    ("column_internal_diameter", "内径"),
    ("particle_size", "粒径"),
    ("coating_thickness", "膜厚"),
    ("injection_volume", "进样体积"),
    ("injection_mode", "进样模式"),
    ("injector_temperature", "进样口温度"),
    ("mobile_phase_composition", "流动相/载气"),
    ("flow_rate", "流速"),
    ("gradient_profile", "梯度/升温程序"),
    ("other_information", "色谱补充信息"),
]

MS_FIELDS = [
    ("ms_instrument_manufacturer", "质谱厂商"),
    ("ms_instrument_model", "质谱型号"),
    ("ionization_mode", "离子化方式"),
    ("ionization_polarity", "离子极性"),
    ("mass_analyzer_type", "质量分析器"),
    ("ms_acquisition_mode", "采集模式"),
    ("sample_introduction_method", "进样方式"),
    ("capillary_voltage", "毛细管电压"),
    ("source_temperature", "离子源温度"),
    ("nebulization_gas_flow", "雾化气流量"),
    ("cone_gas_flow", "锥孔气流量"),
    ("scan_range", "扫描范围"),
    ("mass_resolution", "质量分辨率"),
    ("other_information", "质谱补充信息"),
]


def render_method_details(method: dict[str, Any], key_prefix: str) -> None:
    if not method:
        st.info("当前检测记录未关联到方法参数。")
        return
    show_evidence = st.checkbox("显示参数原文证据", key=f"{key_prefix}_method_evidence")
    sample_tab, prep_tab, chrom_tab, ms_tab = st.tabs(
        ["样品信息", "样品前处理", "色谱条件", "质谱条件"]
    )
    with sample_tab:
        render_parameter_section(method.get("sample_information") or {}, SAMPLE_FIELDS, show_evidence)
    with prep_tab:
        render_parameter_section(method.get("sample_preparation") or {}, PREP_FIELDS, show_evidence)
    with chrom_tab:
        render_parameter_section(
            method.get("chromatography_conditions") or {},
            CHROM_FIELDS,
            show_evidence,
        )
    with ms_tab:
        render_parameter_section(
            method.get("mass_spectrometry_conditions") or {},
            MS_FIELDS,
            show_evidence,
        )


def transition_rows(item: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for number in range(1, 4):
        precursor = item.get(f"precursor_ion_{number}")
        product = item.get(f"product_ion_{number}")
        purpose = item.get(f"ion_purpose_{number}")
        collision = item.get(f"collision_energy_{number}")
        source = item.get(f"source_voltage_{number}")
        if not any(value_exists(field) for field in (precursor, product, purpose, collision, source)):
            continue
        rows.append(
            {
                "通道": str(number),
                "母离子": display_value(precursor),
                "子离子/监测离子": display_value(product),
                "用途": display_value(purpose),
                "碰撞能": display_value(collision),
                "源电压": display_value(source),
            }
        )
    return rows


def render_detection_detail(context: dict[str, Any]) -> None:
    row = context["row"]
    item = context["item"]
    method = context["method"]
    document = context["document"]
    compound = context["compound"]
    cas_detail = compound.get("cas_detail") or {}

    st.markdown(
        f"""
        <div class="detail-head">
            <h2>{safe(row["化合物"])}</h2>
            <p>{safe(row["来源名称"])} · CAS {safe(row["CAS"])} · {safe(row["标准编号"])} / {safe(row["方法"])}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    chemical_column, method_column, source_column = st.columns([1, 1.15, 1.35])
    with chemical_column:
        synonyms = cas_detail.get("synonyms") or []
        synonym_text = "；".join(str(item) for item in synonyms[:3]) or "暂无同义名"
        inchikey = str(cas_detail.get("inchiKey") or "—").replace("InChIKey=", "")
        render_panel(
            "Chemical identity",
            plain_formula(cas_detail.get("molecularFormula")),
            f"分子量 {cas_detail.get('molecularMass') or '—'} · InChIKey {inchikey}",
            [synonym_text],
        )
    with method_column:
        render_panel(
            "Measurement",
            f"{row['平台']} · {row['MS 层级（原始）']}",
            f"基质：{row['基质']}；极性：{row['极性']}",
            [row["定量限"], row["保留时间"]],
        )
    with source_column:
        document_name = field_value(document.get("document_name")) or row["标准名称"]
        agency = field_value(document.get("issuing_agency")) or "发布机构未标注"
        render_panel(
            "Regulatory source",
            str(document_name),
            str(agency),
            [row["地区"], display_value(document.get("document_type"))],
        )

    st.markdown("### 化合物身份详情")
    structure_column, identity_column = st.columns([0.8, 1.8])
    with structure_column:
        st.markdown("#### 化学结构")
        images = cas_detail.get("images") or []
        if images:
            encoded_svg = base64.b64encode(str(images[0]).encode("utf-8")).decode("ascii")
            st.image(
                f"data:image/svg+xml;base64,{encoded_svg}",
                caption=f"CAS {compound.get('cas_number', '—')}",
                width="stretch",
            )
        else:
            st.info("暂无结构图。")
    with identity_column:
        replaced_rns = "；".join(str(value) for value in cas_detail.get("replacedRns") or [])
        identity_rows = [
            {"字段": "规范英文名", "值": compound.get("canonical_english_name") or "—"},
            {"字段": "CAS 首选名", "值": cas_detail.get("name") or "—"},
            {"字段": "CAS RN", "值": compound.get("cas_number") or "—"},
            {"字段": "分子式", "值": plain_formula(cas_detail.get("molecularFormula"))},
            {"字段": "分子量", "值": cas_detail.get("molecularMass") or "—"},
            {"字段": "InChIKey", "值": str(cas_detail.get("inchiKey") or "—").replace("InChIKey=", "")},
            {"字段": "Canonical SMILES", "值": cas_detail.get("canonicalSmile") or "—"},
            {"字段": "SMILES", "值": cas_detail.get("smile") or "—"},
            {"字段": "InChI", "值": cas_detail.get("inchi") or "—"},
            {"字段": "历史/替代 CAS", "值": replaced_rns or "—"},
            {"字段": "Molfile", "值": "已收录" if (compound.get("cas_export") or {}).get("molfile") else "未收录"},
        ]
        st.dataframe(
            pd.DataFrame(identity_rows), width="stretch", hide_index=True, height=422
        )
    synonyms = [plain_formula(value) for value in cas_detail.get("synonyms") or []]
    properties = cas_detail.get("experimentalProperties") or []
    citations = cas_detail.get("propertyCitations") or []
    synonym_tab, property_tab, citation_tab = st.tabs(
        [
            f"同义名（{len(synonyms)}）",
            f"实验性质（{len(properties)}）",
            f"属性来源（{len(citations)}）",
        ]
    )
    with synonym_tab:
        if synonyms:
            st.dataframe(
                pd.DataFrame({"同义名": synonyms}),
                width="stretch",
                hide_index=True,
                height=250,
            )
        else:
            st.caption("暂无同义名。")
    with property_tab:
        if properties:
            property_rows = [
                {
                    "性质": value.get("name", "—"),
                    "数值": value.get("property", "—"),
                    "来源编号": value.get("sourceNumber", "—"),
                }
                for value in properties
            ]
            st.dataframe(
                pd.DataFrame(property_rows), width="stretch", hide_index=True, height=250
            )
        else:
            st.caption("暂无实验性质记录。")
    with citation_tab:
        if citations:
            citation_rows = [
                {
                    "来源编号": value.get("sourceNumber", "—"),
                    "来源": value.get("source", "—"),
                    "文档 URI": value.get("docUri", "—") or "—",
                }
                for value in citations
            ]
            st.dataframe(
                pd.DataFrame(citation_rows), width="stretch", hide_index=True, height=250
            )
        else:
            st.caption("暂无属性来源记录。")
    render_correction_notice(document)
    st.markdown("### 离子与定量参数")
    loq_column, rt_column, level_column = st.columns(3)
    loq_column.metric("定量限", display_value(item.get("limit_of_quantification")))
    rt_column.metric("保留时间", display_value(item.get("retention_time")))
    level_column.metric("采集层级", display_value(item.get("ms_level")))

    transitions = transition_rows(item)
    if transitions:
        st.dataframe(
            pd.DataFrame(transitions),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("该记录没有结构化离子通道；可查看“其他检测参数”或原文证据。")

    other_parameters = display_value(item.get("other_parameters_raw"))
    if other_parameters != "—":
        st.caption(f"其他检测参数：{other_parameters}")

    if st.checkbox("显示检测字段原文证据", key=f"detection_evidence_{row['row_id']}"):
        evidence_fields = [
            ("化合物名称", item.get("compound_name")),
            ("CAS", item.get("cas_number")),
            ("定量限", item.get("limit_of_quantification")),
            ("保留时间", item.get("retention_time")),
            ("采集层级", item.get("ms_level")),
        ]
        for number in range(1, 4):
            evidence_fields.extend(
                [
                    (f"通道 {number} 母离子", item.get(f"precursor_ion_{number}")),
                    (f"通道 {number} 子离子", item.get(f"product_ion_{number}")),
                    (f"通道 {number} 碰撞能", item.get(f"collision_energy_{number}")),
                ]
            )
        evidence_rows = [
            {"字段": label, "结构化值": display_value(field), "原文证据": field_evidence(field)}
            for label, field in evidence_fields
            if field_evidence(field)
        ]
        if evidence_rows:
            st.dataframe(pd.DataFrame(evidence_rows), width="stretch", hide_index=True)
        else:
            st.caption("这条记录没有保留可显示的检测字段证据。")

    st.markdown("### 方法上下文")
    st.caption(
        f"锚定描述：{method.get('anchor_instrument') or '未标注'} · "
        f"{method.get('anchor_matrix') or '未标注'} · "
        f"{method.get('anchor_prep') or '未标注'}"
    )
    render_method_details(method, f"detection_{row['row_id']}")


def render_overview(kb: dict[str, Any]) -> None:
    report_counts = kb["report"].get("counts") or {}
    generated_date = str(kb["report"].get("generated_at_utc") or "—")[:10]
    render_hero(
        "V3 data draft · Regulatory method intelligence",
        "把官方检测标准，变成可检索的质谱方法上下文",
        "覆盖中国、日本、美国与欧洲标准，将化合物身份、样品前处理、色谱条件、质谱参数和原文证据串联在同一条记录中。",
        f"数据生成于 {generated_date} · 当前为待清洗草稿",
    )
    render_metric_cards(
        [
            (f"{report_counts.get('document_count', len(kb['documents'])):,}", "官方标准 / 文档"),
            (f"{report_counts.get('method_count', len(kb['methods'])):,}", "方法配置"),
            (
                f"{report_counts.get('compound_detection_item_count', len(kb['detections_df'])):,}",
                "化合物检测记录",
            ),
            (f"{report_counts.get('compound_count', len(kb['compounds'])):,}", "唯一化合物"),
            ("4", "主要来源区域"),
        ]
    )

    st.markdown("### 数据覆盖")
    st.markdown(
        '<div class="section-note">标准来源与分析平台经过展示层归一化；原始字段仍完整保留在详情中。</div>',
        unsafe_allow_html=True,
    )
    region_column, platform_column = st.columns(2)
    with region_column:
        st.markdown("#### 标准来源")
        region_data = pd.DataFrame(
            kb["overview"]["regions"].most_common(),
            columns=["地区", "标准数量"],
        ).set_index("地区")
        st.bar_chart(region_data, color="#087f6a", height=330)
    with platform_column:
        st.markdown("#### 分析平台")
        platform_data = pd.DataFrame(
            kb["overview"]["platforms"].most_common(8),
            columns=["平台", "方法数量"],
        ).set_index("平台")
        st.bar_chart(platform_data, color="#a4c83f", height=330)

    st.markdown("### 高频化合物")
    top_compounds = pd.DataFrame(
        kb["overview"]["top_compounds"],
        columns=["化合物", "关联检测记录"],
    )
    top_compounds.insert(0, "排名", range(1, len(top_compounds) + 1))
    st.dataframe(top_compounds, width="stretch", hide_index=True, height=310)

    st.markdown(
        """
        <div class="feature-grid">
            <div class="feature-card">
                <div class="feature-no">01 · FIND</div>
                <h4>按身份与标准联合检索</h4>
                <p>同时搜索中英文名称、CAS、标准编号、方法编号、基质和仪器描述。</p>
            </div>
            <div class="feature-card">
                <div class="feature-no">02 · TRACE</div>
                <h4>追溯结构化值的原文</h4>
                <p>定量限、保留时间、离子和方法参数可按需展开来源证据。</p>
            </div>
            <div class="feature-card">
                <div class="feature-no">03 · CONTEXT</div>
                <h4>保留完整方法上下文</h4>
                <p>从样品和前处理一路查看色谱、离子源、质量分析器与采集模式。</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_search(kb: dict[str, Any]) -> None:
    frame = kb["detections_df"]
    render_hero(
        "Compound search",
        "化合物与检测条件检索",
        "输入名称、CAS、标准编号、基质或仪器关键词，再按区域、平台与 MS 层级收窄结果。",
        f"{len(frame):,} 条记录 · 支持中英文混合检索",
    )
    query = st.text_input(
        "检索词",
        placeholder="例如：Aflatoxin B1、1162-65-8、GB 23200、牛奶、QTRAP",
    ).strip().lower()
    region_column, platform_column, level_column = st.columns(3)
    with region_column:
        regions = st.multiselect("地区", sorted(frame["地区"].dropna().unique()))
    with platform_column:
        platforms = st.multiselect("分析平台", sorted(frame["平台"].dropna().unique()))
    with level_column:
        levels = st.multiselect("MS 层级", sorted(frame["MS 层级"].dropna().unique()))

    mask = pd.Series(True, index=frame.index)
    if query:
        mask &= frame["search_blob"].str.contains(query, regex=False, na=False)
    if regions:
        mask &= frame["地区"].isin(regions)
    if platforms:
        mask &= frame["平台"].isin(platforms)
    if levels:
        mask &= frame["MS 层级"].isin(levels)
    filtered = frame.loc[mask].sort_values(["化合物", "标准编号", "方法"])

    st.markdown(f"#### 检索结果 · {len(filtered):,} 条")
    if filtered.empty:
        st.warning("没有匹配记录，请减少筛选条件或尝试名称的一部分。")
        return

    preview_columns = [
        "化合物",
        "来源名称",
        "CAS",
        "标准编号",
        "方法",
        "地区",
        "基质",
        "平台",
        "MS 层级（原始）",
        "定量限",
    ]
    st.dataframe(
        filtered.head(250)[preview_columns],
        width="stretch",
        hide_index=True,
        height=390,
    )
    if len(filtered) > 250:
        st.caption("表格显示前 250 条；可继续输入关键词或增加筛选条件。")

    selectable_ids = filtered["row_id"].head(500).astype(int).tolist()

    def option_label(row_id: int) -> str:
        row = kb["detection_lookup"][row_id]["row"]
        return (
            f"{row['化合物']} · {row['CAS']} · "
            f"{row['标准编号']} / {row['方法']} · {row['基质']}"
        )

    selected_id = st.selectbox(
        "选择一条记录查看完整详情",
        selectable_ids,
        format_func=option_label,
    )
    render_detection_detail(kb["detection_lookup"][int(selected_id)])


def render_documents(kb: dict[str, Any]) -> None:
    render_hero(
        "Standards & methods",
        "标准与方法目录",
        "从法规文档出发，查看每份标准覆盖的方法配置、样品基质、分析平台和化合物数量。",
        f"{len(kb['documents']):,} 份文档 · {len(kb['methods']):,} 个方法配置",
    )
    frame = kb["documents_df"]
    query = st.text_input(
        "检索标准",
        placeholder="标准编号、名称、发布机构或方法类型",
        key="document_query",
    ).strip().lower()
    region_column, type_column = st.columns(2)
    with region_column:
        regions = st.multiselect(
            "地区",
            sorted(frame["地区"].dropna().unique()),
            key="document_regions",
        )
    with type_column:
        type_counts = frame["类型"].value_counts()
        common_types = type_counts[type_counts >= 3].index.tolist()
        document_types = st.multiselect("常见方法类型", sorted(common_types))

    mask = pd.Series(True, index=frame.index)
    if query:
        mask &= frame["search_blob"].str.contains(query, regex=False, na=False)
    if regions:
        mask &= frame["地区"].isin(regions)
    if document_types:
        mask &= frame["类型"].isin(document_types)
    filtered = frame.loc[mask].sort_values(["地区", "标准编号"])

    st.markdown(f"#### 文档目录 · {len(filtered):,} 份")
    if filtered.empty:
        st.warning("没有匹配的标准文档。")
        return
    st.dataframe(
        filtered[
            [
                "标准编号",
                "标准名称",
                "地区",
                "类型",
                "方法数",
                "检测记录",
                "化合物数",
            ]
        ].head(500),
        width="stretch",
        hide_index=True,
        height=430,
    )

    document_ids = filtered["document_id"].head(300).tolist()
    row_by_id = filtered.set_index("document_id").to_dict("index")
    selected_document_id = st.selectbox(
        "选择标准查看方法",
        document_ids,
        format_func=lambda item: (
            f"{row_by_id[item]['标准编号']} · {row_by_id[item]['标准名称']}"
        ),
    )
    document_row = row_by_id[selected_document_id]
    document = kb["documents_by_id"][selected_document_id]
    st.markdown(
        f"""
        <div class="detail-head">
            <h2>{safe(document_row["标准编号"])}</h2>
            <p>{safe(document_row["标准名称"])}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    meta_one, meta_two, meta_three = st.columns(3)
    with meta_one:
        render_panel(
            "Issuing body",
            field_value(document.get("issuing_agency")) or "未标注",
            f"{document_row['地区']} · {display_value(document.get('document_type'))}",
        )
    with meta_two:
        render_panel(
            "Timeline",
            f"发布：{display_value(document.get('publication_date'))}",
            f"实施：{display_value(document.get('implementation_date'))}",
        )
    with meta_three:
        render_panel(
            "Coverage",
            f"{document_row['方法数']} 个方法 · {document_row['化合物数']} 个化合物",
            f"{document_row['检测记录']:,} 条化合物检测记录",
        )

    notes = display_value(document.get("document_notes"))
    if notes != "—":
        st.caption(f"文档备注：{notes}")
    render_correction_notice(document)

    methods = kb["methods_df"].loc[
        kb["methods_df"]["document_id"] == selected_document_id
    ].sort_values("方法")
    st.markdown("### 方法配置")
    st.dataframe(
        methods[["方法", "基质", "平台", "仪器描述", "检测记录"]],
        width="stretch",
        hide_index=True,
    )
    method_ids = methods["方法"].tolist()
    if method_ids:
        selected_method_id = st.selectbox("选择方法查看参数", method_ids)
        selected_method = kb["methods_by_key"].get(
            (selected_document_id, selected_method_id),
            {},
        )
        render_method_details(
            selected_method,
            f"document_{selected_document_id}_{selected_method_id}",
        )


def render_quality(kb: dict[str, Any]) -> None:
    report = kb["report"]
    counts = report.get("counts") or {}
    pipeline_version = report.get("pipeline_version", "3.0-v3-data-file-draft")
    relationship_status = (
        (report.get("relationship_validation") or {}).get("status") or "unknown"
    )
    relationship_label = (
        "PASS"
        if relationship_status.lower() == "passed"
        else relationship_status.upper()
    )
    render_hero(
        "Data provenance & quality",
        "数据状态与质量边界",
        "展示 V3 数据投影的校验结果、字段可用性和尚未执行的清洗步骤，帮助正确理解当前数据。",
        f"Pipeline {pipeline_version} · Draft for cleaning",
    )
    st.markdown(
        """
        <div class="draft-alert">
            <strong>当前数据不是最终发布版。</strong><br>
            四类 JSON 已通过数据契约校验和关系校验，但科学单位归一化、语义值修正与记录去重尚未执行。
            页面会展示原始单位和原文证据，不将这些草稿值包装为已完成清洗的结果。
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_metric_cards(
        [
            (f"{counts.get('document_count', 0):,}", "文档关系节点"),
            (f"{counts.get('method_count', 0):,}", "方法关系节点"),
            (f"{counts.get('compound_detection_item_count', 0):,}", "检测项"),
            (f"{counts.get('compound_count', 0):,}", "化合物实体"),
            (relationship_label, "主键与跨表关系"),
        ]
    )

    reviewed_corrections = (kb.get("corrections") or {}).get("documents") or {}
    if reviewed_corrections:
        st.markdown("### 人工复核校正")
        correction_rows = [
            {
                "内部文档 ID": document_id,
                "展示编号": correction.get("display_id", "—"),
                "复核日期": correction.get("reviewed_at", "—"),
                "校正原因": correction.get("reason", "—"),
                "源文件": correction.get("source_file", "—"),
            }
            for document_id, correction in reviewed_corrections.items()
        ]
        st.dataframe(pd.DataFrame(correction_rows), width="stretch", hide_index=True)

    st.markdown("### 核心字段可用性")
    frame = kb["detections_df"]

    def availability(column: str, empty_values: set[str]) -> str:
        available = (~frame[column].isin(empty_values)).sum()
        return f"{available / len(frame):.1%}"

    render_metric_cards(
        [
            (availability("CAS", {"", "—"}), "CAS"),
            (availability("化合物", {"", "—"}), "规范英文名"),
            (availability("定量限", {"", "—"}), "定量限"),
            (availability("保留时间", {"", "—"}), "保留时间"),
            (availability("MS 层级（原始）", {"", "—", "未标注"}), "MS 层级"),
        ]
    )

    schema_column, relation_column = st.columns(2)
    with schema_column:
        st.markdown("### 数据契约校验")
        schema = (
            report.get("data_contract_validation")
            or report.get("schema_validation")
            or {}
        )
        schema_rows = [
            {
                "数据集": name,
                "状态": details.get("status", "unknown"),
                "错误数": details.get("error_count", "—"),
            }
            for name, details in schema.items()
        ]
        st.dataframe(pd.DataFrame(schema_rows), width="stretch", hide_index=True)
    with relation_column:
        st.markdown("### 关系校验")
        checks = (report.get("relationship_validation") or {}).get("checks") or {}
        check_labels = {
            "documents_document_id_unique": "文档 ID 唯一",
            "methods_document_method_pair_unique": "文档-方法组合唯一",
            "methods_document_ids_exist": "方法均关联有效文档",
            "detections_method_pairs_exist": "检测块均关联有效方法",
            "compounds_cas_unique": "CAS 唯一",
            "compounds_canonical_english_name_unique": "规范英文名唯一",
            "detection_cas_and_name_resolve_same_compound": "CAS 与名称解析一致",
            "detection_item_count_matches_stage7": "检测项数量与上游一致",
        }
        check_rows = [
            {"检查": check_labels.get(name, name), "结果": "通过" if passed else "未通过"}
            for name, passed in checks.items()
        ]
        st.dataframe(pd.DataFrame(check_rows), width="stretch", hide_index=True)

    issue_column, boundary_column = st.columns(2)
    with issue_column:
        st.markdown("### V3 投影边界")
        draft_notes = report.get("draft_notes") or {}
        cas_evidence = draft_notes.get("cas_source_evidence") or {}
        search_response = draft_notes.get("representative_search_response") or {}
        issue_rows = [
            {
                "项目": "身份或完整信息不足，未纳入本草稿",
                "数量": report.get(
                    "excluded_from_draft_but_retained_in_identity_ledger", 0
                ),
            },
            {
                "项目": "当前 CAS 由身份解析获得，源记录无同值证据",
                "数量": cas_evidence.get(
                    "derived_current_cas_without_source_evidence", 0
                ),
            },
            {
                "项目": "源证据支持当前 CAS",
                "数量": cas_evidence.get("source_evidence_supports_current_cas", 0),
            },
            {
                "项目": "存在多个检索查询来源的化合物实体",
                "数量": search_response.get(
                    "entities_with_multiple_search_queries", 0
                ),
            },
        ]
        st.dataframe(pd.DataFrame(issue_rows), width="stretch", hide_index=True)
    with boundary_column:
        st.markdown("### 尚未执行")
        labels = {
            "scientific unit conversion": "科学单位换算与归一化",
            "semantic value correction": "语义值修正",
            "duplicate detection deletion or merging": "重复检测删除或合并",
            "record deduplication": "记录去重",
            "source compound-name replacement": "源化合物名称替换",
            "identity reassessment": "化合物身份重新评估",
        }
        cleaning_not_performed = (
            (report.get("draft_notes") or {}).get("cleaning_not_performed")
            or report.get("cleaning_not_performed")
            or []
        )
        for item in cleaning_not_performed:
            st.markdown(f"- {labels.get(item, item)}")

    generated = report.get("generated_at_utc", "—")
    boundary = report.get("stage_boundary", "—")
    st.caption(f"生成时间（UTC）：{generated} · 阶段边界：{boundary}")


def render_footer() -> None:
    st.markdown(
        """
        <div class="footer">
            Food Safety MS Knowledge Base · V3 data draft interface ·
            Values remain linked to their regulatory source evidence.
        </div>
        """,
        unsafe_allow_html=True,
    )


inject_styles()

with st.sidebar:
    st.markdown(
        """
        <div class="brand">
            <div class="brand-mark">MS</div>
            <div class="brand-name">Food Safety<br>Knowledge Base</div>
            <div class="brand-sub">Regulatory mass spectrometry methods</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    page = st.radio(
        "导航",
        ["数据总览", "化合物检索", "标准与方法", "数据质量"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown(
        """
        <div class="side-status">
            <span class="status-dot"></span><strong>V3 data draft</strong><br>
            结构与关系校验已通过；单位、语义和重复记录仍待清洗。
        </div>
        """,
        unsafe_allow_html=True,
    )

try:
    signature = data_signature(DATA_DIR)
    with st.spinner("正在建立数据索引…"):
        knowledge_base = load_knowledge_base(str(DATA_DIR), signature)
except (OSError, ValueError, json.JSONDecodeError) as error:
    st.error(f"数据加载失败：{error}")
    st.stop()

if page == "数据总览":
    render_overview(knowledge_base)
elif page == "化合物检索":
    render_search(knowledge_base)
elif page == "标准与方法":
    render_documents(knowledge_base)
else:
    render_quality(knowledge_base)

render_footer()
