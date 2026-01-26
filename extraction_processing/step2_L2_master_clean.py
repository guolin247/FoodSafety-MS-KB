import json
from collections import defaultdict
import datetime

# ================= 配置区 =================
INPUT_FILE = r"D:\work_GuoLin\FoodSafety-MS-KB\FoodSafety_MS_Raw_v1.json"  # L1 清洗后的输入
OUTPUT_COMPOUNDS = "compounds.json"
OUTPUT_DETECTIONS_L2 = "FoodSafety_MS_L2_cleaned.json" # L2 清洗后的检测数据
LOG_FILE = "L2_cleaning_log.md"
# ========================================

def build_compounds_and_complete_data():
    print("🚀 Starting L2 Cleaning: Compound Identification & Completion...")
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            l1_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ ERROR: Input file '{INPUT_FILE}' not found.")
        return

    # --- Step 1: Scanning & Learning ---
    print("   - Step 1: Analyzing CAS-Name relationships...")
    
    cas_to_names = defaultdict(set)     # 黄金配对: CAS -> {Names}
    name_to_cas = defaultdict(set)      # 反向索引: Name -> {CAS}
    cas_only_set = set()                # 只有 CAS 的记录
    name_only_set = set()               # 只有 Name 的记录 (潜在 Orphan)
    
    for rec in l1_data:
        cas = str(rec.get("CAS_number") or "").strip()
        name = str(rec.get("compound_english_name") or "").strip()
        
        has_cas = (cas and cas.lower() not in ['none', 'null'])
        has_name = (name and name.lower() not in ['none', 'null'])
        
        if has_cas and has_name:
            cas_to_names[cas].add(name)
            name_to_cas[name.lower()].add(cas)
        elif has_cas and not has_name:
            cas_only_set.add(cas)
        elif has_name and not has_cas:
            name_only_set.add(name) # 注意：这里存原始大小写
            
    print(f"     Found {len(cas_to_names)} Gold CAS, {len(cas_only_set)} CAS-only, {len(name_only_set)} Name-only entries.")

    # --- Step 2: Completion (Patching L1 Data) ---
    print("   - Step 2: Patching detection records...")
    l2_records = []
    log = {"cas_filled": 0, "name_filled": 0}
    
    for rec in l1_data:
        new_rec = rec.copy()
        cas = str(new_rec.get("CAS_number") or "").strip()
        name = str(new_rec.get("compound_english_name") or "").strip()
        
        # 补全 CAS
        if not cas or cas.lower() in ['none', 'null']:
            if name.lower() in name_to_cas and len(name_to_cas[name.lower()]) == 1:
                new_rec["CAS_number"] = list(name_to_cas[name.lower()])[0]
                log["cas_filled"] += 1
        
        # 补全 Name
        if not name or name.lower() in ['none', 'null']:
            if cas in cas_to_names:
                # 选最短的名字
                new_rec["compound_english_name"] = min(cas_to_names[cas], key=len)
                log["name_filled"] += 1
                
        l2_records.append(new_rec)

    # --- Step 3: Generating Compounds List ---
    print("   - Step 3: Generating final compounds list...")
    final_compounds = []
    
    # 3.1 处理 Gold Standard (Verified)
    processed_cas = set()
    verified_names_lower = set() # 用于去重 Orphan
    
    for cas, names_set in cas_to_names.items():
        preferred_name = min(names_set, key=len)
        synonyms = list(names_set - {preferred_name})
        
        final_compounds.append({
            "cas_number": cas,
            "preferred_name": preferred_name,
            "synonyms": synonyms,
            "status": "Verified"
        })
        processed_cas.add(cas)
        for n in names_set: verified_names_lower.add(n.lower())

    # 3.2 处理 CAS-Only (Recycled as Verified)
    for cas in cas_only_set:
        if cas not in processed_cas:
            final_compounds.append({
                "cas_number": cas,
                "preferred_name": f"Unknown Compound ({cas})",
                "synonyms": [],
                "status": "Verified" # 有 CAS 就算 Verified
            })
            processed_cas.add(cas)
            print(f"     -> Recovered CAS-only record: {cas}")

    # 3.3 处理 Orphan (True Name-Only)
    orphan_count = 0
    unique_orphan_names = set() # 防止同名 Orphan 重复添加
    
    for name in name_only_set:
        if name.lower() in verified_names_lower:
            continue # 这个名字已经在 Gold 库里有身份了，不算 Orphan
            
        if name.lower() not in unique_orphan_names:
            final_compounds.append({
                "cas_number": None,
                "preferred_name": name,
                "synonyms": [],
                "status": "Orphan"
            })
            unique_orphan_names.add(name.lower())
            orphan_count += 1

    print(f"     Generated {len(final_compounds)} compounds: {len(processed_cas)} Verified, {orphan_count} Orphan.")

    # --- 保存 ---
    with open(OUTPUT_COMPOUNDS, 'w', encoding='utf-8') as f:
        json.dump(final_compounds, f, indent=2, ensure_ascii=False)
    with open(OUTPUT_DETECTIONS_L2, 'w', encoding='utf-8') as f:
        json.dump(l2_records, f, indent=2, ensure_ascii=False)
        
    print(f"💾 Saved to {OUTPUT_COMPOUNDS} and {OUTPUT_DETECTIONS_L2}")

if __name__ == "__main__":
    build_compounds_and_complete_data()