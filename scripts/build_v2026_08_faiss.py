#!/usr/bin/env python3
"""Build FAISS index for v2026.08 embeddings (1,329,508 vectors).

This script rebuilds the FAISS IVF4096 index for the combined v2026.04 + AMP embeddings.

Usage:
    python scripts/build_v2026_08_faiss.py
"""
import logging
import time
from pathlib import Path

import faiss
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("faiss_v2026.08")


def main():
    embeddings_path = Path("data/final/v2026.08_embeddings.npy")
    output_path = Path("data/final/v2026.08_embeddings.faiss")

    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("FAISS INDEX BUILD - v2026.08")
    print("=" * 70)
    print(f"Input:  {embeddings_path}")
    print(f"Output: {output_path}")
    print()

    # Load embeddings
    logger.info("📖 Loading embeddings from %s", embeddings_path)
    embeddings = np.load(embeddings_path)
    logger.info("   Loaded: shape=%s dtype=%s", embeddings.shape, embeddings.dtype)

    n, d = embeddings.shape
    print()
    print(f"Building FAISS IVF4096 index for {n:,} vectors (dim={d})...")
    print()

    # Build index
    t0 = time.time()

    # Use IndexIVFFlat for large datasets (1M+ vectors)
    # IVF4096 = 4096 Voronoi cells (good for 1-10M vectors)
    logger.info("🔨 Creating IVF4096 index with INNER_PRODUCT metric")
    quantizer = faiss.IndexFlatIP(d)  # Inner product (cosine for normalized vectors)
    index = faiss.IndexIVFFlat(quantizer, d, 4096, faiss.METRIC_INNER_PRODUCT)

    logger.info("🎓 Training index on %d vectors...", n)
    index.train(embeddings)

    logger.info("➕ Adding vectors to index...")
    index.add(embeddings)

    elapsed = time.time() - t0
    logger.info("   ✅ Built index in %.1fs (%.2f min)", elapsed, elapsed / 60)
    print()

    # Save index
    logger.info("💾 Saving index to %s", output_path)
    faiss.write_index(index, str(output_path))

    # Get file size
    index_size_mb = output_path.stat().st_size / 1024**2
    logger.info("   ✅ Saved: %.1f MB", index_size_mb)
    logger.info("   Index stats: ntotal=%d, nlist=%d", index.ntotal, index.nlist)
    print()

    # Sanity test
    logger.info("🔍 Running sanity test (k=10 neighbors for first vector)")
    index.nprobe = 10  # Search 10 cells (speed/accuracy tradeoff)
    D, I = index.search(embeddings[:1], 10)
    logger.info("   Top-5 neighbor distances: %s", D[0][:5])
    logger.info("   Top-5 neighbor indices:   %s", I[0][:5])

    if I[0][0] == 0 and D[0][0] > 0.99:
        logger.info("   ✅ Sanity test passed (self is top result)")
    else:
        logger.warning("   ⚠️  Sanity test unexpected: self not top result")
    print()

    # Summary
    print("=" * 70)
    print("✅ FAISS INDEX BUILD COMPLETE")
    print("=" * 70)
    print(f"Vectors indexed: {n:,}")
    print(f"Dimensions:      {d}")
    print(f"Index type:      IVF4096,Flat")
    print(f"Metric:          INNER_PRODUCT")
    print(f"Output file:     {output_path}")
    print(f"File size:       {index_size_mb:.1f} MB")
    print(f"Build time:      {elapsed:.1f}s ({elapsed / 60:.2f} min)")
    print("=" * 70)


if __name__ == "__main__":
    main()
