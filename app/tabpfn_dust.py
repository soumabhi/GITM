"""TabPFN-3.5 keep-or-sweep suggestions. The model never overrides the deny list."""

from __future__ import annotations

import os
from pathlib import Path

from app.dust import FolderRow, read_history

FEATURE_COLUMNS = ["kind", "size_mb", "age_days", "on_c", "name_has_cache"]


def history_frame(rows: list[dict]):
    import pandas as pd

    frame = pd.DataFrame(rows)
    for column in FEATURE_COLUMNS:
        if column not in frame.columns:
            frame[column] = 0
    labels = frame["label"].astype(str)
    features = frame[FEATURE_COLUMNS].copy()
    features["size_mb"] = features["size_mb"].astype(float)
    features["age_days"] = features["age_days"].astype(float)
    features["on_c"] = features["on_c"].astype(int)
    features["name_has_cache"] = features["name_has_cache"].astype(int)
    features["kind"] = features["kind"].astype(str)
    return features, labels


def both_labels(rows: list[dict]) -> bool:
    labels = {str(row.get("label", "")).strip() for row in rows}
    return "sweep" in labels and "keep" in labels


def suggest(history_path: Path, candidates: list[FolderRow], cache_dir: Path) -> tuple[list[FolderRow], str]:
    rows = read_history(history_path)
    if not both_labels(rows):
        return candidates, "Dust history needs both keep and sweep rows before TabPFN can learn."
    try:
        from tabpfn import TabPFNClassifier
        from tabpfn.constants import ModelVersion
    except Exception:
        return candidates, "TabPFN is not installed. The ghost can still sweep temp files."
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TABPFN_MODEL_CACHE_DIR"] = str(cache_dir)
    try:
        if not candidates:
            return candidates, "No heavy folders to score."
        train_x, train_y = history_frame(rows)
        predict_x, _ = history_frame([row.features() | {"label": "keep"} for row in candidates])
        try:
            classifier = TabPFNClassifier.create_default_for_version(ModelVersion.V3_5, device="cpu")
        except TypeError:
            classifier = TabPFNClassifier.create_default_for_version(ModelVersion.V3_5)
        classifier.fit(train_x, train_y)
        probabilities = classifier.predict_proba(predict_x)
        classes = [str(label) for label in classifier.classes_]
        sweep_index = classes.index("sweep") if "sweep" in classes else 1
        for row, scores in zip(candidates, probabilities):
            if row.denied:
                row.sweep_prob = 0.0
            else:
                row.sweep_prob = float(scores[sweep_index])
        note = "TabPFN 3.5 local"
    except Exception as exc:
        return candidates, f"TabPFN could not run yet ({exc.__class__.__name__}). Temp sweep still works."
    return candidates, note
