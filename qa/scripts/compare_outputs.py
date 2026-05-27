#!/usr/bin/env python3
"""Compare les sorties réelles aux références (non-régression MorphoLapse).

Pour chaque test ayant tourné, regarde ce qu'il a produit dans
`qa/outputs_reels/<id>/` et compare contre `qa/outputs_reference/ref_<id>.*`.

Usage :
    python qa/scripts/compare_outputs.py              # compare tout
    python qa/scripts/compare_outputs.py --only T-063
    python qa/scripts/compare_outputs.py --promote T-074   # crée la référence
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEST_DIR = PROJECT_ROOT / "test"
OUTPUTS_DIR = TEST_DIR / "outputs_reels"
REFERENCES_DIR = TEST_DIR / "outputs_reference"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

NB_FRAMES_TOLERANCE = 2  # tolérance ±2 frames sur la durée vidéo


def _find_run_dir(test_id: str) -> Path | None:
    """Cherche le dossier de run effectif (runs/<timestamp>/) à l'intérieur d'outputs_reels/<id>/.

    En mode CLI, MorphoLapse crée runs/<timestamp>/ dans le CWD. En mode programmatique,
    on prend le run le plus récent à l'intérieur du dossier output.
    """
    base = OUTPUTS_DIR / test_id
    if not base.exists():
        return None
    # MorphoLapse copie les résultats DIRECTEMENT dans output_dir, mais le run lui-même
    # est dans runs/ à la racine du projet. On cherche le plus récent.
    runs_root = PROJECT_ROOT / "runs"
    if not runs_root.exists():
        return base
    candidates = sorted(runs_root.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else base


def _ffprobe_signature(video_path: Path) -> dict | None:
    """Lance ffprobe et extrait les clés utiles."""
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format",
             "-print_format", "json", str(video_path)],
            capture_output=True, text=True, timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    streams = data.get("streams", [])
    if not streams:
        return None
    v = next((s for s in streams if s.get("codec_type") == "video"), streams[0])
    return {
        "codec_name": v.get("codec_name"),
        "pix_fmt": v.get("pix_fmt"),
        "width": v.get("width"),
        "height": v.get("height"),
        "r_frame_rate": v.get("r_frame_rate"),
        "nb_frames": int(v.get("nb_frames", 0)) if v.get("nb_frames", "").isdigit() else None,
    }


def _diff_dict(ref: dict, got: dict, tolerances: dict[str, int] | None = None) -> list[str]:
    """Retourne la liste des écarts. tolerances : {clé: tol_absolue} pour les ints."""
    tolerances = tolerances or {}
    diffs = []
    for k, v_ref in ref.items():
        v_got = got.get(k)
        if k in tolerances and isinstance(v_ref, int) and isinstance(v_got, int):
            if abs(v_ref - v_got) > tolerances[k]:
                diffs.append(f"{k}: ref={v_ref} vs got={v_got} (tolérance ±{tolerances[k]})")
        elif v_ref != v_got:
            diffs.append(f"{k}: ref={v_ref!r} vs got={v_got!r}")
    return diffs


def _find_video_in(run_dir: Path) -> Path | None:
    """Trouve la vidéo MP4 finale dans un run."""
    for sub in ["04_export", "03_morph"]:
        for p in (run_dir / sub).glob("*.mp4"):
            return p
    return None


def compare_one(test_id: str) -> dict:
    """Compare un test unique. Retourne un dict {status, details}."""
    res: dict = {"test_id": test_id, "checks": []}
    run_dir = _find_run_dir(test_id)
    if not run_dir:
        res["status"] = "no_run"
        res["details"] = f"Aucun run trouvé pour {test_id}"
        return res

    # 1. Comparaison vidéo via ffprobe
    ref_ffprobe = REFERENCES_DIR / f"ref_{test_id}.ffprobe.json"
    if ref_ffprobe.exists():
        video = _find_video_in(run_dir)
        if not video:
            res["checks"].append({"kind": "video", "status": "FAIL", "detail": "Aucune vidéo trouvée dans le run"})
        else:
            got_sig = _ffprobe_signature(video)
            if got_sig is None:
                res["checks"].append({"kind": "video", "status": "FAIL", "detail": "ffprobe a échoué"})
            else:
                ref_sig = json.loads(ref_ffprobe.read_text(encoding="utf-8"))
                diffs = _diff_dict(ref_sig, got_sig, tolerances={"nb_frames": NB_FRAMES_TOLERANCE})
                res["checks"].append({
                    "kind": "video",
                    "status": "OK" if not diffs else "FAIL",
                    "diffs": diffs,
                })

    # 2. Comparaison run_summary.json (structurelle)
    ref_summary = REFERENCES_DIR / f"ref_{test_id}.summary.json"
    if ref_summary.exists():
        got_summary_path = run_dir / "04_export" / "run_summary.json"
        if not got_summary_path.exists():
            res["checks"].append({"kind": "summary", "status": "FAIL", "detail": "run_summary.json absent"})
        else:
            try:
                ref = json.loads(ref_summary.read_text(encoding="utf-8"))
                got = json.loads(got_summary_path.read_text(encoding="utf-8"))
                # Comparaison structurelle : mêmes clés top-level
                missing = set(ref.keys()) - set(got.keys())
                extra = set(got.keys()) - set(ref.keys())
                res["checks"].append({
                    "kind": "summary",
                    "status": "OK" if not missing and not extra else "FAIL",
                    "missing_keys": list(missing),
                    "extra_keys": list(extra),
                })
            except json.JSONDecodeError as e:
                res["checks"].append({"kind": "summary", "status": "FAIL", "detail": str(e)})

    # 3. Comparaison metadata.txt (clés)
    ref_meta = REFERENCES_DIR / f"ref_{test_id}.metadata.txt"
    if ref_meta.exists():
        got_meta_path = run_dir / "04_export" / "metadata.txt"
        if not got_meta_path.exists():
            res["checks"].append({"kind": "metadata", "status": "FAIL", "detail": "metadata.txt absent"})
        else:
            ref_lines = ref_meta.read_text(encoding="utf-8").splitlines()
            got_lines = got_meta_path.read_text(encoding="utf-8").splitlines()
            # Compare uniquement les clés ("clé:" en début de ligne)
            kv_pat = re.compile(r"^([a-zA-Z_]+):")
            ref_keys = {m.group(1) for m in (kv_pat.match(line) for line in ref_lines) if m}
            got_keys = {m.group(1) for m in (kv_pat.match(line) for line in got_lines) if m}
            res["checks"].append({
                "kind": "metadata",
                "status": "OK" if ref_keys == got_keys else "FAIL",
                "missing_keys": list(ref_keys - got_keys),
                "extra_keys": list(got_keys - ref_keys),
            })

    if not res["checks"]:
        res["status"] = "no_reference"
    elif all(c["status"] == "OK" for c in res["checks"]):
        res["status"] = "OK"
    else:
        res["status"] = "FAIL"
    return res


def promote(test_id: str) -> None:
    """Promeut les sorties du test test_id en références."""
    run_dir = _find_run_dir(test_id)
    if not run_dir:
        print(f"Aucun run trouvé pour {test_id}", file=sys.stderr)
        sys.exit(2)

    REFERENCES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Vidéo → signature ffprobe
    video = _find_video_in(run_dir)
    if video:
        sig = _ffprobe_signature(video)
        if sig:
            out = REFERENCES_DIR / f"ref_{test_id}.ffprobe.json"
            out.write_text(json.dumps(sig, indent=2), encoding="utf-8")
            print(f"  signature vidéo → {out}")

    # 2. run_summary.json (copie structurelle)
    summary = run_dir / "04_export" / "run_summary.json"
    if summary.exists():
        out = REFERENCES_DIR / f"ref_{test_id}.summary.json"
        shutil.copy2(summary, out)
        print(f"  run_summary → {out}")

    # 3. metadata.txt
    meta = run_dir / "04_export" / "metadata.txt"
    if meta.exists():
        out = REFERENCES_DIR / f"ref_{test_id}.metadata.txt"
        shutil.copy2(meta, out)
        print(f"  metadata → {out}")

    print(f"OK : références {test_id} promues.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Comparaison sorties réelles vs références.")
    parser.add_argument("--only", help="ID unique (ex: T-063)")
    parser.add_argument("--promote", metavar="TEST_ID",
                        help="Promeut les sorties d'un test en référence")
    args = parser.parse_args()

    if args.promote:
        promote(args.promote)
        return 0

    if not OUTPUTS_DIR.exists():
        print("Aucun dossier outputs_reels/ : lance d'abord run_tests.py", file=sys.stderr)
        return 1

    # Collecter les tests à comparer
    if args.only:
        targets = [args.only]
    else:
        targets = [p.name for p in OUTPUTS_DIR.iterdir() if p.is_dir() and p.name.startswith("T-")]

    if not targets:
        print("Aucun test à comparer.", file=sys.stderr)
        return 1

    results = [compare_one(t) for t in sorted(targets)]

    # Rapport markdown
    lines = ["# Comparaison sorties\n",
             f"Date : {datetime.now().isoformat()}\n",
             "| Test | Statut | Détail |",
             "|---|---|---|"]
    for r in results:
        status = r.get("status", "?")
        details = []
        for c in r.get("checks", []):
            details.append(f"{c['kind']}: {c['status']}")
            if c.get("diffs"):
                details.append(" diffs: " + "; ".join(c["diffs"]))
        lines.append(f"| {r['test_id']} | {status} | {' / '.join(details) or '—'} |")
    report = "\n".join(lines)
    out = OUTPUTS_DIR / "_comparison_report.md"
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nRapport : {out}")

    fails = sum(1 for r in results if r.get("status") == "FAIL")
    return 0 if fails == 0 else 3


if __name__ == "__main__":
    sys.exit(main())
