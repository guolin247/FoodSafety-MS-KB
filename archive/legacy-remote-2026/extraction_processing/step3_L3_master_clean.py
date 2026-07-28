import json
import pandas as pd
import datetime

# ================= 配置区 =================
INPUT_FILE = r"D:\work_GuoLin\FoodSafety-MS-KB\FoodSafety_MS_L2_cleaned.json" # L2 清洗后的输入
OUTPUT_JSON = "FoodSafety_MS_Master.json"
OUTPUT_CSV = "FoodSafety_MS_Master.csv"
LOG_FILE = "L3_cleaning_log.md"
# ========================================

class L3MasterCleaner:
    def __init__(self):
        # 定义需要被“提拔”为独立列的 performance_parameters 的键名同义词
        self.key_mappings = {
            'RT_min': ['rt', 'retention time', 'relative_retention_time', 'r.t.'],
            'LOQ': ['loq', 'limit of quantification', 'lod', 'detection_sensitivity', 'concentration'],
            'Matrix_Tag': ['context', 'matrix', 'solvent', 'group', 'source'],
            'DP_V': ['dp', 'declustering potential', 'cone voltage'],
            'EP_V': ['ep', 'entrance potential'],
            'CXP_V': ['cxp', 'collision cell exit potential'],
            'FV_V': ['fv', 'fragmentor voltage', 'in-source fragmentation voltage', 'source fragmentation voltage']
        }
        # 构建一个反向查找表，用于识别哪些key已经被提拔
        self.promoted_keys = {item for sublist in self.key_mappings.values() for item in sublist}
        
        # 定义需要标准化的词汇表
        self.type_map = {
            'quantification': 'Quant', 'quant': 'Quant', '定量': 'Quant',
            'confirmation': 'Qual', 'qual': 'Qual', '定性': 'Qual'
        }
        self.pol_map = {
            'positive': 'Pos', 'pos': 'Pos', 'esi+': 'Pos', '+': 'Pos', '正': 'Pos',
            'negative': 'Neg', 'neg': 'Neg', 'esi-': 'Neg', '-': 'Neg', '负': 'Neg'
        }

    def clean_ce(self, ce_raw):
        """清洗 CE，返回 (Value, Unit)"""
        val, unit = None, 'V'
        if isinstance(ce_raw, dict):
            val, unit = ce_raw.get('value'), ce_raw.get('unit', 'V')
        elif ce_raw is not None:
            val = ce_raw
        
        if val is not None:
            try:
                if str(val).lower() in ['m', 'l', 'h']:
                    return str(val).lower(), 'Category'
                val_str = str(val).lower().replace('ev', '').replace('v', '').strip()
                return float(val_str), 'V' if 'ev' in str(unit).lower() or 'v' in str(unit).lower() else unit
            except (ValueError, TypeError):
                return str(val), unit
        return None, None

    def process_records(self, l2_data):
        master_rows = []
        
        for rec in l2_data:
            # 1. 提取公共字段
            common_info = {
                "Method_ID": rec.get("method_id"),
                "Run_ID": rec.get("run_config_id"),
                "Compound": rec.get("compound_english_name"),
                "CAS": rec.get("CAS_number"),
                "Source_File": rec.get("_source_file")
            }

            # 2. 提取并归一化 Performance Parameters
            perfs = rec.get("performance_parameters", []) or []
            promoted_params = {}
            other_params = {}
            
            for p in perfs:
                p_name = str(p.get("parameter_name", "")).lower().strip()
                is_promoted = False
                # 检查是否是需要提拔的字段
                for target_col, synonyms in self.key_mappings.items():
                    if p_name in synonyms:
                        # 只取第一个找到的值，避免重复
                        if target_col not in promoted_params:
                            promoted_params[target_col] = p.get('value')
                        is_promoted = True
                        break
                
                # 如果没有被提拔，放入 Other_Params
                if not is_promoted:
                    val = p.get('value')
                    unit = p.get('unit')
                    full_val = f"{val} {unit}" if unit else str(val)
                    other_params[p.get("parameter_name")] = full_val

            # 3. 爆炸 MS Params
            ms_list = rec.get("mass_spec_params", []) or []
            if not ms_list: # 如果没有离子对，跳过此记录
                continue

            for ms in ms_list:
                row = {**common_info, **promoted_params} # 合并公共信息和提拔的性能参数
                
                # 填充质谱信息
                row["Precursor_mz"] = ms.get("precursor_mz")
                row["Product_mz"] = ms.get("product_mz")
                
                # 清洗 Polarity
                raw_pol = str(ms.get("polarity", "")).lower()
                row["Polarity"] = next((v for k, v in self.pol_map.items() if k in raw_pol), "N/A") if raw_pol != 'none' else None

                # 清洗 Type
                raw_type = str(ms.get("parameter_type", "") or ms.get("source_ion_label", "")).lower()
                row["Type"] = next((v for k, v in self.type_map.items() if k in raw_type), "Target")
                
                # 清洗 CE
                row["CE_Value"], row["CE_Unit"] = self.clean_ce(ms.get("collision_energy"))
                
                # 保留长尾参数
                row["Other_Params"] = json.dumps(other_params) if other_params else None
                
                master_rows.append(row)
                
        return master_rows

# ================= 执行 =================
if __name__ == "__main__":
    print("🚀 Starting L3 Master Cleaning (Exploding, Normalizing, Preserving)...")
    
    cleaner = L3MasterCleaner()
    log = {}
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            l2_data = json.load(f)
        log['input_records'] = len(l2_data)
            
        cleaned_rows = cleaner.process_records(l2_data)
        log['output_rows'] = len(cleaned_rows)
        
        # 保存 CSV (推荐用于数据附件)
        df = pd.DataFrame(cleaned_rows)
        # 重新排序列，让核心列在前
        core_cols = ['Method_ID', 'Run_ID', 'Compound', 'CAS', 'Precursor_mz', 'Product_mz', 'Polarity', 'Type', 'CE_Value', 'RT_min', 'LOQ', 'Matrix_Tag']
        other_cols = [c for c in df.columns if c not in core_cols]
        df = df[core_cols + other_cols]
        df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
        print(f"✅ CSV Saved: {OUTPUT_CSV} (Total Rows: {log['output_rows']})")
        
        # 保存 JSON (用于Web App)
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            # Pandas to_json 更适合扁平结构
            df.to_json(f, orient='records', indent=2)
        print(f"✅ JSON Saved: {OUTPUT_JSON}")
        
        # 保存日志
        log['explosion_ratio'] = log['output_rows'] / log['input_records'] if log['input_records'] > 0 else 0
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write("# Master Dataset Build Log (L3)\n\n")
            f.write(f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"- **Input L2 Records:** {log['input_records']}\n")
            f.write(f"- **Output Master Rows (Transitions):** {log['output_rows']}\n")
            f.write(f"- **Explosion Ratio:** {log['explosion_ratio']:.2f}x\n")
        print(f"📝 Log saved to {LOG_FILE}")
        
    except Exception as e:
        print(f"❌ Error during L3 cleaning: {e}")