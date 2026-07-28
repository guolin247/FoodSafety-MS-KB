import json
import requests
import time
import pandas as pd
import re

# ================= 配置区 =================
INPUT_FILE = r"D:\work_GuoLin\PDFreader\compounds.json"
OUTPUT_FILE = "orphan_candidates_api.csv"
MAX_RETRIES = 3 # 定义最大重试次数
RETRY_DELAY = 2 # 每次重试间隔秒数
# ========================================

def query_pubchem_with_retry(compound_name):
    """
    通过名称查询 PubChem，带有重试逻辑。
    """
    for attempt in range(MAX_RETRIES):
        try:
            # 替换空格，用于 URL
            name_encoded = compound_name.replace(" ", "%20")
            base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
            
            # 第一步：根据名称获取 CID
            url = f"{base_url}/compound/name/{name_encoded}/property/IUPACName/JSON"
            response = requests.get(url, timeout=15) # 增加超时时间
            
            # 检查 HTTP 状态码
            response.raise_for_status() # 如果是 4xx 或 5xx 错误，会抛出异常
            
            data = response.json()
            # 检查 PubChem 是否真的找到了东西
            if 'PropertyTable' not in data or not data['PropertyTable']['Properties']:
                return {"status": "Not Found"}

            # 通常第一个结果是最佳匹配
            cid = data['PropertyTable']['Properties'][0]['CID']
            iupac_name = data['PropertyTable']['Properties'][0]['IUPACName']
            
            # 第二步：根据 CID 获取 CAS
            cas_url = f"{base_url}/compound/cid/{cid}/synonyms/JSON"
            cas_response = requests.get(cas_url, timeout=15)
            cas_response.raise_for_status()
            
            synonyms_data = cas_response.json()
            if 'InformationList' not in synonyms_data or not synonyms_data['InformationList']['Information']:
                 return {"status": "CAS Not Found", "cid": cid, "iupac_name": iupac_name}

            synonyms = synonyms_data['InformationList']['Information'][0]['Synonym']
            # CAS 号通常是 xxx-xx-x 的格式
            cas_numbers = [s for s in synonyms if re.match(r'^\d{2,7}-\d{2}-\d$', s)]
            
            if cas_numbers:
                return {
                    "status": "Success",
                    "cid": cid,
                    "iupac_name": iupac_name,
                    "cas_number": cas_numbers[0]
                }
            else:
                # 找到了 CID 但没找到 CAS
                return {"status": "CAS Not Found", "cid": cid, "iupac_name": iupac_name}

        except requests.exceptions.RequestException as e:
            print(f"      Attempt {attempt + 1}/{MAX_RETRIES} failed for '{compound_name}': {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY) # 等待一段时间再重试
            else:
                return {"status": "Error", "details": str(e)}

def augment_with_api():
    print("🚀 Starting API Augmentation with Retry Logic...")
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        compounds = json.load(f)
        
    orphans = [c for c in compounds if c.get('status') == 'Orphan']
    print(f"   Found {len(orphans)} orphan compounds to process.")
    
    results = []
    
    for i, orphan in enumerate(orphans):
        name = orphan['preferred_name']
        print(f"   ({i+1}/{len(orphans)}) Querying for '{name}'...")
        
        result = query_pubchem_with_retry(name)
        
        row = {
            "original_name": name,
            "source": "PubChem_API" # 标签
        }
        
        if result['status'] == 'Success':
            row.update({
                "suggested_cas": result['cas_number'],
                "suggested_name": result['iupac_name'],
                "pubchem_cid": result['cid'],
                "confidence": "High",
                "notes": "Direct match from PubChem API."
            })
        else:
            # 记录失败或未找到的原因
            row.update({
                "suggested_cas": None,
                "suggested_name": None,
                "pubchem_cid": result.get('cid'), # 可能有CID但没CAS
                "confidence": "None",
                "notes": result.get('status') + (f": {result.get('details')}" if result.get('details') else "")
            })
        
        results.append(row)
        time.sleep(0.3) # 遵守 PubChem 的 API 速率限制 (每秒不超过5次)

    # 保存为 CSV
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    print(f"\n✅ API augmentation complete. Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    augment_with_api()