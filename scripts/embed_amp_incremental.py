#!/usr/bin/env python3
"""Generate embeddings for AMP CDEs and append to existing v2026.04 embeddings.

Strategy:
1. Load amp_cdes.parquet (535 rows)
2. Generate SapBERT embeddings for AMP CDEs only
3. Load existing v2026.04 embeddings.npy (1,328,973 rows)
4. Concatenate: v2026.04 + AMP
5. Save combined embeddings to data/final/v2026.08_embeddings.npy (1,329,508 rows)

This is much faster than re-embedding all 1.33M rows (would take 6+ hours).
AMP embedding should take ~3-5 minutes for 535 rows.
"""

import pyarrow.parquet as pq
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
from pathlib import Path
from tqdm import tqdm
import sys

def mean_pooling(model_output, attention_mask):
    """Mean pooling - take attention mask into account for correct averaging."""
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

def main():
    amp_path = Path("data/amp/staging/amp_cdes.parquet")
    existing_emb_path = Path("data/final/v2026.04_embeddings.npy")
    output_path = Path("data/final/v2026.08_embeddings.npy")

    model_name = "cambridgeltl/SapBERT-from-PubMedBERT-fulltext"
    batch_size = 512
    device = "cuda" if torch.cuda.is_available() else "cpu"

    print("=" * 70)
    print("INCREMENTAL AMP CDE EMBEDDING")
    print("=" * 70)
    print(f"Model:       {model_name}")
    print(f"Device:      {device}")
    print(f"Batch size:  {batch_size}")
    print()

    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load AMP CDEs
    print("📖 Loading AMP CDEs...")
    amp_table = pq.read_table(amp_path)
    amp_count = amp_table.num_rows
    print(f"   AMP CDEs: {amp_count:,}")

    # Extract text for embedding
    amp_df = amp_table.to_pandas()

    # Build embedding text same way as foundation (description as primary text)
    texts = []
    for _, row in amp_df.iterrows():
        text = row.get('description', '') or ''
        if not text and row.get('item'):
            text = row.get('item', '')
        texts.append(str(text))

    print(f"   Texts extracted: {len(texts):,}")
    print()

    # Load model
    print(f"🤖 Loading {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.to(device)
    model.eval()
    print(f"   ✅ Model loaded on {device}")
    print()

    # Generate embeddings
    print(f"🔢 Generating embeddings for {amp_count:,} AMP CDEs...")
    all_embeddings = []

    num_batches = (len(texts) + batch_size - 1) // batch_size

    with torch.no_grad():
        for i in tqdm(range(0, len(texts), batch_size), total=num_batches, desc="Embedding"):
            batch_texts = texts[i:i + batch_size]

            # Tokenize
            encoded = tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors='pt'
            )
            encoded = {k: v.to(device) for k, v in encoded.items()}

            # Forward pass
            outputs = model(**encoded)

            # Mean pooling
            embeddings = mean_pooling(outputs, encoded['attention_mask'])

            # L2 normalize
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

            # Move to CPU and store
            embeddings = embeddings.cpu().numpy()
            all_embeddings.append(embeddings)

    # Stack all embeddings
    amp_embeddings = np.vstack(all_embeddings)
    print(f"   ✅ AMP embeddings shape: {amp_embeddings.shape}")
    print()

    # Validate AMP embeddings
    print("🔍 Validating AMP embeddings...")
    norms = np.linalg.norm(amp_embeddings, axis=1)
    print(f"   L2 norms - min: {norms.min():.6f}, max: {norms.max():.6f}, mean: {norms.mean():.6f}")

    if not np.allclose(norms, 1.0, atol=1e-5):
        print(f"   ❌ ERROR: Embeddings not properly normalized!")
        sys.exit(1)
    else:
        print(f"   ✅ All embeddings properly L2-normalized")
    print()

    # Load existing v2026.04 embeddings
    print("📖 Loading v2026.04 embeddings...")
    existing_embeddings = np.load(existing_emb_path)
    existing_count = existing_embeddings.shape[0]
    print(f"   Existing embeddings: {existing_embeddings.shape} ({existing_count:,} × 768)")
    print()

    # Concatenate embeddings
    print("🔗 Concatenating v2026.04 + AMP embeddings...")
    combined_embeddings = np.vstack([existing_embeddings, amp_embeddings])
    combined_count = combined_embeddings.shape[0]
    print(f"   Combined shape: {combined_embeddings.shape} ({combined_count:,} × 768)")

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

    # Save combined embeddings
    print(f"💾 Saving combined embeddings to {output_path}...")
    np.save(output_path, combined_embeddings)

    # Get file size
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"   ✅ Saved: {file_size_mb:.1f} MB")
    print()

    # Summary
    print("=" * 70)
    print("✅ INCREMENTAL EMBEDDING COMPLETE")
    print("=" * 70)
    print(f"v2026.04 embeddings:   {existing_count:>10,} rows")
    print(f"AMP embeddings:        {amp_count:>10,} rows")
    print(f"Combined v2026.08:     {combined_count:>10,} rows")
    print()
    print(f"Output: {output_path}")
    print(f"Size:   {file_size_mb:.1f} MB")
    print(f"Shape:  {combined_embeddings.shape} (float32, L2-normalized)")
    print("=" * 70)

if __name__ == "__main__":
    main()
