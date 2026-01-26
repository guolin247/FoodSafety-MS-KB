import json
import re
import datetime
from collections import Counter
import statistics

# ================= 配置区 =================
INPUT_FILE = r"D:\work_GuoLin\PDFreader\FoodSafety_Methods_Raw_v1.json"
OUTPUT_FILE = "FoodSafety_Methods_App_v2.json"
LOG_FILE = "Methods_L2_Semantic_log.md"
# ========================================

class MethodL2SemanticCleaner:
    def __init__(self):
        self.stats = {
            "total_runs": 0,
            "matrix_tags_found": Counter(),
            "prep_techniques_found": Counter(),
            "solvents_found": Counter(),
            "instruments_found": Counter(),
            # [NEW] 变更追踪指标
            "runs_with_matrix": 0,
            "runs_with_prep_flow": 0,
            "runs_with_mobile_phase": 0,
            "mobile_phase_len_orig": [],
            "mobile_phase_len_clean": []
        }

    # ... (extract_matrix_tags, simplify_mobile_phase, extract_prep_workflow, extract_instrument 函数保持不变 ...)
    # 只要把你之前的逻辑复制过来即可，或者我这里简化省略，重点看 process 和 save_log

    def extract_matrix_tags(self, sample_info):
        """模块 1: 提取基质标签"""
        tags = set()
        text = " ".join([str(v) for v in sample_info.values() if v]).lower()
        keywords = {
            'milk': 'Milk', 'dairy': 'Dairy', 'yogurt': 'Dairy', 'cheese': 'Dairy',
            'egg': 'Egg', 'poultry': 'Poultry', 'chicken': 'Poultry',
            'meat': 'Meat', 'muscle': 'Muscle', 'beef': 'Meat', 'pork': 'Meat', 'bovine': 'Meat', 'porcine': 'Meat',
            'liver': 'Liver', 'kidney': 'Kidney', 'fat': 'Fat',
            'fish': 'Fish', 'seafood': 'Seafood', 'catfish': 'Fish', 'siluriformes': 'Fish',
            'cereal': 'Cereal', 'grain': 'Cereal', 'rice': 'Cereal', 'wheat': 'Cereal', 'corn': 'Cereal', 'maize': 'Cereal',
            'fruit': 'Fruit', 'vegetable': 'Vegetable', 'orange': 'Fruit', 'apple': 'Fruit', 'cabbage': 'Vegetable',
            'feed': 'Feed', 'silage': 'Feed',
            'honey': 'Honey', 'tea': 'Tea'
        }
        for k, v in keywords.items():
            if k in text:
                tags.add(v)
                self.stats["matrix_tags_found"][v] += 1
        return sorted(list(tags))

    def simplify_mobile_phase(self, mp_text):
        """模块 2: 简化流动相"""
        if not mp_text: return None
        # [NEW] 记录原始长度
        self.stats["mobile_phase_len_orig"].append(len(mp_text))
        
        text = mp_text.lower()
        replacements = {
            'acetonitrile': 'ACN', 'methanol': 'MeOH', 'water': 'H2O',
            'formic acid': 'FA', 'acetic acid': 'HAc', 
            'ammonium acetate': 'NH4Ac', 'ammonium formate': 'NH4Fm',
            'mobile phase': '', 'eluent': '',
            'containing': 'w/', 'solution': ''
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = text.replace('a:', 'A:').replace('b:', 'B:').strip()
        text = re.sub(r'\s+', ' ', text)
        
        # [NEW] 记录清洗后长度
        self.stats["mobile_phase_len_clean"].append(len(text))
        return text

    def extract_prep_workflow(self, prep_info):
        """模块 3: 提取前处理流程步骤"""
        steps = []
        sol = str(prep_info.get('extraction_solvent', '')).lower()
        if 'acetonitrile' in sol or 'acn' in sol: steps.append("Ext: ACN"); self.stats["solvents_found"]["ACN"] += 1
        elif 'ethyl acetate' in sol: steps.append("Ext: EtOAc"); self.stats["solvents_found"]["EtOAc"] += 1
        elif 'methanol' in sol: steps.append("Ext: MeOH"); self.stats["solvents_found"]["MeOH"] += 1
        elif 'hexane' in sol: steps.append("Ext: Hexane"); self.stats["solvents_found"]["Hexane"] += 1
        else: steps.append("Extraction")
        
        clean_text = (str(prep_info.get('cleanup_method', '')) + str(prep_info.get('spe_details', '')) + str(prep_info.get('enrichment_method', ''))).lower()
        if 'quechers' in clean_text: steps.append("QuEChERS"); self.stats["prep_techniques_found"]["QuEChERS"] += 1
        if 'spe' in clean_text and 'quechers' not in clean_text: steps.append("SPE"); self.stats["prep_techniques_found"]["SPE"] += 1
        if 'iac' in clean_text or 'immunoaffinity' in clean_text: steps.append("IAC"); self.stats["prep_techniques_found"]["IAC"] += 1
        if 'gpc' in clean_text: steps.append("GPC"); self.stats["prep_techniques_found"]["GPC"] += 1
        
        conc = str(prep_info.get('concentration_process', '')).lower()
        if 'nitrogen' in conc or 'blow' in conc or 'evaporate' in conc: steps.append("Concentrate")
        return steps

    def extract_instrument(self, ms_info):
        """模块 4: 提取仪器标签"""
        manu = ms_info.get('ms_instrument_manufacturer', '')
        model = ms_info.get('ms_instrument_model', '')
        if manu:
            if 'sciex' in manu.lower(): manu = 'SCIEX'
            elif 'waters' in manu.lower(): manu = 'Waters'
            elif 'agilent' in manu.lower(): manu = 'Agilent'
            elif 'thermo' in manu.lower(): manu = 'Thermo'
        tag = f"{manu} {model}".strip()
        if tag and len(tag) > 1: self.stats["instruments_found"][manu] += 1
        return tag if len(tag) > 1 else "Unknown MS"

    def process(self):
        print(f"🧠 Starting L2 Semantic Extraction...")
        try:
            with open(INPUT_FILE, 'r', encoding='utf-8') as f:
                methods = json.load(f)
            
            cleaned_methods = []
            for m in methods:
                m_new = m.copy()
                runs = m.get('analytical_runs', [])
                new_runs = []
                for r in runs:
                    r_new = r.copy()
                    
                    # 1. 基质
                    tags = self.extract_matrix_tags(r.get('sample_information', {}))
                    r_new['aug_matrix_tags'] = tags
                    if tags: self.stats["runs_with_matrix"] += 1
                    
                    # 2. 流动相
                    mp = self.simplify_mobile_phase(r.get('chromatography_conditions', {}).get('mobile_phase_composition'))
                    r_new['aug_mobile_phase_short'] = mp
                    if mp: self.stats["runs_with_mobile_phase"] += 1
                    
                    # 3. 前处理
                    steps = self.extract_prep_workflow(r.get('sample_preparation', {}))
                    r_new['aug_prep_steps'] = steps
                    if len(steps) > 1: self.stats["runs_with_prep_flow"] += 1
                    
                    # 4. 仪器
                    r_new['aug_instrument_tag'] = self.extract_instrument(r.get('mass_spectrometry_conditions', {}))
                    
                    new_runs.append(r_new)
                    self.stats["total_runs"] += 1
                
                m_new['analytical_runs'] = new_runs
                cleaned_methods.append(m_new)
                
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(cleaned_methods, f, ensure_ascii=False, indent=2)
            print(f"✅ Saved L2 Semantic Data to {OUTPUT_FILE}")
            
            self.save_log()
            
        except Exception as e:
            print(f"❌ Error: {e}")

    def save_log(self):
        # 计算统计量
        total = self.stats['total_runs']
        matrix_cov = (self.stats['runs_with_matrix'] / total) * 100 if total else 0
        prep_cov = (self.stats['runs_with_prep_flow'] / total) * 100 if total else 0
        
        avg_len_orig = statistics.mean(self.stats['mobile_phase_len_orig']) if self.stats['mobile_phase_len_orig'] else 0
        avg_len_clean = statistics.mean(self.stats['mobile_phase_len_clean']) if self.stats['mobile_phase_len_clean'] else 0
        reduction = ((avg_len_orig - avg_len_clean) / avg_len_orig) * 100 if avg_len_orig else 0

        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"# Methods Semantic Extraction Log (L2)\n")
            f.write(f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("### 1. Data Enrichment Impact (Augmentation)\n")
            f.write(f"- **Matrix Tagging Coverage:** {matrix_cov:.1f}% ({self.stats['runs_with_matrix']}/{total})\n")
            f.write(f"  > *Successfully extracted structured matrix tags (e.g., Milk, Cereal) from unstructured text.*\n")
            f.write(f"- **Prep Workflow Extraction:** {prep_cov:.1f}% ({self.stats['runs_with_prep_flow']}/{total})\n")
            f.write(f"  > *Successfully identified multi-step workflows (e.g., Ext->Clean->Conc).*\n")
            
            f.write("\n### 2. Text Simplification Impact\n")
            f.write(f"- **Mobile Phase String Reduction:** {reduction:.1f}%\n")
            f.write(f"  > *Average Length: {avg_len_orig:.0f} chars -> {avg_len_clean:.0f} chars. Improved readability for UI.*\n")
            
            f.write("\n### 3. Knowledge Graph Statistics\n")
            f.write("#### Top Matrix Tags\n")
            for k, v in self.stats["matrix_tags_found"].most_common(5):
                f.write(f"- {k}: {v}\n")
            
            f.write("\n#### Prep Techniques\n")
            for k, v in self.stats["prep_techniques_found"].most_common():
                f.write(f"- {k}: {v}\n")

        print(f"📝 Log saved to {LOG_FILE}")

if __name__ == "__main__":
    cleaner = MethodL2SemanticCleaner()
    cleaner.process()