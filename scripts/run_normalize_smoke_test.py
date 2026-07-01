"""
Smoke test: run normalize() end-to-end on real Marker output.
Not a pytest file — a standalone script to prove the pipeline runs.
"""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from betydb_extraction.marker_adapter.raw_model import MarkerDocument
from betydb_extraction.normalizer.api import normalize
from betydb_extraction.normalizer.context import NormalizerProcessingContext

PAPERS = {
    "pecan": "data/marker_output/pecan/pecan.json",
    "nutrient_cycling": "data/marker_output/Nutrient-cycling/Nutrient-cycling.json",
    "culti_mixtures": "data/marker_output/culti-mixtures/culti-mixtures.json",
}

OUTPUT_DIR = Path("data/normalized_output")


def _dump_document(document, path: Path) -> None:
    """Write a materialized Document out as JSON for manual inspection.
    Tries Pydantic v2's model_dump_json first, falls back to v1's .json()."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(document, "model_dump_json"):
        path.write_text(document.model_dump_json(indent=2))
    else:
        path.write_text(document.json(indent=2))

def run_one(name: str, path: str) -> bool:
    print(f"\n{'='*70}\n{name}  ({path})\n{'='*70}")
    try:
        raw_json = json.loads(Path(path).read_text())
        marker_doc = MarkerDocument(root=raw_json, source_marker_json_path=path)

        ctx = NormalizerProcessingContext(
            marker_version="unknown",
            normalizer_version="0.1.0-smoketest",
            source_marker_artifact_ref=path,
            processed_at=datetime.now(timezone.utc),
        )

        document = normalize(
            marker_document=marker_doc,
            source_pdf_identifier=f"smoketest:{name}",
            processing_context=ctx,
        )

        print(f"OK — pages={len(document.pages)}")
        print(f"  metadata.title = {document.metadata.title!r}")
        print(f"  statistics = {document.statistics}")
        out_path = OUTPUT_DIR / f"{name}.json"
        _dump_document(document, out_path)
        print(f"  saved to {out_path}")
        return True

    except Exception:
        print(f"FAILED on {name}")
        traceback.print_exc()
        return False


def main() -> None:
    results = {name: run_one(name, path) for name, path in PAPERS.items()}
    print(f"\n{'='*70}\nSUMMARY\n{'='*70}")
    for name, ok in results.items():
        print(f"  {name}: {'PASS' if ok else 'FAIL'}")
    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()