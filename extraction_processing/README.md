# Data Extraction and Processing Pipeline Documentation

This repository contains the scripts and workflows used for data cleaning, standardization, and knowledge graph construction for the **FoodSafety-MS-KB** project. The processing workflow is divided into two primary pipelines:

1.  **Detections Pipeline**: Processes mass spectrometry detection data (Compounds, Detections, MS Parameters).
2.  **Methods Pipeline**: Processes analytical method descriptions (Sample Preparation, Chromatography Conditions, Instruments).

## 📂 Repository Structure

*   `raw_data/`: Directory for input JSON files extracted from scientific literature.
*   `data_prep.py`: Initial data preparation utility (supporting script).
*   `step*.py`: Sequential processing scripts corresponding to the data cleaning stages.
*   `orphan_candidates_*.csv`: Intermediate files for compound entity resolution (generated via API or LLM).

---

## 🚀 1. Detections Pipeline

This pipeline is designed to ingest raw extraction data, normalize compound entities, resolve CAS Registry Numbers, and generate a flattened, analysis-ready master dataset.

### Processing Workflow

#### **Phase 1: Initial Cleaning and Standardization**
*   **Script**: `step1_L1_clean.py`
*   **Input**: `raw_data/*.json`
*   **Output**: `FoodSafety_MS_Raw_v1.json`
*   **Description**: Performs structural normalization (unifying list/dictionary formats) and recursive string sanitization (removing non-standard whitespace/characters). It also filters out invalid records missing critical mass spectrometry parameters.

#### **Phase 2: Entity Resolution and Master List Generation**
*   **Script**: `step2_L2_master_clean.py`
*   **Input**: `FoodSafety_MS_Raw_v1.json`
*   **Output**: `FoodSafety_MS_L2_cleaned.json`, `compounds.json`
*   **Description**:
    *   Constructs a mapping between Compound Names and CAS numbers.
    *   Performs bidirectional imputation to fill missing metadata.
    *   Generates a unique `compounds.json` catalog, classifying compounds as **Verified** (validated CAS) or **Orphan** (missing CAS).

#### **Phase 3: External Knowledge Augmentation**
*   **Script**: `step4a_augment_api.py.py`
*   **Input**: `compounds.json`
*   **Output**: `orphan_candidates_api.csv`
*   **Description**: Queries the **PubChem PUG REST API** to retrieve metadata (CAS, IUPAC Name, CID) for "Orphan" compounds, enhancing data completeness.

#### **Phase 4: Data Fusion and Curation**
*   **Script**: `step5_curate_compounds.py`
*   **Input**: `compounds.json`, `orphan_candidates_api.csv`, `orphan_candidates_llm_wb.csv` (LLM-derived data)
*   **Output**: `compounds_v2.json`, `curation_review_conflicts.csv`
*   **Description**: Merges provenance data from original documents, API results, and Large Language Model (LLM) inference. It applies a waterfall decision logic to prioritize high-confidence sources (e.g., API > LLM) and flags conflicts for manual review.

#### **Phase 5: Knowledge Propagation (Back-filling)**
*   **Script**: `step6_backfill_detections.py`
*   **Input**: `compounds_v2.json`, `FoodSafety_MS_L2_cleaned.json`
*   **Output**: `FoodSafety_MS_L2_Final.json`
*   **Description**: Propagates the curated metadata (e.g., newly discovered CAS numbers) back into the detection-level dataset, ensuring all instances of a compound are enriched.

#### **Phase 6: Final Flattening and Export**
*   **Script**: `step3_L3_master_clean.py`
*   **Input**: `FoodSafety_MS_L2_Final.json` (Recommended)
*   **Output**: `FoodSafety_MS_Master.csv`, `FoodSafety_MS_Master.json`
*   **Description**:
    *   Explodes nested JSON structures (e.g., multiple ion pairs per compound) into flat tabular rows.
    *   Normalizes performance parameters (e.g., unifying 'RT', 'Retention Time' to 'RT_min'; 'Pos', 'ESI+' to 'Polarity').
    *   Produces the final dataset for statistical analysis and application deployment.

---

## 🧪 2. Methods Pipeline

This pipeline focuses on extracting structured semantic information from unstructured experimental method descriptions.

#### **Phase 1: Text Normalization**
*   **Script**: `step1_clean_methods_L1.py`
*   **Input**: `method.json`
*   **Output**: `FoodSafety_Methods_Raw_v1.json`
*   **Description**: Applies deep text cleaning, including Unicode normalization (NFKC), de-hyphenation of line-broken words, and removal of invisible control characters.

#### **Phase 2: Semantic Feature Extraction**
*   **Script**: `step2_clean_methods_L2.py`
*   **Input**: `FoodSafety_Methods_Raw_v1.json`
*   **Output**: `FoodSafety_Methods_App_v2.json`
*   **Description**: Uses rule-based NLP to extract structured tags from free text:
    *   **Matrix**: (e.g., Milk, Cereals, Tissue).
    *   **Mobile Phase**: Standardizes solvent names (e.g., 'Acetonitrile' → 'ACN').
    *   **Prep Workflow**: Identifies techniques like SPE, QuEChERS, or Liquid-Liquid Extraction.
    *   **Instrumentation**: Extracts MS manufacturer and model information.

---

## ⚠️ Configuration and Reproducibility

1.  **Path Configuration**: Ensure that file paths defined in the `Configuration Section` at the top of each script match your local environment.
2.  **Sequential Execution**: Scripts are numbered to indicate the intended execution order.
3.  **API Rate Limiting**: The augmentation script (`step4a`) includes built-in delays to comply with PubChem API usage policies.