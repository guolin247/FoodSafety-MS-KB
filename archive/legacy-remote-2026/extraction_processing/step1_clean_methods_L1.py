import json
import unicodedata
import datetime
import re

# ================= 配置区 =================
INPUT_FILE = r"D:\work_GuoLin\PDFreader\method.json"
OUTPUT_FILE = "FoodSafety_Methods_Raw_v1.json"
LOG_FILE = "Methods_L1_log.md"
# ========================================

class MethodL1DeepCleaner:
    def __init__(self):
        self.stats = {
            "total_methods": 0,
            "total_runs": 0,
            "unicode_fixes": 0,      # 全角转半角
            "hyphen_fixes": 0,       # 修复断行连字符 (Method- \n ology)
            "whitespace_fixes": 0,   # 多余空格、换行、制表符合并
            "invisible_char_fixes": 0 # 去除不可见字符 (如 \u200b)
        }

    def normalize_string(self, val):
        if not isinstance(val, str): return val
        
        original = val
        current = val

        # 1. 深度 Unicode 标准化 (NFKC)
        # 处理全角字符、兼容性字符
        current = unicodedata.normalize('NFKC', current)
        if current != original:
            self.stats["unicode_fixes"] += 1
            
        # 2. 修复断行连字符 (De-hyphenation)
        # 逻辑：匹配 "单词字符 + 连字符 + 换行/空格 + 单词字符"
        # 慎用：有些化学名确实有连字符 (LC-MS)，所以我们只处理连字符后紧跟换行的情况
        # 模式：单词- \n 单词 -> 单词单词
        step2 = re.sub(r'(\w)-\s*[\n\r]+\s*(\w)', r'\1\2', current)
        if step2 != current:
            self.stats["hyphen_fixes"] += 1
        current = step2

        # 3. 清理不可见字符和非标准空格
        # \u00a0: No-break space, \u200b: Zero-width space
        step3 = current.replace('\u00a0', ' ').replace('\u200b', '')
        if step3 != current:
            self.stats["invisible_char_fixes"] += 1
        current = step3

        # 4. 空白符坍缩 (Whitespace Collapse)
        # 将所有连续的空白符（\n, \t, \r, space）替换为单个空格，并去除首尾空格
        step4 = " ".join(current.split())
        if step4 != current:
            self.stats["whitespace_fixes"] += 1
        current = step4

        # 5. 空值标准化
        if current.lower() in ['none', 'null', '']:
            return None
            
        return current

    def clean_dict(self, d):
        """递归清洗字典"""
        if isinstance(d, dict):
            return {k: self.clean_dict(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [self.clean_dict(v) for v in d]
        elif isinstance(d, str):
            return self.normalize_string(d)
        else:
            return d

    def process(self):
        print(f"🧹 Starting Enhanced L1 Cleaning...")
        
        try:
            with open(INPUT_FILE, 'r', encoding='utf-8') as f:
                methods = json.load(f)
            
            self.stats["total_methods"] = len(methods)
            cleaned_methods = []
            
            for m in methods:
                # 递归清洗
                m_clean = self.clean_dict(m)
                
                # 统计 Run
                runs = m_clean.get('analytical_runs', [])
                if isinstance(runs, list):
                    self.stats["total_runs"] += len(runs)
                
                cleaned_methods.append(m_clean)
                
            # 保存
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(cleaned_methods, f, ensure_ascii=False, indent=2)
            print(f"✅ Saved Deep Cleaned data to {OUTPUT_FILE}")
            
            self.save_log()
            
        except Exception as e:
            print(f"❌ Error: {e}")

    def save_log(self):
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"# Methods Deep Cleaning Log (L1)\n")
            f.write(f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("### Data Overview\n")
            f.write(f"- **Total Methods:** {self.stats['total_methods']}\n")
            f.write(f"- **Total Analytical Runs:** {self.stats['total_runs']}\n\n")
            
            f.write("### Cleaning Operations Applied\n")
            f.write(f"- **Unicode Normalizations (NFKC):** {self.stats['unicode_fixes']}\n")
            f.write(f"  > *Fixes full-width chars (Ａ -> A) and compatibility chars.*\n")
            f.write(f"- **De-hyphenation Fixes:** {self.stats['hyphen_fixes']}\n")
            f.write(f"  > *Joins words split by line breaks (Meth- \\n od -> Method).*\n")
            f.write(f"- **Invisible Character Removal:** {self.stats['invisible_char_fixes']}\n")
            f.write(f"  > *Removes Zero-width spaces, Non-breaking spaces.*\n")
            f.write(f"- **Whitespace Collapsing:** {self.stats['whitespace_fixes']}\n")
            f.write(f"  > *Converts newlines/tabs to spaces, removes double spaces.*\n")
            
        print(f"📝 Log saved to {LOG_FILE}")

if __name__ == "__main__":
    cleaner = MethodL1DeepCleaner()
    cleaner.process()