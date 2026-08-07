#!/usr/bin/env python3
"""Ingest AMP (SysBio FAIRplex) CDE collection from RoP-compatible CSV.

The AMP collection arrives pre-formatted with RoP schema columns including:
- source_authority, source_code, item, description, item_type
- canonical_concept_id, curation_status, member_of_collections
- metadata_variants (OMOP mappings), metadata_ (rich JSON metadata)

This script:
1. Reads the RoP-compatible CSV
2. Maps "AMP" source_authority to "AMP (SysBio FAIRplex)"
3. Validates against RoPElement schema
4. Outputs parquet file for merging

Usage:
    python scripts/ingest_amp_collection.py \\
        --input sysbio-collection-August_7th_2026/amp_rop_elements.csv \\
        --output data/amp/staging/amp_cdes.parquet
"""
import argparse
import csv
import json
import logging
from pathlib import Path
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("amp_ingest")


def parse_amp_csv(filepath: Path) -> list[dict]:
    """Parse AMP RoP-compatible CSV into element records."""
    logger.info("Parsing %s", filepath.name)

    rows = []
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        # Increase field size limit for large metadata fields
        csv.field_size_limit(10 * 1024 * 1024)
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            # Extract core fields
            source_authority = row.get("source_authority", "").strip()
            source_code = row.get("source_code", "").strip()
            item = row.get("item", "").strip()
            description = row.get("description", "").strip()
            item_type = row.get("item_type", "").strip() or None

            # Skip empty rows
            if not source_code or not item:
                continue

            # Map "AMP" to "AMP (SysBio FAIRplex)"
            if source_authority == "AMP":
                source_authority = "AMP (SysBio FAIRplex)"

            # Build RoPElement-compatible record
            element = {
                "rop_id": str(uuid4()),
                "item": item[:255],  # Truncate to schema max
                "description": description[:8000] if description else item,
                "source_authority": source_authority,
                "source_code": source_code,
                "source_version": row.get("source_version", "AMP-2026.08").strip(),
                "source_url": row.get("source_url", "").strip() or None,
                "source_retrieved_date": row.get("source_retrieved_date", "2026-08-07").strip(),
                "item_type": item_type,
                "unit_of_measure": row.get("unit_of_measure", "").strip() or None,
                "unit_vocabulary": row.get("unit_vocabulary", "").strip() or None,
                "plausible_min": row.get("plausible_min", "").strip() or None,
                "plausible_max": row.get("plausible_max", "").strip() or None,
                "cardinality": row.get("cardinality", "").strip() or None,
                "values": row.get("values", "").strip() or None,
                "canonical_concept_id": row.get("canonical_concept_id", "").strip() or None,
                "curation_status": row.get("curation_status", "under-review").strip(),
                "alternate_names": row.get("alternate_names", "").strip() or None,
                "member_of_collections": _parse_json_list(row.get("member_of_collections", "[]")),
                "metadata_variants": _parse_json_dict(row.get("metadata_variants", "{}")),
                "metadata_": _parse_json_dict(row.get("metadata_", "{}")),
                "source_row_count": row.get("source_row_count", "1").strip() or "1",
                "alternate_codes": _parse_json_list(row.get("alternate_codes", "[]")),
            }

            # Convert numeric strings to appropriate types
            if element["plausible_min"]:
                try:
                    element["plausible_min"] = float(element["plausible_min"])
                except ValueError:
                    element["plausible_min"] = None

            if element["plausible_max"]:
                try:
                    element["plausible_max"] = float(element["plausible_max"])
                except ValueError:
                    element["plausible_max"] = None

            if element["canonical_concept_id"]:
                try:
                    element["canonical_concept_id"] = int(element["canonical_concept_id"])
                except ValueError:
                    element["canonical_concept_id"] = None

            try:
                element["source_row_count"] = int(element["source_row_count"])
            except ValueError:
                element["source_row_count"] = 1

            rows.append(element)

    logger.info("  Parsed %d CDEs from %s", len(rows), filepath.name)
    return rows


def _parse_json_list(value: str) -> list[str]:
    """Parse JSON list string, return empty list on error."""
    if not value or value.strip() in ("", "[]"):
        return []
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []


def _parse_json_dict(value: str) -> dict | None:
    """Parse JSON dict string, return None on error."""
    if not value or value.strip() in ("", "{}"):
        return None
    try:
        result = json.loads(value)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Input AMP CSV file")
    parser.add_argument("--output", required=True, help="Output parquet file")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Parse CSV
    elements = parse_amp_csv(input_path)
    logger.info("Total AMP CDEs parsed: %d", len(elements))

    # Convert to PyArrow table
    # Match schema used by boutique and foundation bundles
    schema = pa.schema([
        ("rop_id", pa.string()),
        ("item", pa.string()),
        ("description", pa.string()),
        ("source_authority", pa.string()),
        ("source_code", pa.string()),
        ("source_version", pa.string()),
        ("source_url", pa.string()),
        ("source_retrieved_date", pa.string()),
        ("item_type", pa.string()),
        ("unit_of_measure", pa.string()),
        ("unit_vocabulary", pa.string()),
        ("plausible_min", pa.float64()),
        ("plausible_max", pa.float64()),
        ("cardinality", pa.string()),
        ("values", pa.string()),
        ("canonical_concept_id", pa.int64()),
        ("curation_status", pa.string()),
        ("alternate_names", pa.string()),
        ("member_of_collections", pa.list_(pa.string())),
        ("metadata_variants", pa.string()),  # JSON string
        ("metadata_", pa.string()),  # JSON string
        ("source_row_count", pa.int64()),
        ("alternate_codes", pa.list_(pa.string())),
    ])

    # Prepare table data
    table_data = {
        "rop_id": [e["rop_id"] for e in elements],
        "item": [e["item"] for e in elements],
        "description": [e["description"] for e in elements],
        "source_authority": [e["source_authority"] for e in elements],
        "source_code": [e["source_code"] for e in elements],
        "source_version": [e["source_version"] for e in elements],
        "source_url": [e["source_url"] for e in elements],
        "source_retrieved_date": [e["source_retrieved_date"] for e in elements],
        "item_type": [e["item_type"] for e in elements],
        "unit_of_measure": [e["unit_of_measure"] for e in elements],
        "unit_vocabulary": [e["unit_vocabulary"] for e in elements],
        "plausible_min": [e["plausible_min"] for e in elements],
        "plausible_max": [e["plausible_max"] for e in elements],
        "cardinality": [e["cardinality"] for e in elements],
        "values": [e["values"] for e in elements],
        "canonical_concept_id": [e["canonical_concept_id"] for e in elements],
        "curation_status": [e["curation_status"] for e in elements],
        "alternate_names": [e["alternate_names"] for e in elements],
        "member_of_collections": [e["member_of_collections"] for e in elements],
        "metadata_variants": [json.dumps(e["metadata_variants"]) if e["metadata_variants"] else None for e in elements],
        "metadata_": [json.dumps(e["metadata_"]) if e["metadata_"] else None for e in elements],
        "source_row_count": [e["source_row_count"] for e in elements],
        "alternate_codes": [e["alternate_codes"] for e in elements],
    }

    table = pa.table(table_data, schema=schema)

    # Write parquet
    logger.info("Writing %d rows to %s", len(elements), output_path)
    pq.write_table(table, output_path, compression='snappy')

    # Summary
    collections = set()
    for e in elements:
        collections.update(e["member_of_collections"])

    logger.info("✅ AMP CDEs ingested successfully")
    logger.info("   Total CDEs: %d", len(elements))
    logger.info("   Collections: %s", ", ".join(sorted(collections)))
    logger.info("   Output: %s", output_path)


if __name__ == "__main__":
    main()
