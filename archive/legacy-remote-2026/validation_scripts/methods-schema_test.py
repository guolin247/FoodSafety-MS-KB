import json
import os
import pandas as pd
from jsonschema import validate, exceptions
from datetime import datetime

# ================= CONFIGURATION =================
# 您的方法文件所在文件夹 (里面是单个的 .txt/.json 文件)
DATA_FOLDER = r"D:\work_GuoLin\FoodSafety-MS-KB\validation_scripts\methods"
# 您的 Schema 文件路径
SCHEMA_PATH = r"D:\work_GuoLin\FoodSafety-MS-KB\validation_scripts\schema.json"
# 输出 Excel 路径
OUTPUT_LOG = "Table_S2_Methods_Structural_Audit.xlsx"
# ============================================

# 定义方法定义在 Schema 中的路径
METHOD_DEFINITION_PATH = ["definitions", "methods"]

def load_json_file(file_path):
    """加载 JSON 文件内容 (复用原脚本逻辑)"""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def get_method_schema_content(schema):
    """(复用原脚本) 提取原始属性字典"""
    current_def = schema
    try:
        for key in METHOD_DEFINITION_PATH:
            current_def = current_def[key]
        return current_def
    except KeyError:
        return None

def get_validation_schema(schema):
    """(复用原脚本) 构建验证用根 Schema"""
    method_properties = get_method_schema_content(schema)
    if method_properties is None:
        return None
    
    return {
        "type": "object",
        "properties": method_properties,
        "required": list(method_properties.keys())
    }

def validate_schema_compliance(data, schema):
    """(复用原脚本逻辑，改为返回状态字符串)"""
    method_schema = get_validation_schema(schema)
    if method_schema is None:
        return "Schema Error", "Cannot build schema"
        
    try:
        validate(instance=data, schema=method_schema)
        return "PASS", ""
    except exceptions.ValidationError as e:
        return "FAIL", e.message[:200]
    except Exception as e:
        return "FAIL", str(e)

def check_key_presence(data, schema_properties, path=""):
    """(复用原脚本) 递归检查键完整性"""
    missing_keys = []
    
    for key, definition in schema_properties.items():
        current_path = f"{path}.{key}" if path else key
        
        if key not in data:
            missing_keys.append(current_path)
            continue

        if definition.get("type") == "object":
            if "properties" in definition and isinstance(data[key], dict) and data[key] is not None:
                missing_keys.extend(
                    check_key_presence(data[key], definition["properties"], current_path)
                )
            
        elif definition.get("type") == "array" and "items" in definition:
            item_schema = definition["items"]
            if item_schema.get("type") == "object" and "properties" in item_schema and isinstance(data[key], list):
                for i, item_data in enumerate(data[key]):
                    item_path = f"{current_path}[{i}]" 
                    if isinstance(item_data, dict) and item_data is not None:
                        missing_keys.extend(
                            check_key_presence(item_data, item_schema["properties"], item_path)
                        )
    
    return missing_keys

def run_batch_validation():
    print(f"🚀 Starting Batch Method Validation...")
    
    # 1. Load Schema
    schema_content = load_json_file(SCHEMA_PATH)
    if not schema_content:
        print("❌ Critical Error: Cannot load schema.")
        return

    schema_props = get_method_schema_content(schema_content)
    if not schema_props:
        print("❌ Critical Error: Invalid schema structure.")
        return

    # 2. Iterate Files
    results = []
    files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(('.json', '.txt'))]
    print(f"📊 Found {len(files)} files to process.")

    for filename in files:
        file_path = os.path.join(DATA_FOLDER, filename)
        
        # Load Data
        data = load_json_file(file_path)
        
        if not data:
            results.append({
                "File Name": filename,
                "Method ID": "Load Error",
                "Schema Validation": "FAIL",
                "Completeness Check": "FAIL",
                "Notes": "JSON Decode Error"
            })
            continue

        # Extract Method ID
        method_id = data.get("method_identification", {}).get("method_id", "Unknown")

        # Check 1: Schema Compliance
        schema_status, schema_note = validate_schema_compliance(data, schema_content)

        # Check 2: Completeness
        missing = check_key_presence(data, schema_props)
        if not missing:
            completeness_status = "PASS"
            completeness_note = ""
        else:
            completeness_status = "FAIL"
            completeness_note = f"Missing keys: {', '.join(missing[:3])}..."

        # Console Log
        icon = "✅" if (schema_status == "PASS" and completeness_status == "PASS") else "❌"
        print(f"  {icon} {filename} | ID: {method_id}")

        results.append({
            "File Name": filename,
            "Method ID": method_id,
            "Schema Validation": schema_status,
            "Completeness Check": completeness_status,
            "Notes": f"{schema_note} {completeness_note}".strip(),
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    # 3. Save Report
    df = pd.DataFrame(results)
    df.to_excel(OUTPUT_LOG, index=False)
    print(f"\n💾 Validation Log saved to: {OUTPUT_LOG}")
    
    # Summary
    pass_count = len(df[(df["Schema Validation"] == "PASS") & (df["Completeness Check"] == "PASS")])
    print(f"📈 Summary: {pass_count}/{len(files)} files passed all checks.")

if __name__ == "__main__":
    run_batch_validation()