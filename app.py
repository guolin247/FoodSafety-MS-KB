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
    """Load Detection and Method data from JSON files in the 'data' directory."""
    data_dir = "data"
    
    # Load Detections
    d_path = os.path.join(data_dir, 'detections.json')
    try:
        with open(d_path, 'r', encoding='utf-8') as f:
            detections = json.load(f)
    except FileNotFoundError:
        st.error(f"File not found: {d_path}")
        detections = []
        
    # Load Methods
    m_path = os.path.join(data_dir, 'methods.json') # Ensure your file is named methods.json
    try:
        with open(m_path, 'r', encoding='utf-8') as f:
            methods = json.load(f)
    except FileNotFoundError:
        st.error(f"File not found: {m_path}")
        methods = []
        
    return detections, methods

@st.cache_data
def create_method_index(methods_data):
    """
    Build an efficient index for methods.
    Structure: { "Method_ID": { "info": {...}, "runs": { "Run_ID": {...} } } }
    Allows instant lookup by method_id and run_config_id.
    """
    index = {}
    for m in methods_data:
        # Extract basic info
        mid_info = m.get('method_identification', {})
        m_id = mid_info.get('method_id')
        
        if not m_id: continue
        
        index[m_id] = {
            "info": mid_info,
            "runs": {}
        }
        
        # Index all analytical runs under this method
        runs = m.get('analytical_runs', [])
        for r in runs:
            r_id = r.get('run_config_id')
            if r_id:
                index[m_id]["runs"][r_id] = r
                
    return index

def normalize_ms_data(ms_params_list):
    """Normalize mass spectrometry parameters for display."""
    if not ms_params_list: return pd.DataFrame()
    clean_rows = []
    for item in ms_params_list:
        ce_raw = item.get('collision_energy')
        ce_display = "-"
        # Handle CE if it's a dict (value/unit) or a raw string/number
        if isinstance(ce_raw, dict):
            ce_display = str(ce_raw.get('value', '-'))
        elif ce_raw is not None:
            ce_display = str(ce_raw)
            
        row = {
            "Type": item.get('parameter_type', 'Target'),
            "Polarity": item.get('polarity', '-'),
            "Precursor (m/z)": item.get('precursor_mz'),
            "Product (m/z)": item.get('product_mz', '-'),
            "CE (V)": ce_display,
            "Ion Label": item.get('source_ion_label', '-')
        }
        clean_rows.append(row)
    return pd.DataFrame(clean_rows)

# ==========================================
# 3. Load & Index Data
# ==========================================
raw_detections, raw_methods = load_data()
method_index = create_method_index(raw_methods)

# ==========================================
# 4. Sidebar
# ==========================================
with st.sidebar:
    st.title("🎛️ Control Panel")
    
    # Metrics
    st.metric("Total Detections", len(raw_detections))
    st.metric("Indexed Methods", len(method_index))
    
    st.divider()
    st.info("**Data Sources:**\n\nOfficial Regulatory Standards from China (GB), USA (USDA/FDA), and EU (CEN/EURL).")
    st.caption("v1.0.0-beta | Data Repository linked to Zenodo")

# ==========================================
# 5. Main Interface: Tabs
# ==========================================
st.title("🧬 Food Safety MS Knowledge Base")
st.markdown("A structured repository of validated mass spectral parameters extracted from official regulatory documents.")

# Create tabs
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
        # Search logic
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
                cas = res.get('CAS_number') or "N/A"
                name = res.get('compound_english_name')
                
                # Retrieve context from index
                method_context = method_index.get(m_id, {})
                method_info = method_context.get('info', {})
                run_details = method_context.get('runs', {}).get(r_id, {})
                
                # Card Title
                with st.expander(f"🧬 **{name}** (CAS: {cas}) | 📜 {m_id}", expanded=(idx==0)):
                    
                    col_left, col_right = st.columns([1.2, 1])
                    
                    # --- Left Column: MS Data ---
                    with col_left:
                        st.markdown("##### 📊 Mass Spectrum")
                        st.caption(f"Config: **{r_id}** | Polarity: **{run_details.get('mass_spectrometry_conditions', {}).get('ionization_polarity', 'N/A')}**")
                        
                        df_ms = normalize_ms_data(res.get('mass_spec_params', []))
                        st.dataframe(df_ms, use_container_width=True, hide_index=True)
                        
                        # Show Retention Time only if available
                        perf = res.get('performance_parameters', [])
                        rt_val = next((p['value'] for p in perf if p['parameter_name'] in ['RT', 'Retention Time']), None)
                        if rt_val:
                            st.info(f"🕒 **Retention Time:** {rt_val} min")

                    # --- Right Column: Method Context ---
                    with col_right:
                        st.markdown("##### 🧪 Method Context")
                        
                        if not run_details:
                            st.warning(f"Method details for {m_id} / {r_id} not found in metadata.")
                        else:
                            # 1. Instrument & Column
                            chrom = run_details.get('chromatography_conditions', {})
                            ms_cond = run_details.get('mass_spectrometry_conditions', {})
                            
                            st.markdown(f"""
                            - **Instrument:** {chrom.get('instrument_model', '-')} / {ms_cond.get('ms_instrument_model', '-')}
                            - **Column:** {chrom.get('column_model', '-')} ({chrom.get('column_type', '-')})
                            - **Mobile Phase:** {chrom.get('mobile_phase_composition', '-')}
                            - **Ion Mode:** {ms_cond.get('ionization_mode', '-')}
                            """)
                            
                            # 2. Sample Preparation (Popover)
                            prep = run_details.get('sample_preparation', {})
                            with st.popover("View Sample Preparation"):
                                st.markdown(f"**Extraction:** {prep.get('extraction_solvent', '-')}")
                                st.markdown(f"**Cleanup:** {prep.get('cleanup_method', '-')}")
                                st.markdown(f"**Details:** {prep.get('other_information', '-')}")
                            
                            # 3. Gradient (Popover)
                            with st.popover("View Gradient Program"):
                                st.code(chrom.get('gradient_profile', 'No gradient info available.'))
                                
                            # 4. Agency
                            st.caption(f"Issuing Agency: {method_info.get('issuing_agency', '-')}")

        else:
            st.warning("No results found. Try entering a generic name (e.g., 'Aflatoxin') or a specific CAS number.")
    else:
        st.info("Enter a compound name or CAS number to view validated MS parameters and method details.")

# ------------------------------------------------------------------
# TAB 2: Browse Functionality
# ------------------------------------------------------------------
with tab_browse:
    st.markdown("#### 📂 Database Overview")
    
    # 1. Convert detections to DataFrame for preview
    preview_data = []
    for d in raw_detections:
        preview_data.append({
            "Method": d.get('method_id'),
            "Compound": d.get('compound_english_name'),
            "CAS": d.get('CAS_number'),
            "Config": d.get('run_config_id')
        })
    df_preview = pd.DataFrame(preview_data)
    
    # 2. Filters
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        filter_method = st.multiselect("Filter by Standard", df_preview['Method'].unique())
    
    # Apply Filter
    if filter_method:
        df_preview = df_preview[df_preview['Method'].isin(filter_method)]
        
    # 3. Display Table
    st.dataframe(
        df_preview, 
        use_container_width=True, 
        hide_index=True,
        height=600
    )