# Food Safety MS Knowledge Base

一个面向食品安全官方检测标准的质谱方法知识库。当前界面使用 V3 data draft，将法规文档、方法配置、化合物检测记录与 CAS 化合物身份关联起来。

## 当前数据

数据快照生成于 2026-07-29，包含：

- 450 份官方标准或方法文档
- 1,129 个方法配置
- 17,770 条化合物检测记录
- 1,298 个唯一化合物
- 中国、日本、美国、欧盟/欧洲等主要来源区域

`data/` 中的四类主数据保持 V3 草稿原始结构：

```text
data/
├── documents.json
├── methods.json
├── detections.json
├── compounds.json
├── v3_data_draft_summary.json
├── data_report.json          # 与 v3 摘要相同的旧部署兼容别名
└── corrections.json
```

`data_report.json` 与 `v3_data_draft_summary.json` 内容完全一致，仅用于兼容仍缓存旧加载器的托管部署；当前代码以 v3 文件名为准。

这批数据来自 `v3_data_draft`。数据契约校验、主键校验和跨表关系校验均已通过，但科学单位归一化、语义值修正、记录去重与身份重新评估尚未完成。应用中的“数据质量”页会明确展示这些边界。

人工复核发现的元数据误抽取通过 `data/corrections.json` 以覆盖层形式记录，原始草稿 JSON 保持不变。当前运行不再使用的旧版脚本、旧数据和远程旧处理工具分别封存在 `archive/legacy-2025/` 与 `archive/legacy-remote-2026/`。

## 功能

- 数据总览：查看区域、平台、标准、方法和化合物覆盖情况
- 化合物检索：搜索中英文名、CAS、标准编号、方法、基质与仪器
- 化合物身份：展示结构图、SMILES/InChI、历史 CAS、完整同义名、实验性质与属性来源
- 检测详情：查看定量限、保留时间、离子通道、碰撞能和源电压
- 方法上下文：查看样品信息、样品前处理、色谱和质谱条件
- 标准浏览：按文档追踪方法配置和化合物覆盖
- 原文证据：按需展开结构化字段对应的来源文本
- 数据质量：查看 Schema 与关系校验，以及待清洗事项

## 本地运行

Windows PowerShell（项目已创建独立环境）：

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

在其他已正确配置 Python 的环境中：

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

应用首次启动时会加载约 95 MB 的 JSON 数据并建立内存索引，之后由 Streamlit 缓存复用。
