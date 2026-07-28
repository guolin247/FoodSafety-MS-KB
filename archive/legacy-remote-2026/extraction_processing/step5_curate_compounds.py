import json
import pandas as pd
import numpy as np
import os

# ================= 配置区 =================
# 输入文件
FILE_COMPOUNDS = r"D:\work_GuoLin\FoodSafety-MS-KB\compounds.json"
FILE_API_CSV = r"D:\work_GuoLin\FoodSafety-MS-KB\extraction_processing\orphan_candidates_api.csv"
FILE_LLM_CSV = r"D:\work_GuoLin\FoodSafety-MS-KB\extraction_processing\orphan_candidates_llm_wb.csv" # 刚才救回来的那个文件

# 输出文件
OUTPUT_JSON = "compounds_v2.json"
OUTPUT_REVIEW_CSV = "curation_review_conflicts.csv"
# ========================================

def clean_cas(val):
    """简单的 CAS 清洗"""
    if pd.isna(val) or val == "" or str(val).lower() in ["none", "nan", "not_found"]:
        return None
    return str(val).strip()

def curate_compounds():
    print("🚀 Starting Step 5: Data Curation & Fusion...")

    # 1. 加载数据
    try:
        with open(FILE_COMPOUNDS, 'r', encoding='utf-8') as f:
            compounds = json.load(f)
        
        # 读取 CSV 并建立索引 (以 original_name 为 key)
        # 填充 NaN 为 None，方便后续处理
        df_api = pd.read_csv(FILE_API_CSV).replace({np.nan: None})
        df_llm = pd.read_csv(FILE_LLM_CSV).replace({np.nan: None})
        
        # 转换为字典，方便 O(1) 查找
        # key: original_name, value: row dict
        api_lookup = {row['original_name']: row for _, row in df_api.iterrows()}
        llm_lookup = {row['original_name']: row for _, row in df_llm.iterrows()}
        
        print(f"   Loaded: {len(compounds)} compounds, {len(api_lookup)} API records, {len(llm_lookup)} LLM records.")

    except FileNotFoundError as e:
        print(f"❌ Error: Missing input files. {e}")
        return

    # 2. 融合循环
    updated_count = 0
    conflicts = []
    
    for rec in compounds:
        name = rec.get('preferred_name')
        original_cas = clean_cas(rec.get('cas_number'))
        status = rec.get('status')
        
        # --- 初始化 Provenance 结构 ---
        # 这将保存所有来源的 CAS，互不覆盖
        rec['provenance'] = {
            'cas_from_doc': original_cas,
            'cas_from_api': None,
            'cas_from_llm': None
        }
        
        # 额外属性字典
        rec['chemical_properties'] = {
            'molecular_formula': None,
            'molecular_weight': None,
            'smiles': None,
            'pubchem_cid': None
        }

        # 如果是 Verified (有 Doc CAS)，它就是最终结果
        if status == 'Verified' and original_cas:
            rec['cas_source'] = 'Document'
            # 即使是 Verified，如果有 API 数据也可以补充属性（分子量等），但不改 CAS
            # (此处略过，专注补全 Orphan)
            continue

        # --- 处理 Orphan 数据 ---
        api_data = api_lookup.get(name, {})
        llm_data = llm_lookup.get(name, {})
        
        # 提取 CAS
        cas_api = clean_cas(api_data.get('suggested_cas'))
        cas_llm = clean_cas(llm_data.get('suggested_cas'))
        
        # 记录到 Provenance
        rec['provenance']['cas_from_api'] = cas_api
        rec['provenance']['cas_from_llm'] = cas_llm
        
        # --- 决策逻辑 (Waterfall) ---
        final_cas = None
        source_tag = "Unresolved"
        
        # Priority 1: API (最高优先级)
        if cas_api:
            final_cas = cas_api
            source_tag = "API_PubChem"
            rec['chemical_properties']['pubchem_cid'] = api_data.get('pubchem_cid')
            rec['chemical_properties']['suggested_iupac'] = api_data.get('suggested_name')
            
        # Priority 2: LLM (只要有结果就采纳)
        elif cas_llm:
            final_cas = cas_llm
            confidence = llm_data.get('confidence', 'Unknown')
            source_tag = f"LLM_{confidence}" # 标记为 LLM_High, LLM_Medium 等
            
            # 注入属性
            rec['chemical_properties']['molecular_formula'] = llm_data.get('molecular_formula')
            rec['chemical_properties']['molecular_weight'] = llm_data.get('molecular_weight')
            rec['chemical_properties']['smiles'] = llm_data.get('smiles')
            
        # 冲突检测 (用于人工审核)
        if cas_api and cas_llm and cas_api != cas_llm:
            conflicts.append({
                "name": name,
                "cas_api": cas_api,
                "cas_llm": cas_llm,
                "llm_confidence": llm_data.get('confidence'),
                "decision": "Auto-selected API" # 脚本默认选了 API
            })

        # --- 更新主记录 ---
        if final_cas:
            rec['cas_number'] = final_cas  # 更新主 CAS，供下游使用
            rec['cas_source'] = source_tag # 标记来源
            rec['status'] = 'Curated'      # 更新状态
            updated_count += 1
        else:
            rec['cas_source'] = 'None'

    # 3. 保存结果
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(compounds, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Curation Complete!")
    print(f"   - Updated {updated_count} orphan records with new CAS numbers.")
    print(f"   - Saved final database to: {OUTPUT_JSON}")

    # 4. 保存冲突报告
    if conflicts:
        pd.DataFrame(conflicts).to_csv(OUTPUT_REVIEW_CSV, index=False)
        print(f"⚠️  Found {len(conflicts)} conflicts between API and LLM. Saved to {OUTPUT_REVIEW_CSV} for review.")
    else:
        print("🎉 No conflicts found between API and LLM.")

if __name__ == "__main__":
    curate_compounds()