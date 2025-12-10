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
    Load Detections (L2 Cleaned), Methods, and Compounds (v2) data.
    Returns: detections (list), methods (list), compounds_map (dict)
    """
    data_dir = "data"
    
    # 1. Load Detections (L2 Cleaned)
    d_path = os.path.join(data_dir, 'detections.json') # Ensure this file contains L2 data
    try:
        with open(d_path, 'r', encoding='utf-8') as f:
            detections = json.load(f)
    except FileNotFoundError:
        st.error(f"File not found: {d_path}")
        detections = []
        
    # 2. Load Methods
    m_path = os.path.join(data_dir, 'methods.json')
    try:
        with open(m_path, 'r', encoding='utf-8') as f:
            methods = json.load(f)
    except FileNotFoundError:
        st.error(f"File not found: {m_path}")
        methods = []

    # 3. Load Compounds (v2 with Metadata)
    c_path = os.path.join(data_dir, 'compounds.json')
    compounds_map = {}
    try:
        with open(c_path, 'r', encoding='utf-8') as f:
            compounds_list = json.load(f)
            # Build a lookup dictionary: CAS -> Compound Record
            # Also support Name lookup for orphans if needed, but CAS is primary
            for c in compounds_list:
                cas = c.get('cas_number')
                if cas:
                    compounds_map[cas] = c
                # Optional: You could also map names if needed
    except FileNotFoundError:
        st.warning(f"Compounds metadata not found: {c_path}")
        
    return detections, methods, compounds_map

@st.cache_data
def create_method_index(methods_data):
    """
    Build an efficient index for methods.
    Structure: { "Method_ID": { "info": {...}, "runs": { "Run_ID": {...} } } }
    """
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
            if r_id:
                index[m_id]["runs"][r_id] = r
                
    return index

def normalize_ms_data(ms_params_list):
    """Normalize mass spectrometry parameters for display (Compatible with L2 data)."""
    if not ms_params_list: return pd.DataFrame()
    clean_rows = []
    for item in ms_params_list:
        # Handle Collision Energy
        ce_raw = item.get('collision_energy')
        ce_display = "-"
        if isinstance(ce_raw, dict):
            ce_display = str(ce_raw.get('value', '-'))
            # Optional: Add unit if exists
            if ce_raw.get('unit'):
                ce_display += f" {ce_raw.get('unit')}"
        elif ce_raw is not None:
            ce_display = str(ce_raw)
            
        row = {
            "Type": item.get('parameter_type', 'Target'),
            "Polarity": item.get('polarity', '-'),
            "Precursor (m/z)": item.get('precursor_mz'),
            "Product (m/z)": item.get('product_mz', '-'),
            "CE": ce_display,
            "Ion Label": item.get('source_ion_label', '-')
        }
        clean_rows.append(row)
    return pd.DataFrame(clean_rows)

# ==========================================
# 3. Load & Index Data
# ==========================================
raw_detections, raw_methods, compounds_map = load_data()
method_index = create_method_index(raw_methods)

# ==========================================
# 4. Sidebar
# ==========================================
with st.sidebar:
    st.title("🎛️ Control Panel")
    
    st.metric("Total Detections", len(raw_detections))
    st.metric("Unique Compounds", len(compounds_map))
    st.metric("Indexed Methods", len(method_index))
    
    st.divider()
    st.info("**Data Sources:**\n\nOfficial Regulatory Standards from China (GB), USA (USDA/FDA), and EU (CEN/EURL).")
    st.caption("v1.1.0 (L2 Data) | Data Repository linked to Zenodo")

# ==========================================
# 5. Main Interface: Tabs
# ==========================================
st.title("🧬 Food Safety MS Knowledge Base")
st.markdown("A structured repository of validated mass spectral parameters extracted from official regulatory documents.")

tab_search, tab_browse = st.tabs(["🔍 Search & Analysis", "📂 Browse Database"])

# ------------------------------------------------------------------
# TAB 1: Search Functionality
# ------------------------------------------------------------------
with tab_search:
    st.markdown("#### Find Compounds and Method Context")
    
    col_q, col_btn = st.columns([3, 1])
    with col_q:
        query = st.text_input("Input CAS or Name", placeholder="e.g., 94-75-7 or Doramectin", label_visibility="collapsed")
    
    if query:
        query = query.strip().lower()
        # Search logic: Filter detections list
        results = [
            r for r in raw_detections 
            if query in str(r.get('CAS_number', '')).lower() or query in str(r.get('compound_english_name', '')).lower()
        ]
        
        if results:
            st.success(f"Found {len(results)} records linked to official methods.")
            
            for idx, res in enumerate(results):
                # Retrieve keys
                m_id = res.get('method_id')
                r_id = res.get('run_config_id')
                cas = res.get('CAS_number')
                name = res.get('compound_english_name')
                
                # Retrieve Contexts
                method_context = method_index.get(m_id, {})
                method_info = method_context.get('info', {})
                run_details = method_context.get('runs', {}).get(r_id, {})
                
                # Retrieve Compound Metadata (from compounds_v2.json)
                comp_meta = compounds_map.get(cas, {}) if cas else {}
                
                # --- Card Title ---
                # Add Status Badge to title if available
                status_icon = "✅" if comp_meta.get('status') == 'Verified' else "🤖" if 'LLM' in str(comp_meta.get('cas_source', '')) else "📝"
                
                card_label = f"{status_icon} **{name}** (CAS: {cas or 'N/A'}) | 📜 {m_id}"
                
                with st.expander(card_label, expanded=(idx==0)):
                    
                    # Layout: 3 Columns (Chem Info | MS Data | Method Context)
                    c1, c2, c3 = st.columns([1, 1.5, 1])
                    
                    # --- Col 1: Chemical Profile (New!) ---
                    with c1:
                        st.markdown("##### 🧪 Chemical Profile")
                        if comp_meta:
                            props = comp_meta.get('chemical_properties', {})
                            st.markdown(f"**Formula:** {props.get('molecular_formula') or '-'}")
                            st.markdown(f"**Mol. Weight:** {props.get('molecular_weight') or '-'}")
                            st.markdown(f"**PubChem CID:** {props.get('pubchem_cid') or '-'}")
                            
                            # Show Source Tag
                            source_tag = comp_meta.get('cas_source', 'Unknown')
                            st.caption(f"Identity Source: {source_tag}")
                            
                            # Show Synonyms (First 3)
                            syns = comp_meta.get('synonyms', [])
                            if syns:
                                st.caption(f"Synonyms: {', '.join(syns[:3])}...")
                        else:
                            st.warning("No extended chemical metadata available.")

                    # --- Col 2: MS Data ---
                    with c2:
                        st.markdown("##### 📊 Mass Spectrum")
                        st.caption(f"Config: **{r_id}** | Polarity: **{run_details.get('mass_spectrometry_conditions', {}).get('ionization_polarity', 'N/A')}**")
                        
                        df_ms = normalize_ms_data(res.get('mass_spec_params', []))
                        st.dataframe(df_ms, use_container_width=True, hide_index=True)
                        
                        # Show RT if available
                        perf = res.get('performance_parameters', [])
                        rt_val = next((p['value'] for p in perf if p.get('parameter_name', '').lower() in ['rt', 'retention time', 'relative_retention_time']), None)
                        if rt_val:
                            st.info(f"🕒 **Retention Time:** {rt_val} min")

                    # --- Col 3: Method Context ---
                    with c3:
                        st.markdown("##### 🔬 Method Context")
                        
                        if not run_details:
                            st.warning("Method details missing.")
                        else:
                            chrom = run_details.get('chromatography_conditions', {})
                            ms_cond = run_details.get('mass_spectrometry_conditions', {})
                            
                            # Mini Table style
                            st.markdown(f"**Instrument:** {chrom.get('instrument_model', '-')} / {ms_cond.get('ms_instrument_model', '-')}")
                            st.markdown(f"**Column:** {chrom.get('column_model', '-')}")
                            st.markdown(f"**Mobile Phase:** {chrom.get('mobile_phase_composition', '-')}")
                            
                            # Popovers for heavy text
                            prep = run_details.get('sample_preparation', {})
                            with st.popover("Sample Prep Details"):
                                st.markdown(f"**Extraction:** {prep.get('extraction_solvent', '-')}")
                                st.markdown(f"**Cleanup:** {prep.get('cleanup_method', '-')}")
                                st.markdown(f"**Details:** {prep.get('other_information', '-')}")
                            
                            st.caption(f"Agency: {method_info.get('issuing_agency', '-')}")

        else:
            st.warning("No records found.")
    else:
        st.info("Enter keyword to search.")

# ------------------------------------------------------------------
# TAB 2: Browse Functionality
# ------------------------------------------------------------------
with tab_browse:
    st.markdown("#### 📂 Database Overview")
    
    # 1. Flatten detections for preview
    preview_data = []
    for d in raw_detections:
        preview_data.append({
            "Method": d.get('method_id'),
            "Compound": d.get('compound_english_name'),
            "CAS": d.get('CAS_number'),
            "Source": d.get('_source_file', 'N/A') # Show file source
        })
    df_preview = pd.DataFrame(preview_data)
    
    # 2. Filters
    methods_list = df_preview['Method'].unique().tolist()
    filter_method = st.multiselect("Filter by Standard", methods_list)
    
    if filter_method:
        df_preview = df_preview[df_preview['Method'].isin(filter_method)]
        
    st.dataframe(df_preview, use_container_width=True, hide_index=True, height=600)