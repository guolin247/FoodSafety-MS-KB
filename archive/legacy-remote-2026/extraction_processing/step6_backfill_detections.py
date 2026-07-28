import json
import os

# ================= 配置区 =================
FILE_COMPOUNDS = r"D:\work_GuoLin\PDFreader\compounds_v2.json"          # 包含最新 CAS 和 Name 的知识库
FILE_DETECTIONS_L2 = r"D:\work_GuoLin\PDFreader\FoodSafety_MS_L2_cleaned.json" # 待更新的检测数据
OUTPUT_FILE = "FoodSafety_MS_L2_Final.json"   # 更新后的最终 L2 文件
# ========================================

def backfill_detections():
    print("🚀 Starting Back-fill Process (Injecting V2 Knowledge into Detections)...")
    
    # 1. 加载化合物知识库
    try:
        with open(FILE_COMPOUNDS, 'r', encoding='utf-8') as f:
            compounds = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: {FILE_COMPOUNDS} not found.")
        return

    # 2. 构建查找表 (Lookup Map)
    # 我们需要根据 L2 数据中现有的 Name 来查找最新的 CAS
    # Key: preferred_name (lowercase), Value: cas_number (from v2)
    name_to_cas_map = {}
    
    # 同时也建立 CAS -> Name 的映射，防止数据里只有 CAS 没 Name
    cas_to_name_map = {}
    
    for c in compounds:
        cas = c.get('cas_number')
        name = c.get('preferred_name')
        
        if name:
            name_lower = name.strip().lower()
            if cas: 
                name_to_cas_map[name_lower] = cas
        
        if cas:
            cas_clean = cas.strip()
            if name:
                cas_to_name_map[cas_clean] = name

    print(f"   - Knowledge Base Loaded: {len(name_to_cas_map)} Name->CAS mappings.")

    # 3. 加载 L2 检测数据
    try:
        with open(FILE_DETECTIONS_L2, 'r', encoding='utf-8') as f:
            detections = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: {FILE_DETECTIONS_L2} not found.")
        return

    # 4. 执行回填 (Back-filling)
    filled_cas_count = 0
    filled_name_count = 0
    
    updated_detections = []
    
    for rec in detections:
        # 复制对象
        new_rec = rec.copy()
        
        current_cas = str(new_rec.get('CAS_number') or '').strip()
        current_name = str(new_rec.get('compound_english_name') or '').strip()
        
        # 逻辑 A: 有 Name 无 CAS -> 尝试从 v2 补 CAS
        if (not current_cas or current_cas.lower() == 'none') and current_name:
            target_cas = name_to_cas_map.get(current_name.lower())
            if target_cas:
                new_rec['CAS_number'] = target_cas
                filled_cas_count += 1
                
        # 逻辑 B: 有 CAS 无 Name (罕见但可能) -> 尝试从 v2 补 Name
        if (not current_name or current_name.lower() == 'none') and current_cas:
            target_name = cas_to_name_map.get(current_cas)
            if target_name:
                new_rec['compound_english_name'] = target_name
                filled_name_count += 1
                
        # 逻辑 C: 标准化 Name (可选)
        # 如果你想把所有检测数据里的名字都统一成 compounds_v2 里的 preferred_name
        # if current_name and current_name.lower() in name_to_cas_map:
        #     # new_rec['compound_english_name'] = ... (这里需要反向查找 preferred name)
        #     pass 

        updated_detections.append(new_rec)

    # 5. 保存结果
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(updated_detections, f, indent=2, ensure_ascii=False)
        
    print("-" * 40)
    print(f"✅ Back-fill Complete!")
    print(f"   - Total Detections Processed: {len(updated_detections)}")
    print(f"   - CAS Numbers Filled: {filled_cas_count}")
    print(f"   - Names Filled: {filled_name_count}")
    print(f"   - Saved to: {OUTPUT_FILE}")
    print("\n   👉 Next Step: Use this file as input for 'step3_L3_master_clean.py'")

if __name__ == "__main__":
    backfill_detections()