import json
import pandas as pd
import os

# ================= 配置区 =================
# 请替换为您的 method.json 文件的绝对路径
INPUT_FILE = r"D:\work_GuoLin\FoodSafety-MS-KB\data\methods.json" 
OUTPUT_EXCEL = "Methods_Audit_Checklist.xlsx"
# ========================================

def generate_audit_checklist():
    print(f"🚀 Starting Audit Checklist Generation...")
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: Input file not found at {INPUT_FILE}")
        return

    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            methods_data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        return

    # 准备数据列表
    rows = []

    for method in methods_data:
        # 获取 Method ID (从 method_identification 中)
        # 注意：根据您的Schema，method_identification 是一个 key，下面才是 method_id
        # 如果您的 json 结构不同，请根据实际情况微调。
        # 假设结构是: { "method_identification": { "method_id": "..." }, "analytical_runs": [...] }
        
        m_id_info = method.get("method_identification", {})
        method_id = m_id_info.get("method_id", "Unknown_ID")
        
        # 获取 Analytical Runs
        runs = method.get("analytical_runs", [])
        
        if not runs:
            # 如果没有 runs，也记录一条，标注为无 Runs
            rows.append({
                "Method ID": method_id,
                "Run Config ID": "NO_RUNS",
                "Method Identification": "", # 预留空位给人工打勾
                "Analytical Runs Structure": "",
                "Sample Info": "N/A",
                "Sample Prep": "N/A",
                "Chromatography": "N/A",
                "Mass Spec": "N/A",
                "Aug: Matrix Tags": "N/A",
                "Aug: Mobile Phase": "N/A",
                "Aug: Prep Steps": "N/A",
                "Aug: Instrument": "N/A",
                "Auditor Comments": "No analytical runs found"
            })
            continue

        for run in runs:
            run_id = run.get("run_config_id", "Unknown_Run")
            
            # 提取一些关键信息供 Auditor 参考 (Optional，方便核对)
            # 例如：把 Solvent 提取出来显示在批注里，方便核对
            # 这里我们只生成空的 Checkbox 列，或者您可以选择填入 'Pending'
            
            row = {
                "Method ID": method_id,
                "Run Config ID": run_id,
                
                # --- Check Columns (Auditor to fill 'v' or 'x') ---
                "Method Identification": "", 
                "Analytical Runs Structure": "",
                "Sample Info": "",
                "Sample Prep": "",
                "Chromatography": "",
                "Mass Spec": "",
                
                # --- Augmented Fields Check ---
                "Aug: Matrix Tags": "",
                "Aug: Mobile Phase": "",
                "Aug: Prep Steps": "",
                "Aug: Instrument": "",
                
                # --- Comments ---
                "Auditor Comments": "" 
            }
            
            # 为了方便 Auditor，我们可以把实际值填入 Excel 的批注或者相邻列
            # 这里简单起见，我们只生成打分表。
            # 如果您希望看到实际值以便核对，可以取消下面的注释：
            # row["_Ref_Matrix"] = str(run.get("aug_matrix_tags", ""))
            
            rows.append(row)

    # 创建 DataFrame
    df = pd.read_json(json.dumps(rows)) # 中转一下确保格式
    df = pd.DataFrame(rows)

    # 保存为 Excel
    try:
        # 使用 xlsxwriter 引擎可以设置列宽等格式
        writer = pd.ExcelWriter(OUTPUT_EXCEL, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='Audit_Checklist')
        
        workbook = writer.book
        worksheet = writer.sheets['Audit_Checklist']
        
        # 设置格式：居中，加边框
        cell_format = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'bg_color': '#D7E4BC'})
        
        # 应用格式
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 20) # 设置列宽
            
        # 设置 Method ID 列宽一点
        worksheet.set_column(0, 0, 30)
        
        writer.close()
        print(f"✅ Checklist generated successfully: {OUTPUT_EXCEL}")
        print(f"📊 Total Records to Audit: {len(df)}")
        
    except Exception as e:
        print(f"❌ Error saving Excel: {e}")

if __name__ == "__main__":
    generate_audit_checklist()