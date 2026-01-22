import streamlit as st
import pandas as pd
import json
import os

# ==========================================
# 1. Global Configuration
# ==========================================
st.set_page_config(
    page_title="Food Safety MS Knowledge Base",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. Core Data Processing Functions
# ==========================================

@st.cache_data
def load_data():
    """
    Load Detections (L2), Methods (L2), and Compounds (v2).
    Returns: detections_list, methods_list, compounds_map, stats_dict
    """
    data_dir = "data"
    
    # 1. Load Detections
    d_path = os.path.join(data_dir, 'detections.json') 
    try:
        with open(d_path, 'r', encoding='utf-8') as f:
            detections = json.load(f)
    except FileNotFoundError:
        st.error(f"File not found: {d_path}")
        detections = []
        
    # 2. Load Methods (L2 Cleaned version)
    m_path = os.path.join(data_dir, 'methods.json')
    try:
        with open(m_path, 'r', encoding='utf-8') as f:
            methods = json.load(f)
    except FileNotFoundError:
        st.error(f"File not found: {m_path}")
        methods = []

    # 3. Load Compounds
    c_path = os.path.join(data_dir, 'compounds.json')
    compounds_map = {}
    compounds_list = [] # 用于统计总数
    try:
        with open(c_path, 'r', encoding='utf-8') as f:
            compounds_list = json.load(f)
            for c in compounds_list:
                # 建立 CAS 映射方便查找
                cas = c.get('cas_number')
                if cas: compounds_map[cas] = c
                # 也可以考虑建立 Name 映射作为备用
                # name = c.get('preferred_name')
                # if name: compounds_map[name.lower()] = c 
    except FileNotFoundError:
        pass 
    
    # --- 4. Calculate Statistics (新增逻辑) ---
    # Metric 1: Total Transitions (离子对总数)
    total_transitions = 0
    for d in detections:
        ms_params = d.get('mass_spec_params', [])
        if isinstance(ms_params, list):
            total_transitions += len(ms_params)
            
    # Metric 2: Total Compounds (无论有无CAS)
    total_compounds = len(compounds_list)
    
    stats = {
        "transitions": total_transitions,
        "compounds": total_compounds
    }
        
    return detections, methods, compounds_map, stats

@st.cache_data
def create_method_index(methods_data):
    """Build index: Method_ID -> Run_ID -> Data"""
    index = {}
    for m in methods_data:
        mid_info = m.get('method_identification', {})
        m_id = mid_info.get('method_id')
        if not m_id: continue
        index[m_id] = {
            "info": mid_info,
            "runs": {}
        }
        runs = m.get('analytical_runs', [])
        for r in runs:
            r_id = r.get('run_config_id')
            if r_id: index[m_id]["runs"][r_id] = r
    return index

def normalize_ms_data(ms_params_list):
    """Normalize MS params for DataFrame display."""
    if not ms_params_list: return pd.DataFrame()
    clean_rows = []
    for item in ms_params_list:
        ce_raw = item.get('collision_energy')
        ce_display = "-"
        if isinstance(ce_raw, dict):
            ce_display = str(ce_raw.get('value', '-'))
            if ce_raw.get('unit'): ce_display += f" {ce_raw.get('unit')}"
        elif ce_raw is not None:
            ce_display = str(ce_raw)
            
        row = {
            "Type": item.get('parameter_type', 'Target'),
            "Polarity": item.get('polarity', '-'),
            "Precursor": item.get('precursor_mz'),
            "Product": item.get('product_mz', '-'),
            "CE": ce_display,
            "Label": item.get('source_ion_label', '-')
        }
        clean_rows.append(row)
    return pd.DataFrame(clean_rows)

# ==========================================
# 3. Load & Index
# ==========================================
raw_detections, raw_methods, compounds_map, stats = load_data()
method_index = create_method_index(raw_methods)

# ==========================================
# 4. Sidebar (Modified Metrics)
# ==========================================
with st.sidebar:
    st.title("🎛️ Control Panel")
    
    # 1. Detection Records (原 Total Detections)
    # 含义：有多少个“化合物-方法”组合
    st.metric("Detection Records", len(raw_detections))
    
    # 2. Total Transitions (新增)
    # 含义：有多少个具体的离子对数据
    st.metric("Total Transitions", stats["transitions"])
    
    # 3. Unique Compounds (修正)
    # 含义：化合物字典里的总条目数 (Verified + Curated + Orphan)
    st.metric("Unique Compounds", stats["compounds"])
    
    # 4. Methods
    st.metric("Standard Methods", len(method_index))
    
    st.divider()
    st.info("Data Source: Official Regulatory Standards (GB, USDA, CEN)")
    st.caption("Powered by L2 Semantic Extraction")

# ==========================================
# 5. Main Interface (保持不变)
# ==========================================
st.title("🧬 Food Safety MS Knowledge Base")
tab_search, tab_browse = st.tabs(["🔍 Search & Analysis", "📂 Browse Database"])

# ... (Tab 1 和 Tab 2 的代码与原版一致，不需要修改，直接粘贴即可) ...
# ... (为节省篇幅，此处省略 Tab 部分，请保留您原有的 Tab 代码) ...

# --- TAB 1: Search ---
with tab_search:
    st.markdown("#### Find Compounds and Method Context")
    col_q, _ = st.columns([3, 1])
    with col_q:
        query = st.text_input("Input CAS or Name", placeholder="e.g., 94-75-7 or Doramectin", label_visibility="collapsed")
    
    if query:
        query = query.strip().lower()
        results = [
            r for r in raw_detections 
            if query in str(r.get('CAS_number', '')).lower() or query in str(r.get('compound_english_name', '')).lower()
        ]
        
        if results:
            st.success(f"Found {len(results)} records.")
            
            for idx, res in enumerate(results):
                m_id = res.get('method_id')
                r_id = res.get('run_config_id')
                cas = res.get('CAS_number')
                name = res.get('compound_english_name')
                
                # Context Lookup
                method_context = method_index.get(m_id, {})
                method_info = method_context.get('info', {})
                run_details = method_context.get('runs', {}).get(r_id, {})
                
                # Compound Metadata
                comp_meta = compounds_map.get(cas, {}) if cas else {}
                
                # Title
                status_icon = "✅" if comp_meta.get('status') == 'Verified' else "📝"
                with st.expander(f"{status_icon} **{name}** (CAS: {cas or 'N/A'}) | 📜 {m_id}", expanded=(idx==0)):
                    
                    c1, c2, c3 = st.columns([0.7, 1.5, 1.5])
                    
                    # --- Col 1: Chemical Info ---
                    with c1:
                        st.markdown("##### 🧪 Identity")
                        if comp_meta:
                            props = comp_meta.get('chemical_properties', {})
                            st.caption(f"Formula: {props.get('molecular_formula') or '-'}")
                            st.caption(f"MW: {props.get('molecular_weight') or '-'}")
                            st.caption(f"CID: {props.get('pubchem_cid') or '-'}")
                            if comp_meta.get('synonyms'):
                                st.caption(f"Synonyms: {', '.join(comp_meta['synonyms'][:2])}")
                        else:
                            st.caption("No extended metadata.")

                    # --- Col 2: MS Data ---
                    with c2:
                        st.markdown("##### 📊 Spectrum")
                        # 优先展示 L2 提取的仪器标签
                        inst_tag = run_details.get('aug_instrument_tag') or run_details.get('mass_spectrometry_conditions', {}).get('ms_instrument_model', '-')
                        st.caption(f"Instrument: **{inst_tag}**")
                        
                        df_ms = normalize_ms_data(res.get('mass_spec_params', []))
                        st.dataframe(df_ms, use_container_width=True, hide_index=True)
                        
                        # RT Display
                        perf = res.get('performance_parameters', [])
                        rt_val = next((p['value'] for p in perf if p.get('parameter_name', '').lower() in ['rt', 'retention time']), None)
                        if rt_val: st.info(f"RT: {rt_val} min")

                    # --- Col 3: Method Context (L2 Enhanced!) ---
                    with c3:
                        st.markdown("##### 🧪 Measurement Details") # 改名: 测量方法细节
                        
                        if not run_details:
                            st.warning("Method details missing.")
                        else:
                            # 准备数据
                            chrom = run_details.get('chromatography_conditions', {})
                            ms_cond = run_details.get('mass_spectrometry_conditions', {})
                            prep = run_details.get('sample_preparation', {})
                            
                            # 1. [Area A] 核心配置 (高亮展示)
                            # 组合仪器名
                            inst_name = f"{ms_cond.get('ms_instrument_manufacturer', '')} {ms_cond.get('ms_instrument_model', '')}".strip()
                            if len(inst_name) < 2: inst_name = "LC-MS/MS System"
                            
                            # 组合色谱柱
                            col_name = chrom.get('column_model', 'Unknown Column')
                            
                            # 获取简化的流动相
                            mp = run_details.get('aug_mobile_phase_short') or "See details"
                            
                            # 展示核心卡片
                            st.info(f"""
                            **🖥️ {inst_name}**  
                            **💈 {col_name}**  
                            **💧 {mp}**
                            """)
                            
                            # 2. [Area B] 基质与流程 (标签化)
                            # Matrix Tags
                            matrix_tags = run_details.get('aug_matrix_tags', [])
                            if matrix_tags:
                                st.caption("Applicable Matrices:")
                                st.markdown(" ".join([f"`{t}`" for t in matrix_tags[:6]])) # 最多显示6个
                            
                            st.divider()
                            
                            # Prep Flow Arrow
                            prep_steps = run_details.get('aug_prep_steps', [])
                            if prep_steps:
                                st.caption("Prep Workflow:")
                                st.markdown(" **→** ".join(prep_steps))
                            
                            # 3. [Area C] 详细协议 (折叠区)
                            # 只有当用户真的想看“怎么做”的时候才点开
                            with st.expander("📋 Sample Prep Protocol (Full Text)"):
                                st.markdown(f"**Extraction:** {prep.get('extraction_solvent', '-')}")
                                st.markdown(f"**Cleanup:** {prep.get('cleanup_method', '-')}")
                                st.markdown(f"**Concentration:** {prep.get('concentration_process', '-')}")
                                if prep.get('other_information'):
                                    st.info(f"Note: {prep.get('other_information')}")

                            with st.expander("📈 Gradient & MS Parameters"):
                                st.markdown("**Gradient Profile:**")
                                st.code(chrom.get('gradient_profile', 'N/A'))
                                st.markdown("**MS Source Settings:**")
                                st.write(ms_cond.get('other_information', '-'))
                                st.caption(f"Ion Mode: {ms_cond.get('ionization_mode', '-')}")

# --- TAB 2: Browse ---
with tab_browse:
    st.markdown("#### 📂 Database Overview")
    preview_data = []
    for d in raw_detections:
        preview_data.append({
            "Method": d.get('method_id'),
            "Compound": d.get('compound_english_name'),
            "CAS": d.get('CAS_number'),
            "Source": d.get('_source_file', 'N/A')
        })
    df_preview = pd.DataFrame(preview_data)
    
    methods_list = df_preview['Method'].unique().tolist()
    filter_method = st.multiselect("Filter by Standard", methods_list)
    
    if filter_method:
        df_preview = df_preview[df_preview['Method'].isin(filter_method)]
        
    st.dataframe(df_preview, use_container_width=True, hide_index=True, height=600)