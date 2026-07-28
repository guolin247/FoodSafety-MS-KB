import json
import os
import datetime

# ================= 配置区 =================
INPUT_FOLDER = r"D:\work_GuoLin\FoodSafety-MS-KB\extraction_processing\raw_data"
OUTPUT_FILE = "FoodSafety_MS_Raw_v1.json"
LOG_FILE = "L1_cleaning_log.md"
# ========================================

class AuditLogger:
    def __init__(self):
        self.logs = []
        self.stats = {
            "total_files": 0,
            "total_input_records": 0,
            "total_output_records": 0,
            "dropped_records": [],
            "structure_fixes": [],
            "string_cleanups": 0
        }

    def log_structure_fix(self, filename, original_type):
        self.stats["structure_fixes"].append(f"File **{filename}** converted from `{original_type}` to `List`.")

    def log_dropped(self, filename, index, reason, snippet):
        self.stats["dropped_records"].append({
            "file": filename,
            "index": index,
            "reason": reason,
            "snippet": str(snippet)[:100] + "..." # 只记录前100个字符用于核对
        })

    def increment_string_clean(self):
        self.stats["string_cleanups"] += 1

    def save_report(self, filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# Data Cleaning Audit Log (L1)\n")
            f.write(f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## 1. Summary Statistics\n")
            f.write(f"- **Files Processed:** {self.stats['total_files']}\n")
            f.write(f"- **Total Input Records:** {self.stats['total_input_records']}\n")
            f.write(f"- **Total Valid Output:** {self.stats['total_output_records']}\n")
            f.write(f"- **Dropped Records:** {len(self.stats['dropped_records'])}\n")
            f.write(f"- **String Format Fixes (whitespace/newlines):** {self.stats['string_cleanups']}\n\n")
            
            f.write("## 2. Structure Normalization\n")
            if self.stats["structure_fixes"]:
                for fix in self.stats["structure_fixes"]:
                    f.write(f"- {fix}\n")
            else:
                f.write("- No structural anomalies found.\n")
            
            f.write("\n## 3. Dropped Records Detail\n")
            if self.stats["dropped_records"]:
                f.write("| File | Index | Reason | Snippet |\n")
                f.write("|---|---|---|---|\n")
                for item in self.stats["dropped_records"]:
                    f.write(f"| {item['file']} | {item['index']} | {item['reason']} | `{item['snippet']}` |\n")
            else:
                f.write("- No records were dropped.\n")
                
        print(f"📝 Audit log saved to {filepath}")

auditor = AuditLogger()

def clean_string_with_audit(val):
    """递归清洗字符串，并计数"""
    if isinstance(val, str):
        # 检查是否有需要清洗的内容
        cleaned = val.strip().replace('\n', ' ').replace('\t', ' ')
        if cleaned != val:
            auditor.increment_string_clean()
        return cleaned
    elif isinstance(val, list):
        return [clean_string_with_audit(x) for x in val]
    elif isinstance(val, dict):
        return {k: clean_string_with_audit(v) for k, v in val.items()}
    else:
        return val

def process_l1_cleaning():
    print(f"🧹 Re-running L1 Cleaning with Audit...")
    
    all_records = []
    
    if not os.path.exists(INPUT_FOLDER):
        print("❌ Input folder not found.")
        return

    for filename in os.listdir(INPUT_FOLDER):
        if not filename.endswith(".json"): continue
        
        filepath = os.path.join(INPUT_FOLDER, filename)
        auditor.stats["total_files"] += 1
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            
            # 1. 结构诊断与修复
            current_batch = []
            if isinstance(raw, list):
                current_batch = raw
            elif isinstance(raw, dict):
                auditor.log_structure_fix(filename, "Dict")
                if "detections" in raw:
                    current_batch = raw["detections"]
                else:
                    current_batch = [raw]
            
            auditor.stats["total_input_records"] += len(current_batch)
            
            # 2. 逐条清洗
            for idx, rec in enumerate(current_batch):
                # 2.1 完整性检查
                ms_params = rec.get("mass_spec_params")
                if not ms_params or (isinstance(ms_params, list) and len(ms_params) == 0):
                    # 记录丢弃原因
                    compound_name = rec.get("compound_english_name", "Unknown")
                    auditor.log_dropped(filename, idx, "Empty/Missing MS Params", f"Compound: {compound_name}")
                    continue
                
                # 2.2 字符串净化
                cleaned_rec = clean_string_with_audit(rec)
                
                # 2.3 注入来源
                cleaned_rec["_source_file"] = filename
                
                all_records.append(cleaned_rec)
                
        except Exception as e:
            print(f"  ❌ Error processing {filename}: {e}")

    auditor.stats["total_output_records"] = len(all_records)

    # 3. 保存数据
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    
    # 4. 保存日志
    auditor.save_report(LOG_FILE)
    print(f"💾 Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_l1_cleaning()