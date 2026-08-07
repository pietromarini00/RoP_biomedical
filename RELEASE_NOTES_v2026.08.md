# RoP v2026.08 Release Notes

**Release Date**: August 7, 2026
**Previous Version**: v2026.04

## 🎉 What's New

### Added: AMP (SysBio FAIRplex) Collection

This release adds **535 new Common Data Elements** from the **Accelerating Medicines Partnership (AMP) SysBio FAIRplex** collection, covering four major disease domains:

- **AMP-AD**: Alzheimer's Disease and related dementias
- **AMP-CMD**: Cardiovascular and Metabolic Disease
- **AMP-PD**: Parkinson's Disease
- **AMP-RA-SLE**: Rheumatoid Arthritis / Systemic Lupus Erythematosus

## 📊 Statistics

| Metric | v2026.04 | v2026.08 | Change |
|--------|----------|----------|--------|
| **Total CDEs** | 1,328,973 | 1,329,508 | +535 (+0.040%) |
| **Foundation CDEs** | 1,326,063 | 1,326,063 | 0 |
| **Boutique CDEs** | 2,910 | 2,910 | 0 |
| **AMP CDEs** | 0 | 535 | +535 (NEW) |
| **Boutique Collections** | 9 | 9 | 0 |
| **AMP Collections** | 0 | 4 | +4 (NEW) |
| **Bundle Size** | 7.77 GB | 7.78 GB | +3.3 MB (+0.04%) |
| **Embedding Vectors** | 1,328,973 × 768 | 1,329,508 × 768 | +535 |

## 🗂️ Collections

### Existing Collections (Preserved)
- ASAP, Answer-ALS, BDR, BDSA, CARD-PathND, GP2, NACC, PARTS, SEA-AD

### New AMP Collections
- **AMP-AD**: Alzheimer's Disease CDEs
- **AMP-CMD**: Cardiovascular/Metabolic Disease CDEs
- **AMP-PD**: Parkinson's Disease CDEs
- **AMP-RA-SLE**: RA/SLE CDEs

## 🔧 Technical Details

### Source Authority
- **Added**: `AMP (SysBio FAIRplex)` as new source authority
- All 535 AMP CDEs tagged with this authority

### Embeddings
- Generated SapBERT embeddings for all 535 new AMP CDEs
- Model: `cambridgeltl/SapBERT-from-PubMedBERT-fulltext`
- Embeddings properly L2-normalized
- Appended to existing v2026.04 embeddings (first 1,328,973 vectors preserved)

### FAISS Index
- Rebuilt IVF4096 index for 1,329,508 total vectors
- Index type: IVF4096,Flat
- Metric: INNER_PRODUCT
- Training time: ~23 minutes
- Total build time: ~26 minutes

### File Integrity
- All files checksummed with SHA256
- Checksums stored in `manifest.json`
- Files:
  - `elements.parquet`: 151.2 MB
  - `embeddings.npy`: 3.9 GB
  - `embeddings.faiss`: 3.9 GB

## ✅ Validation

All validation checks passed:
- ✅ Row count increased by exactly 535
- ✅ Embedding shape increased by exactly 535 vectors
- ✅ First 1,328,973 embeddings identical to v2026.04
- ✅ New source authority successfully added
- ✅ 4 new collections properly tagged
- ✅ FAISS index sanity test passed
- ✅ Bundle size increase minimal and expected

## 📝 Data Quality

### AMP CDE Characteristics
- Rich OMOP concept mappings (canonical_concept_id populated)
- Detailed metadata including original boutique fields
- Curation status: mixture of "reviewed" and "under-review"
- Item types: enum, numeric, string, date
- Collection membership properly tagged

### Sample AMP CDEs
- Demographics: age, sex, race, ethnicity
- Clinical: diagnosis types, disease outcomes, pathology scores
- Measurements: Braak staging, CERAD scores, Modified Schwab & England ADL
- Biomarkers: amyloid deposition, tau pathology

## 🔗 Sources

### Data Sources (Unchanged from v2026.04)
- OMOP/Athena
- HPO (Human Phenotype Ontology)
- Mondo Disease Ontology
- NINDS-CDE
- CDISC
- PhenX
- BIDS
- DICOM
- DUO (Data Use Ontology)
- Boutique Collections

### New Source
- **AMP (SysBio FAIRplex)**: Accelerating Medicines Partnership SysBio FAIRplex collection

## 📦 Files

### Bundle Contents
```
dist/rop_v2026.08/
├── elements.parquet         # 151.2 MB  - All 1,329,508 CDEs
├── embeddings.npy           # 3.9 GB    - SapBERT embeddings
├── embeddings.faiss         # 3.9 GB    - FAISS IVF4096 index
└── manifest.json            # Metadata and checksums
```

### Scripts Created
- `scripts/ingest_amp_collection.py` - Ingest AMP CDEs from CSV
- `scripts/merge_amp_with_foundation.py` - Merge AMP with v2026.04
- `scripts/embed_amp_incremental.py` - Generate AMP embeddings
- `scripts/build_v2026_08_faiss.py` - Build FAISS index
- `scripts/package_v2026_08_bundle.py` - Package final bundle

## 🚀 Migration from v2026.04

### Breaking Changes
None. v2026.08 is fully backward compatible with v2026.04.

### New Features
- 535 additional CDEs available for harmonization
- 4 new disease-specific collections
- Enhanced coverage of Alzheimer's, Parkinson's, CVD/metabolic, and autoimmune diseases

### Schema Changes
- Added `AMP_SYSBIO = "AMP (SysBio FAIRplex)"` to `SourceAuthority` enum in `rop/schema.py`

## 📚 Documentation

See README.md for:
- Updated statistics
- New AMP collection information
- Usage examples

## 🙏 Acknowledgments

- **AMP Program**: Accelerating Medicines Partnership
- **SysBio FAIRplex**: Systems Biology Fair Data Sharing
- **NIH**: National Institutes of Health
- **Foundation for NIH**: Data coordination

## 📧 Contact

For questions or issues:
- GitHub Issues: https://github.com/datatecnica/rop/issues
- Email: info@datatecnica.com

---

**License**: AGPL-3.0 (code) + CC-BY-NC-4.0 (data)
**DOI**: (to be assigned upon Hugging Face upload)
