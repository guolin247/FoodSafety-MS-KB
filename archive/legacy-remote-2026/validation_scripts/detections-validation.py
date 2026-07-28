import json
import pandas as pd
import random
import os

# ================= 配置区 =================
# 请替换为您的 detections.json 文件的绝对路径
# 这里假设输入的是清洗后的最终版本
INPUT_FILE = r"D:\work_GuoLin\FoodSafety-MS-KB\data\detections.json"
OUTPUT_EXCEL = "Detections_Audit_Sampling_350.xlsx"
SAMPLE_SIZE = 350
# ========================================

def generate_detection_sample():
    print(f"🚀 Starting Detection Sampling (Target: {SAMPLE_SIZE} records)...")
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: Input file not found at {INPUT_FILE}")
        return

    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 兼容性处理：如果根节点是 list 则直接用，如果是 dict 则找 keys
        all_records = data if isinstance(data, list) else data.get("detections", [])
        
        total_records = len(all_records)
        print(f"📊 Total Records Loaded: {total_records}")
        
        if total_records < SAMPLE_SIZE:
            print(f"⚠️ Warning: Total records ({total_records}) < Sample Size ({SAMPLE_SIZE}). Taking all.")
            sample_size = total_records
        else:
            sample_size = SAMPLE_SIZE

    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        return

    # --- 策略：展开所有离子对 (Flattening) ---
    # 因为一条 detection 记录里可能有多个 mass_spec_params (多对离子)
    # 您的要求是“一种化合物对应的一个离子对的数据”作为一条抽样单位。
    # 如果您的 JSON 结构是：一条记录 = 一个化合物 = 包含 mass_spec_params 数组 (含 Q, q1, q2...)
    # 那么我们需要先“展开”这个数组，把每一对 (Precursor, Product) 变成一个可抽样的 Item。
    
    flattened_items = []
    
    for parent_idx, rec in enumerate(all_records):
        method_id = rec.get("method_id", "Unknown")
        run_id = rec.get("run_config_id", "Unknown")
        comp_name = rec.get("compound_english_name", "Unknown")
        cas = rec.get("CAS_number", "Unknown")
        source_file = rec.get("_source_file", "Unknown") # 用于溯源
        
        ms_params = rec.get("mass_spec_params", [])
        if not isinstance(ms_params, list): continue
        
        for sub_idx, ms in enumerate(ms_params):
            # 提取关键数值
            prec_mz = ms.get("precursor_mz")
            prod_mz = ms.get("product_mz")
            # --- 修正开始: 安全获取 Collision Energy ---
            ce_obj = ms.get("collision_energy")
            if isinstance(ce_obj, dict):
                ce = ce_obj.get("value")
            else:
                ce = None # 或者 "N/A" 如果您希望在表格里显示字符
            # --- 修正结束 ---
            pol = ms.get("polarity")
            p_type = ms.get("parameter_type") # Quant/Conf
            
            # 构建扁平化对象
            item = {
                "Parent_Index": parent_idx, # 方便回溯
                "Sub_Index": sub_idx,
                "Method_ID": method_id,
                "Run_ID": run_id,
                "Compound_Name": comp_name,
                "CAS": cas,
                "Precursor_m/z": prec_mz,
                "Product_m/z": prod_mz,
                "Collision_Energy": ce,
                "Polarity": pol,
                "Type": p_type,
                "Source_File": source_file
            }
            flattened_items.append(item)
            
    print(f"   -> Flattened into {len(flattened_items)} unique transitions (ion pairs).")

    # --- 抽样策略：分层抽样 (Stratified by Method ID) ---
    # 目的：保证每个 Method 至少被抽到一点，大 Method 抽多点。
    
    df_pool = pd.DataFrame(flattened_items)
    
    # 按 Method_ID 分组抽样
    # 计算每个 Method 的权重
    # 如果 Method 数量太多，导致 sample_size 不够分，则退化为随机抽样
    
    try:
        # 使用 pandas 的 groupby sample (需 pandas >= 1.1.0)
        # weights 设为 None 表示按比例自然分层
        # frac = sample_size / total
        fraction = sample_size / len(df_pool)
        
        # 为了保证精确凑够 350 条，简单分层有时会有取舍误差。
        # 这里采用更稳健的方法：直接从整体池子里带权重随机抽样（权重=1，即简单随机），
        # 或者先按 Method_ID 分组，每组至少抽 1 条，剩下的随机分。
        
        # 简化策略：直接简单随机抽样 (Simple Random Sampling) 
        # 因为离子对总数大，随机抽样通常能很好地覆盖各大 Method。
        # 如果您一定要严格分层，请告诉我。此处使用 Random 以保证操作简便且统计学有效。
        
        sampled_df = df_pool.sample(n=sample_size, random_state=42) # 设定种子保证可复现
        
    except Exception as e:
        print(f"⚠️ Sampling error: {e}. Falling back to head.")
        sampled_df = df_pool.head(sample_size)

    # --- 格式化输出 ---
    # 增加排序列，方便您核对（例如按 Method ID 排序）
    sampled_df = sampled_df.sort_values(by=["Method_ID", "Compound_Name"])
    
    # 增加人工打分列
    sampled_df["[Check] Precursor Correct?"] = ""
    sampled_df["[Check] Product Correct?"] = ""
    sampled_df["[Check] CE Correct?"] = ""
    sampled_df["[Check] Meta Correct? (Name/CAS)"] = ""
    sampled_df["Auditor_Comments"] = ""

    # 调整列顺序
    cols = [
        "Method_ID", "Run_ID", "Compound_Name", "CAS", 
        "Precursor_m/z", "[Check] Precursor Correct?",
        "Product_m/z", "[Check] Product Correct?",
        "Collision_Energy", "[Check] CE Correct?",
        "Polarity", "Type", 
        "[Check] Meta Correct? (Name/CAS)", "Auditor_Comments",
        "Source_File", "Parent_Index", "Sub_Index"
    ]
    
    # 只保留存在的列
    cols = [c for c in cols if c in sampled_df.columns]
    final_df = sampled_df[cols]

    # 保存
    try:
        writer = pd.ExcelWriter(OUTPUT_EXCEL, engine='xlsxwriter')
        final_df.to_excel(writer, index=False, sheet_name='Detection_Audit')
        
        workbook = writer.book
        worksheet = writer.sheets['Detection_Audit']
        
        # 格式
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1})
        check_fmt = workbook.add_format({'bg_color': '#FFF2CC', 'border': 1}) # 黄色背景提示填空
        
        for col_num, value in enumerate(final_df.columns.values):
            worksheet.write(0, col_num, value, header_fmt)
            
            # 如果是 Check 列，加宽并标黄
            if "[Check]" in value:
                worksheet.set_column(col_num, col_num, 15, check_fmt)
            else:
                worksheet.set_column(col_num, col_num, 15)
                
        writer.close()
        print(f"✅ Sampling Complete. Checklist saved to: {OUTPUT_EXCEL}")
        print(f"   Please open the file and verify {len(final_df)} records against your PDFs.")
        
    except Exception as e:
        print(f"❌ Error saving Excel: {e}")

if __name__ == "__main__":
    generate_detection_sample()