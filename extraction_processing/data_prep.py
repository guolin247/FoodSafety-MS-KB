import json
import os
import pandas as pd

# 配置路径
RAW_DATA_FOLDER = r"D:\work_GuoLin\PDFreader\data_files\raw_data"  # 存放你分批提取的 json 文件的目录
OUTPUT_DETECTIONS = r"D:\work_GuoLin\PDFreader\data_files\raw_data\detections.json"
OUTPUT_COMPOUNDS = r"D:\work_GuoLin\PDFreader\data_files\raw_data\compounds.json"

def merge_and_extract():
    all_detections = []
    
    # 1. 遍历文件夹合并所有 detection 数据
    # ------------------------------------------------
    print(f"📂 Scanning {RAW_DATA_FOLDER}...")
    if not os.path.exists(RAW_DATA_FOLDER):
        print(f"❌ Folder {RAW_DATA_FOLDER} not found. Please create it and put your JSON files in it.")
        return

    for filename in os.listdir(RAW_DATA_FOLDER):
        if filename.endswith(".json"):
            file_path = os.path.join(RAW_DATA_FOLDER, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 兼容处理：有些可能提取是一个 list，有些可能是单个 dict
                    if isinstance(data, dict) and "detections" in data:
                        all_detections.extend(data["detections"])  # 剥壳取肉
                    elif isinstance(data, list):
                        all_detections.extend(data)
                    elif isinstance(data, dict):
                        all_detections.append(data)
                print(f"  ✅ Loaded {filename}")
            except Exception as e:
                print(f"  ❌ Error loading {filename}: {e}")

    print(f"📊 Total detections merged: {len(all_detections)}")
    
    # 保存合并后的 detections.json
    with open(OUTPUT_DETECTIONS, 'w', encoding='utf-8') as f:
        json.dump(all_detections, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved to {OUTPUT_DETECTIONS}")

    # 2. 生成简易版 compounds.json
    # ------------------------------------------------
    print("⚗️ Extracting unique compounds...")
    
    unique_compounds = {}
    
    for item in all_detections:
        cas = str(item.get("CAS_number", "")).strip()
        name = str(item.get("compound_english_name", "")).strip()
        
        # 跳过无效数据
        if not cas or cas.lower() == "none":
            continue
            
        # 以 CAS 为键进行去重
        if cas not in unique_compounds:
            unique_compounds[cas] = {
                "CAS_number": cas,
                "compound_english_name": name,
                # 预留字段，等以后爬虫爬到了再填
                "formula": None, 
                "classification": None,
                "mol_weight": None
            }
    
    # 转回 List 格式
    compounds_list = list(unique_compounds.values())
    print(f"📊 Total unique compounds found: {len(compounds_list)}")
    
    # 保存 compounds.json
    with open(OUTPUT_COMPOUNDS, 'w', encoding='utf-8') as f:
        json.dump(compounds_list, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved to {OUTPUT_COMPOUNDS}")

if __name__ == "__main__":
    merge_and_extract()