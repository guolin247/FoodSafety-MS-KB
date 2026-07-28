import json
import os
import pandas as pd
from jsonschema import validate, exceptions
from datetime import datetime

# ================= CONFIGURATION =================
# Detections 文件所在文件夹 (请确认路径正确)
DATA_FOLDER = r"D:\work_GuoLin\FoodSafety-MS-KB\validation_scripts\detections"
# Schema 文件路径 (请确认路径正确)
SCHEMA_PATH = r"D:\work_GuoLin\FoodSafety-MS-KB\validation_scripts\schema.json"
# 输出日志文件
OUTPUT_LOG = "Table_S3_Detections_Diagnostic_Log.xlsx"
# ============================================

# Detections 在 Schema 中的定义路径
DETECTION_DEFINITION_PATH = ["definitions", "detections"]

def load_json_file(file_path):
    """加载 JSON 文件内容"""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def get_detection_schema_content(schema):
    """提取 detections 的原始属性定义"""
    current_def = schema
    try:
        for key in DETECTION_DEFINITION_PATH:
            current_def = current_def[key]
        return current_def
    except KeyError:
        return None

def get_item_validation_schema(schema):
    """构建单个 Detection Item 的验证 Schema (含 AnyOf 规则，且允许 Null)"""
    detection_properties = get_detection_schema_content(schema)
    if detection_properties is None: return None
    
    # 浅拷贝 properties
    modified_properties = detection_properties.copy()
    
    # 1. 允许 CAS_number 为 null
    if "CAS_number" in modified_properties:
        orig = modified_properties["CAS_number"].copy()
        if orig.get("type") == "string": orig["type"] = ["string", "null"]
        modified_properties["CAS_number"] = orig

    # 2. 允许 compound_english_name 为 null
    if "compound_english_name" in modified_properties:
        orig = modified_properties["compound_english_name"].copy()
        if orig.get("type") == "string": orig["type"] = ["string", "null"]
        modified_properties["compound_english_name"] = orig

    # 3. [NEW] 允许 mass_spec_params 里的 collision_energy 为 null
    # 这比较深，需要进到 items -> properties
    if "mass_spec_params" in modified_properties:
        msp = modified_properties["mass_spec_params"].copy()
        if "items" in msp:
            msp_items = msp["items"].copy()
            if "properties" in msp_items:
                msp_props = msp_items["properties"].copy()
                if "collision_energy" in msp_props:
                    ce_def = msp_props["collision_energy"].copy()
                    # 放宽类型：允许 object 或 null
                    if ce_def.get("type") == "object":
                        ce_def["type"] = ["object", "null"]
                    msp_props["collision_energy"] = ce_def
                msp_items["properties"] = msp_props
            msp["items"] = msp_items
        modified_properties["mass_spec_params"] = msp

    return {
        "type": "object",
        "properties": modified_properties,
        "anyOf": [
            # 这里的逻辑保持不变：要求至少有一个字段是非空的 String
            {"properties": {"CAS_number": {"type": "string"}}, "required": ["CAS_number"]},
            {"properties": {"compound_english_name": {"type": "string"}}, "required": ["compound_english_name"]}
        ]
    }

def check_key_presence(data, schema_properties, path=""):
    """
    递归检查键完整性。
    兼容性逻辑：只要键存在，值为 None 也视为通过。
    """
    missing_keys = []
    
    for key, definition in schema_properties.items():
        current_path = f"{path}.{key}" if path else key
        
        # 1. 检查键是否存在
        if key not in data:
            missing_keys.append(current_path)
            continue
        
        # 2. 如果键存在但值为 None，直接视为通过，不检查子结构
        if data[key] is None:
            continue

        # 3. 如果是对象，递归检查
        if definition.get("type") == "object":
            if "properties" in definition and isinstance(data[key], dict):
                missing_keys.extend(
                    check_key_presence(data[key], definition["properties"], current_path)
                )
            
        # 4. 如果是数组，遍历检查每个元素
        elif definition.get("type") == "array" and "items" in definition:
            item_schema = definition.get("items", {})
            if item_schema.get("type") == "object" and "properties" in item_schema and isinstance(data[key], list):
                for i, item_data in enumerate(data[key]):
                    item_path = f"{current_path}[{i}]" 
                    if isinstance(item_data, dict):
                        missing_keys.extend(
                            check_key_presence(item_data, item_schema["properties"], item_path)
                        )
    
    return missing_keys

def run_batch_validation():
    print(f"🚀 Starting DIAGNOSTIC Detections Validation...")
    print(f"📂 Scanning: {DATA_FOLDER}")
    
    # 1. Load Schema
    schema_content = load_json_file(SCHEMA_PATH)
    if not schema_content:
        print("❌ Critical Error: Cannot load schema.")
        return

    schema_props = get_detection_schema_content(schema_content)
    item_validator = get_item_validation_schema(schema_content)
    
    if not schema_props or not item_validator:
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
        if data is None:
            results.append({"File Name": filename, "Status": "Load Error"})
            continue
            
        # --- 1. 自适应数据结构 (Auto-unwrap) ---
        target_list = []
        is_unwrapped = False
        
        if isinstance(data, list):
            target_list = data
        elif isinstance(data, dict):
            # 尝试找 detections 键
            if "detections" in data and isinstance(data["detections"], list):
                target_list = data["detections"]
                is_unwrapped = True
            else:
                # 尝试将整个字典作为单条记录
                target_list = [data]
                is_unwrapped = True # 标记为经过了处理
        
        # --- 2. 逐条验证 ---
        file_errors = []
        
        for idx, item in enumerate(target_list):
            # Schema Check
            try:
                validate(instance=item, schema=item_validator)
            except exceptions.ValidationError as e:
                # 记录详细错误路径
                path_str = ".".join(str(x) for x in e.path) if e.path else "root"
                file_errors.append(f"[Row {idx}] Schema: {e.message} @ {path_str}")
            
            # Completeness Check
            missing = check_key_presence(item, schema_props)
            if missing:
                file_errors.append(f"[Row {idx}] Missing Keys: {', '.join(missing[:3])}")

        # --- 3. 结果汇总与输出 ---
        is_pass = len(file_errors) == 0
        icon = "✅" if is_pass else "❌"
        
        # 构建状态描述
        status_msg = f"{filename}"
        if is_unwrapped:
            status_msg += " (Unwrapped)"
        
        print(f"  {icon} {status_msg} | Records: {len(target_list)}")
        
        if not is_pass:
            # 打印前3个错误供诊断
            for err in file_errors[:3]:
                print(f"     -> {err}")
            if len(file_errors) > 3:
                print(f"     -> ... ({len(file_errors)-3} more errors)")

        results.append({
            "File Name": filename,
            "Record Count": len(target_list),
            "Status": "PASS" if is_pass else "FAIL",
            "Error Count": len(file_errors),
            "First 3 Errors": " || ".join(file_errors[:3]),
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    # 3. Save Report
    df = pd.DataFrame(results)
    df.to_excel(OUTPUT_LOG, index=False)
    print(f"\n💾 Diagnostic Log saved to: {OUTPUT_LOG}")
    
    # Summary
    pass_count = len(df[df["Status"] == "PASS"])
    print(f"📈 Summary: {pass_count}/{len(files)} files passed all checks.")

if __name__ == "__main__":
    run_batch_validation()