# Validation and Quality Assurance Scripts

This directory contains the suite of validation tools developed to ensure the integrity, consistency, and accuracy of the **FoodSafety-MS-KB** knowledge base. The validation framework employs a dual-strategy approach: **Automated Schema Compliance Testing** and **Statistical Sampling for Manual Audit**.

## 📂 Repository Structure

*   `detections/` & `methods/`: Directories containing sample data or validation targets (configurable in scripts).
*   `schema.json`: The master JSON Schema definition serving as the single source of truth for data structure and data type validation.
*   `*-schema_test.py`: Scripts for automated structural validation against `schema.json`.
*   `*-validation.py`: Scripts for generating stratified variation lists for human-in-the-loop auditing.

---

## 🛠️ 1. Automated Schema Validation

These scripts utilize the `jsonschema` library to rigorously test every data record against the rules defined in `schema.json`. This ensures that all data integrated into the knowledge base adheres to the strict structural and typing requirements of the project.

### Detections Schema Validation
*   **Script**: `detections-schema_test.py`
*   **Target**: Mass spectrometry detection records (Compounds, Ion pairs).
*   **Function**:
    *   Verifies data against the `detections` definition in `schema.json`.
    *   Enforces logic rules (e.g., Logic: *At least one of `CAS_number` or `compound_english_name` must be present*).
    *   Checks for missing mandatory keys and invalid data types.
    *   **Output**: `Table_S3_Detections_Diagnostic_Log.xlsx` (Diagnostic report).

### Methods Schema Validation
*   **Script**: `methods-schema_test.py`
*   **Target**: Methodological metadata (Sample prep, Chromatography conditions).
*   **Function**:
    *   Verifies data against the `methods` definition in `schema.json`.
    *   Checks the completeness of hierarchical structures (e.g., `chromatography_conditions`, `mass_spectrometry_conditions`).
    *   **Output**: `Table_S2_Methods_Structural_Audit.xlsx` (Diagnostic report).

---

## 🔎 2. Manual Audit Sampling

To validate the semantic accuracy of the extracted data against the original source documents (PDFs), these scripts generate randomized, stratified samples for manual verification.

### Detections Audit Sampling
*   **Script**: `detections-validation.py`
*   **Methodology**:
    *   **Flattening**: Explodes nested complex objects (multiple ion pairs per compound) into atomic transition records.
    *   **Stratification**: Performs random sampling (stratified by Method ID where applicable) to select a statistically significant subset (e.g., N=350).
*   **Output**: `Detections_Audit_Sampling_350.xlsx`
    *   Generates a checklist with "Check" columns for auditors to verify Precursor m/z, Product m/z, Collision Energy, and Metadata against the original papers.

### Methods Audit Checklist
*   **Script**: `methods-validation.py`
*   **Methodology**:
    *   Iterates through all extracted methods and analytical run configurations.
    *   Extracts key semantic fields (Matrix, Mobile Phase, Prep Workflow) for verification.
*   **Output**: `Methods_Audit_Checklist.xlsx`
    *   Produces a comprehensive checklist for auditors to validate that the semantic text extraction (performed in the `extraction_processing` pipeline) accurately reflects the experimental procedures described in the standards.

---

## 📜 3. Schema Definition

*   **File**: `schema.json`
*   **Description**: This JSON file formally defines the ontology of the Food Safety MS Knowledge Base. It includes:
    *   **Controlled Vocabularies**: Specifications for allowed values (e.g., `polarity`: "Positive"/"Negative").
    *   **Data Types**: String, Number, Array, Boolean constraints.
    *   **Field Descriptions**: Detailed metadata descriptions for every field (e.g., defining `method_id`, `precursor_mz`, `column_type`), serving as both validation rule and data dictionary.

---

## ⚠️ Usage Instructions

1.  **Dependencies**: Ensure `pandas`, `jsonschema`, and `xlsxwriter` are installed.
2.  **Configuration**: Before running any script, check the `CONFIGURATION` section at the top of the file to verify that `DATA_FOLDER` or `INPUT_FILE` points to the correct location of your dataset.
3.  **Logs**: Inspect the generated Excel logs (`*.xlsx`) to identify and fix data inconsistencies.
