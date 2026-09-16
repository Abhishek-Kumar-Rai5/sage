from __future__ import annotations
import copy
import json
import os

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")


PAPERS = {
    "pecan": {
        "id": "pecan",
        "title": "Canopy Architecture and Morphology of Switchgrass Populations "
                  "Differing in Forage Yield",
        "authors": "Daren D. Redfearn, Kenneth J. Moore, Kenneth P. Vogel, "
                    "Steven S. Waller, and Robert B. Mitchell",
        "year": 1997,
        "journal": "Agron. J. 89:262-269 (1997).",
        "pdf_path": os.path.join(ASSETS_DIR, "mock_paper.pdf"),
    }
}


DOCUMENT_BLOCKS = [
    {"anchor": "b:0006", "text": "Canopy Architecture and Morphology of Switchgrass "
                                  "Populations Differing in Forage Yield"},
    {"anchor": "b:0007", "text": "Daren D. Redfearn, Kenneth J. Moore, Kenneth P. Vogel,\n"
                                  "Steven S. Waller, and Robert B. Mitchell"},
    {"anchor": "b:0008", "text": "Department of Agronomy, University of Nebraska, "
                                  "Lincoln, NE 68583"},
    {"anchor": "b:0009", "text": "ABSTRACT\nCanopy architecture influences forage "
                                  "accumulation and light interception in switchgrass "
                                  "(Panicum virgatum L.). Two switchgrass populations "
                                  "selected for divergent forage yield were evaluated "
                                  "for canopy structure over two growing seasons."},
    {"anchor": "b:0010", "text": "Published in Agron. J. 89:262-269 (1997)."},
    {"anchor": "b:0011", "text": "MATERIALS AND METHODS\nField studies were conducted "
                                  "at the University of Nebraska Agricultural Research "
                                  "and Development Center near Mead, NE, on a "
                                  "Sharpsburg silty clay loam soil."},
    {"anchor": "b:0012", "text": "Two switchgrass populations, a high-yielding cycle-2 "
                                  "(HY C2) population and the unselected cultivar "
                                  "'Trailblazer', were established in 1993 in a "
                                  "randomized complete block design with four "
                                  "replications."},
    {"anchor": "b:0013", "text": "Plots were harvested at three stages of maturity: "
                                  "vegetative, elongation, and anthesis, in each of "
                                  "the two years of the study (1994 and 1995)."},
    {"anchor": "b:0014", "text": "Nitrogen fertilizer was applied each spring at a "
                                  "rate of 112 kg N ha-1 as ammonium nitrate."},
    {"anchor": "b:0015", "text": "RESULTS AND DISCUSSION\nLeaf area index (LAI) "
                                  "differed significantly (P < 0.05) between "
                                  "populations at the elongation stage, with HY C2 "
                                  "averaging 3.8 and Trailblazer averaging 3.1."},
    {"anchor": "b:0016", "text": "Canopy height at anthesis averaged 142 cm for HY C2 "
                                  "and 128 cm for Trailblazer across both years."},
    {"anchor": "b:0017", "text": "Light interception exceeded 90% for both populations "
                                  "once canopy height reached approximately 60 cm."},
]



def _load_provenance_geometry() -> dict[str, dict]:
    path = os.path.join(ASSETS_DIR, "mock_provenance.json")
    try:
        with open(path, "r") as f:
            entries = json.load(f)
        return {e["anchor"]: {"page": e["page"], "polygon": e["polygon"]} for e in entries}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


_PROVENANCE_GEOMETRY = _load_provenance_geometry()

for _block in DOCUMENT_BLOCKS:
    _geo = _PROVENANCE_GEOMETRY.get(_block["anchor"])
    if _geo:
        _block["page"] = _geo["page"]
        _block["polygon"] = _geo["polygon"]
    else:
        _block["page"] = None
        _block["polygon"] = None



def _field(value, status="EXTRACTED", anchors=None, reason=None, confidence=None):
    return {
        "value": value,
        "status": status,               # EXTRACTED | UNRESOLVED | EDITED
        "anchors": anchors or [],
        "reason": reason,
        "confidence": confidence,
    }


def _base_record(rec_id, entity_type, review_status, fields, evidence, confidence=None,
                  inference_source="LLM extraction (mock)"):
    return {
        "id": rec_id,
        "entity_type": entity_type,
        "review_status": review_status,
        "fields": fields,
        "evidence": evidence,
        "confidence": confidence,
        "inference_source": inference_source,
    }


RECORDS = {
    "citation": [
        _base_record(
            "citation-1", "Citation", "NEEDS REVIEW",
            fields={
                "title": _field(PAPERS["pecan"]["title"], anchors=["b:0006"]),
                "authors": _field(PAPERS["pecan"]["authors"], anchors=["b:0007"]),
                "year": _field(PAPERS["pecan"]["year"], anchors=["b:0010"]),
                "persistent_identifier": _field(
                    None, status="UNRESOLVED",
                    reason="No identifier found in the available document metadata.",
                ),
            },
            evidence=["b:0006", "b:0007", "b:0010"],
            confidence=0.93,
        ),
    ],
    "study": [
        _base_record(
            "study-1", "Study", "NEEDS REVIEW",
            fields={
                "study_name": _field("Switchgrass Canopy Architecture Field Study",
                                      anchors=["b:0011"]),
                "design": _field("Randomized complete block, 4 replications",
                                  anchors=["b:0012"]),
                "years": _field("1994-1995", anchors=["b:0013"]),
                "location": _field("Mead, NE (UNL ARDC)", anchors=["b:0011"]),
            },
            evidence=["b:0011", "b:0012", "b:0013"],
            confidence=0.88,
        ),
    ],
    "site": [
        _base_record(
            "site-1", "Site", "READY",
            fields={
                "site_name": _field("UNL Agricultural Research and Development Center",
                                     anchors=["b:0011"]),
                "soil_type": _field("Sharpsburg silty clay loam", anchors=["b:0011"]),
                "location": _field("Near Mead, NE", anchors=["b:0011"]),
                "study": _field("study-1", status="EXTRACTED"),
            },
            evidence=["b:0011"],
            confidence=0.95,
        ),
    ],
    "treatment": [
        _base_record(
            "treatment-1", "Treatment", "NEEDS REVIEW",
            fields={
                "factor": _field("Population", anchors=["b:0012"]),
                "level": _field("High-yielding cycle-2 (HY C2)", anchors=["b:0012"]),
                "control_status": _field("Comparison population", anchors=["b:0012"]),
                "study": _field("study-1"),
            },
            evidence=["b:0012"],
            confidence=0.9,
        ),
        _base_record(
            "treatment-2", "Treatment", "NEEDS REVIEW",
            fields={
                "factor": _field("Population", anchors=["b:0012"]),
                "level": _field("'Trailblazer' cultivar", anchors=["b:0012"]),
                "control_status": _field("Unselected control", anchors=["b:0012"]),
                "study": _field("study-1"),
            },
            evidence=["b:0012"],
            confidence=0.9,
        ),
        _base_record(
            "treatment-3", "Treatment", "UNRESOLVED",
            fields={
                "factor": _field("Maturity stage", anchors=["b:0013"]),
                "level": _field(None, status="UNRESOLVED",
                                 reason="Multiple maturity-stage levels listed; unclear "
                                        "which is the primary treatment factor vs. a "
                                        "repeated-measures covariate."),
                "control_status": _field(None, status="UNRESOLVED"),
                "study": _field("study-1"),
            },
            evidence=["b:0013"],
            confidence=0.52,
        ),
        _base_record(
            "treatment-4", "Treatment", "READY",
            fields={
                "factor": _field("Nitrogen fertilization", anchors=["b:0014"]),
                "level": _field("112 kg N ha-1, ammonium nitrate", anchors=["b:0014"]),
                "control_status": _field("Applied uniformly, not a factorial treatment",
                                          anchors=["b:0014"]),
                "study": _field("study-1"),
            },
            evidence=["b:0014"],
            confidence=0.91,
        ),
        _base_record(
            "treatment-5", "Treatment", "ACCEPTED",
            fields={
                "factor": _field("Harvest stage", anchors=["b:0013"]),
                "level": _field("Vegetative", anchors=["b:0013"]),
                "control_status": _field("Earliest harvest stage", anchors=["b:0013"]),
                "study": _field("study-1"),
            },
            evidence=["b:0013"],
            confidence=0.87,
        ),
    ],
    "observation": [
        _base_record(
            "observation-1", "Observation", "READY",
            fields={
                "variable": _field("Leaf Area Index (LAI)", anchors=["b:0015"]),
                "value": _field("3.8", anchors=["b:0015"]),
                "unit": _field("m2 m-2", anchors=["b:0015"]),
                "treatment": _field("treatment-1"),
                "site": _field("site-1"),
                "study": _field("study-1"),
            },
            evidence=["b:0015"],
            confidence=0.9,
        ),
        _base_record(
            "observation-2", "Observation", "READY",
            fields={
                "variable": _field("Leaf Area Index (LAI)", anchors=["b:0015"]),
                "value": _field("3.1", anchors=["b:0015"]),
                "unit": _field("m2 m-2", anchors=["b:0015"]),
                "treatment": _field("treatment-2"),
                "site": _field("site-1"),
                "study": _field("study-1"),
            },
            evidence=["b:0015"],
            confidence=0.9,
        ),
        _base_record(
            "observation-3", "Observation", "ACCEPTED",
            fields={
                "variable": _field("Canopy height at anthesis", anchors=["b:0016"]),
                "value": _field("142", anchors=["b:0016"]),
                "unit": _field("cm", anchors=["b:0016"]),
                "treatment": _field("treatment-1"),
                "site": _field("site-1"),
                "study": _field("study-1"),
            },
            evidence=["b:0016"],
            confidence=0.92,
        ),
        _base_record(
            "observation-4", "Observation", "ACCEPTED",
            fields={
                "variable": _field("Canopy height at anthesis", anchors=["b:0016"]),
                "value": _field("128", anchors=["b:0016"]),
                "unit": _field("cm", anchors=["b:0016"]),
                "treatment": _field("treatment-2"),
                "site": _field("site-1"),
                "study": _field("study-1"),
            },
            evidence=["b:0016"],
            confidence=0.92,
        ),
        _base_record(
            "observation-5", "Observation", "NEEDS REVIEW",
            fields={
                "variable": _field("Light interception", anchors=["b:0017"]),
                "value": _field("90", anchors=["b:0017"]),
                "unit": _field("%", anchors=["b:0017"]),
                "treatment": _field(None, status="UNRESOLVED",
                                     reason="Statement applies to both populations; "
                                            "not attributed to a single treatment."),
                "site": _field("site-1"),
                "study": _field("study-1"),
            },
            evidence=["b:0017"],
            confidence=0.68,
        ),
        _base_record(
            "observation-6", "Observation", "NEEDS REVIEW",
            fields={
                "variable": _field("Canopy height threshold for 90% interception",
                                    anchors=["b:0017"]),
                "value": _field("60", anchors=["b:0017"]),
                "unit": _field("cm", anchors=["b:0017"]),
                "treatment": _field(None, status="UNRESOLVED"),
                "site": _field("site-1"),
                "study": _field("study-1"),
            },
            evidence=["b:0017"],
            confidence=0.7,
        ),
        _base_record(
            "observation-7", "Observation", "READY",
            fields={
                "variable": _field("Harvest years", anchors=["b:0013"]),
                "value": _field("2", anchors=["b:0013"]),
                "unit": _field("years", anchors=["b:0013"]),
                "treatment": _field("N/A"),
                "site": _field("site-1"),
                "study": _field("study-1"),
            },
            evidence=["b:0013"],
            confidence=0.85,
        ),
        _base_record(
            "observation-8", "Observation", "REJECTED",
            fields={
                "variable": _field("Replications", anchors=["b:0012"]),
                "value": _field("4", anchors=["b:0012"]),
                "unit": _field("blocks", anchors=["b:0012"]),
                "treatment": _field("N/A"),
                "site": _field("site-1"),
                "study": _field("study-1"),
            },
            evidence=["b:0012"],
            confidence=0.4,
        ),
    ],
    "management": [
        _base_record(
            "management-1", "Management", "READY",
            fields={
                "event": _field("Nitrogen fertilization", anchors=["b:0014"]),
                "timing": _field("Each spring", anchors=["b:0014"]),
                "material": _field("Ammonium nitrate", anchors=["b:0014"]),
                "amount": _field("112 kg N ha-1", anchors=["b:0014"]),
                "study": _field("study-1"),
            },
            evidence=["b:0014"],
            confidence=0.93,
        ),
        _base_record(
            "management-2", "Management", "ACCEPTED",
            fields={
                "event": _field("Establishment", anchors=["b:0012"]),
                "timing": _field("1993", anchors=["b:0012"]),
                "material": _field("Switchgrass seed (HY C2, Trailblazer)",
                                    anchors=["b:0012"]),
                "amount": _field("N/A", anchors=["b:0012"]),
                "study": _field("study-1"),
            },
            evidence=["b:0012"],
            confidence=0.86,
        ),
        _base_record(
            "management-3", "Management", "UNRESOLVED",
            fields={
                "event": _field("Harvest", anchors=["b:0013"]),
                "timing": _field(None, status="UNRESOLVED",
                                 reason="Exact harvest dates not stated, only maturity "
                                        "stages and years."),
                "material": _field("N/A"),
                "amount": _field("N/A"),
                "study": _field("study-1"),
            },
            evidence=["b:0013"],
            confidence=0.45,
        ),
    ],
}

ENTITY_ORDER = ["citation", "study", "site", "treatment", "observation", "management"]
ENTITY_LABELS = {
    "citation": "Citation",
    "study": "Studies",
    "site": "Sites",
    "treatment": "Treatments",
    "observation": "Observations",
    "management": "Management",
}


def get_fresh_records():
    """Return a deep copy of the mock records so session state can safely mutate it."""
    return copy.deepcopy(RECORDS)


def get_fresh_document_blocks():
    return copy.deepcopy(DOCUMENT_BLOCKS)


def get_paper(paper_id="pecan"):
    return copy.deepcopy(PAPERS.get(paper_id))


def get_all_papers():
    return copy.deepcopy(list(PAPERS.values()))