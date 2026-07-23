"""
eval_accuracy.py
Measures the detector's actual precision, recall, and F1 against a
labeled test set, instead of relying on "it worked when I tried it once."

Matching is by (label, exact text) - a detection counts as correct
only if both the PII type and the exact matched string are right.
"""

import os
import sys
from pdf2image import convert_from_path

sys.path.insert(0, os.path.dirname(__file__))
from detectors import detect_pii
from tests.generate_test_set import build_all


def _detect_on_pdf(pdf_path: str) -> list:
    pages = convert_from_path(pdf_path, dpi=200)
    all_detections = []
    for page in pages:
        all_detections.extend(detect_pii(page))
    return [{"label": d["label"], "text": d["text"]} for d in all_detections]


def run_eval():
    manifest = build_all()

    total_tp = total_fp = total_fn = 0
    per_doc_results = []

    for case in manifest:
        predicted = _detect_on_pdf(case["path"])
        expected = case["ground_truth"]

        pred_remaining = predicted.copy()
        tp = 0
        for exp in expected:
            match = next((p for p in pred_remaining if p == exp), None)
            if match:
                pred_remaining.remove(match)
                tp += 1
        fp = len(pred_remaining)
        fn = len(expected) - tp

        total_tp += tp
        total_fp += fp
        total_fn += fn

        per_doc_results.append({
            "file": os.path.basename(case["path"]),
            "expected": expected,
            "predicted": predicted,
            "tp": tp, "fp": fp, "fn": fn,
            "note": case["note"],
        })

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 1.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "total_tp": total_tp, "total_fp": total_fp, "total_fn": total_fn,
        "per_doc": per_doc_results,
    }


if __name__ == "__main__":
    results = run_eval()
    print("\n=== MaskFin Detector Accuracy ===")
    print(f"Precision: {results['precision']}")
    print(f"Recall:    {results['recall']}")
    print(f"F1:        {results['f1']}")
    print(f"(TP={results['total_tp']}, FP={results['total_fp']}, FN={results['total_fn']})\n")

    for doc in results["per_doc"]:
        status = "check" if doc["fp"] == 0 and doc["fn"] == 0 else "warn"
        print(f"{status} {doc['file']}  (tp={doc['tp']} fp={doc['fp']} fn={doc['fn']})")
        if doc["note"]:
            print(f"    note: {doc['note']}")
        if doc["fp"] or doc["fn"]:
            print(f"    expected: {doc['expected']}")
            print(f"    predicted: {doc['predicted']}")
    print()

# ---------------------------------------------------------------------------
# Root cause note (found via this eval, kept here for anyone reading the code):
#
# doc4's failure isn't just "an order number got misclassified as an account
# number" - Tesseract's OCR introduced a spurious space in the middle of the
# 15-digit reference number ("1002345678901 23" instead of "100234567890123"),
# splitting it into two OCR "words". Since the Account Number pattern doesn't
# allow internal whitespace (unlike the Aadhaar pattern, which does, since
# real Aadhaar numbers are conventionally printed with spaces), only the
# first 13-digit chunk matched.
#
# Practical implication: long numeric identifiers (15+ digits) are more
# vulnerable to partial-only redaction than short, fixed-format ones like
# PAN or IFSC, because a single OCR whitespace artifact can split them.
# A production version of this tool should merge adjacent short digit-only
# OCR words before applying the Account Number pattern, to make long numbers
# robust to this kind of OCR noise.
# ---------------------------------------------------------------------------
