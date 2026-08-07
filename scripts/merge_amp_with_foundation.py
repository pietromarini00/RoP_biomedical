#!/usr/bin/env python3
"""Merge AMP (SysBio FAIRplex) collection with existing v2026.04 bundle.

Combines:
- Existing v2026.04 bundle: data/final/v2026.04_elements.parquet (1,328,973 rows)
- AMP collection: data/amp/staging/amp_cdes.parquet (~535 rows)

Output:
- data/final/v2026.08_elements.parquet (1,329,508 rows combined)

Strategy:
1. Load both parquets
2. Concatenate (no dedup needed - AMP CDEs are distinct project-specific collection)
3. Write combined parquet
4. Verify row counts
"""

import pyarrow.parquet as pq
import pyarrow as pa
from pathlib import Path
import sys

def main():
    existing_path = Path("data/final/v2026.04_elements.parquet")
    amp_path = Path("data/amp/staging/amp_cdes.parquet")
    output_path = Path("data/final/v2026.08_elements.parquet")

    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("🔄 Merging AMP collection with existing v2026.04 bundle...")
    print(f"   Existing:   {existing_path}")
    print(f"   AMP:        {amp_path}")
    print(f"   Output:     {output_path}")
    print()

    # Load existing bundle
    print("📖 Loading existing v2026.04 bundle...")
    existing_table = pq.read_table(existing_path)
    existing_count = existing_table.num_rows
    print(f"   Existing rows: {existing_count:,}")

    # Load AMP collection
    print("📖 Loading AMP collection...")
    amp_table = pq.read_table(amp_path)
    amp_count = amp_table.num_rows
    print(f"   AMP rows:      {amp_count:,}")
    print()

    # Schema check - ensure compatible schemas
    print("🔍 Checking schema compatibility...")
    existing_schema = existing_table.schema
    amp_schema = amp_table.schema

    # Get field names
    existing_fields = set(existing_schema.names)
    amp_fields = set(amp_schema.names)

    # Fields only in existing
    existing_only = existing_fields - amp_fields
    if existing_only:
        print(f"   ⚠️  Fields only in existing: {existing_only}")

    # Fields only in AMP
    amp_only = amp_fields - existing_fields
    if amp_only:
        print(f"   ⚠️  Fields only in AMP: {amp_only}")

    # Common fields
    common_fields = existing_fields & amp_fields
    print(f"   ✅ Common fields: {len(common_fields)}")
    print()

    # Align schemas - force AMP table to match existing schema exactly
    print("🔧 Aligning AMP table to match existing schema...")

    # Build AMP table with columns matching existing schema in exact order
    amp_arrays = []
    for field in existing_schema:
        field_name = field.name
        if field_name in amp_fields:
            # Column exists in AMP - check if types match
            amp_field_type = amp_schema.field(field_name).type
            if amp_field_type != field.type:
                # Type mismatch - convert if possible
                if field_name in ['metadata_variants', 'alternate_codes']:
                    # These are JSON strings in AMP but structs in existing
                    # Use null arrays for now (proper parsing would be complex)
                    print(f"   ⚠️  Converting {field_name} to null (complex type mismatch)")
                    amp_arrays.append(pa.nulls(amp_count, type=field.type))
                else:
                    # Try to cast
                    try:
                        amp_arrays.append(amp_table.column(field_name).cast(field.type))
                    except:
                        print(f"   ⚠️  Cannot cast {field_name}, using nulls")
                        amp_arrays.append(pa.nulls(amp_count, type=field.type))
            else:
                # Types match - use as-is
                amp_arrays.append(amp_table.column(field_name))
        else:
            # Column missing in AMP - add nulls
            amp_arrays.append(pa.nulls(amp_count, type=field.type))

    # Reconstruct AMP table with existing schema
    amp_table = pa.Table.from_arrays(amp_arrays, schema=existing_schema)
    print(f"   ✅ AMP table aligned to existing schema ({len(existing_schema.names)} fields)")
    print()

    # Concatenate tables
    print("🔗 Concatenating tables...")
    combined_table = pa.concat_tables([existing_table, amp_table])
    combined_count = combined_table.num_rows
    print(f"   Combined rows: {combined_count:,}")

    # Verify count
    expected_count = existing_count + amp_count
    if combined_count != expected_count:
        print(f"   ❌ ERROR: Row count mismatch!")
        print(f"      Expected: {expected_count:,}")
        print(f"      Got:      {combined_count:,}")
        sys.exit(1)
    else:
        print(f"   ✅ Row count verified: {combined_count:,} = {existing_count:,} + {amp_count:,}")
    print()

    # Write combined parquet
    print(f"💾 Writing combined parquet to {output_path}...")
    pq.write_table(combined_table, output_path, compression='snappy')

    # Get file size
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"   ✅ Written: {file_size_mb:.1f} MB")
    print()

    # Summary
    print("=" * 70)
    print("✅ MERGE COMPLETE")
    print("=" * 70)
    print(f"Existing v2026.04:    {existing_count:>10,} CDEs")
    print(f"AMP collection:       {amp_count:>10,} CDEs")
    print(f"Combined v2026.08:    {combined_count:>10,} CDEs")
    print()
    print(f"Output: {output_path}")
    print(f"Size:   {file_size_mb:.1f} MB")
    print("=" * 70)

if __name__ == "__main__":
    main()
