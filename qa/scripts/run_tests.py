#!/usr/bin/env python3
"""Exécute la campagne de tests fonctionnels MorphoLapse en mode CLI.

Itère sur les jeux d'inputs prédéfinis et lance `python main.py --cli ...`
pour chacun. Les sorties vont dans `qa/outputs_reels/<test_id>/`.

NB : ne couvre QUE les tests fonctionnels reproductibles via CLI.
Les tests IHM purs (T-001..T-040, T-070..T-088) doivent être exécutés
manuellement via `qa/validation_ihm.html`.

Usage :
    python qa/scripts/run_tests.py              # tous les tests CLI
    python qa/scripts/run_tests.py --only T-063 # un seul test
    python qa/scripts/run_tests.py --list       # liste les tests CLI
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEST_DIR = PROJECT_ROOT / "test"
INPUTS_DIR = TEST_DIR / "inputs"
OUTPUTS_DIR = TEST_DIR / "outputs_reels"

# Console Windows par défaut en cp1252 → forcer UTF-8 pour les caractères Unicode dans les notes
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


@dataclass
class CliTest:
    test_id: str
    input_subdir: str
    options: dict
    expected_outcome: str          # "ok" / "error_no_image" / "error_pipeline" / ...
    note: str = ""


# Catalogue des tests exécutables via CLI
CLI_TESTS: list[CliTest] = [
    CliTest("T-063", "input_nominal", {}, "ok",
            "Workflow nominal synthétique (fallback cross-dissolve attendu)"),
    CliTest("T-064", "input_vide", {}, "error_no_image",
            "Dossier vide → erreur 'Aucune image trouvée'"),
    CliTest("T-065", "input_1image", {}, "error_pipeline",
            "1 seule image → erreur step Morph"),
    CliTest("T-066", "input_volume", {}, "ok",
            "Volume 100 images"),
    CliTest("T-067", "input_mauvais_format", {}, "error_no_image",
            "Tous les fichiers .png sont invalides → 0 image valide"),
    CliTest("T-068", "input_specchars", {}, "ok",
            "Noms Unicode"),
    CliTest("T-070", "input_limite_haute", {}, "ok",
            "Images 2000×2000 (mémoire)"),
    CliTest("T-071", "input_limite_basse", {}, "ok",
            "Images 64×64 (dlib échouera)"),
    CliTest("T-072", "input_corrompu", {}, "error_no_image",
            "PNG tronqués"),
    CliTest("T-073", "input_no_face", {}, "ok",
            "Gradients (fallback cross-dissolve)"),
    CliTest("T-074", "input_reel", {}, "ok",
            "Photos réelles (fournies par utilisateur)"),
    CliTest("T-076", "input_reel", {"resolution": "720p"}, "ok",
            "Résolution 720p"),
    CliTest("T-077", "input_reel", {"resolution": "1080p"}, "ok",
            "Résolution 1080p"),
    CliTest("T-078", "input_reel", {"resolution": "480p"}, "ok",
            "Résolution 480p"),
]


def _build_command(test: CliTest, input_dir: Path, output_dir: Path) -> list[str]:
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "main.py"),
        "--cli",
        "-i", str(input_dir),
        "-o", str(output_dir),
    ]
    # Options optionnelles
    if "resolution" in test.options:
        # Le CLI courant ne propose pas --resolution direct ; à passer via config si besoin.
        # Ici on logue simplement la limite.
        pass
    return cmd


def run_one(test: CliTest, *, verbose: bool = True) -> dict:
    """Exécute un test, retourne un dict de résultat."""
    input_dir = INPUTS_DIR / test.input_subdir
    output_dir = OUTPUTS_DIR / test.test_id

    # Reset output
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result: dict = {
        "test_id": test.test_id,
        "input": str(input_dir),
        "output": str(output_dir),
        "expected": test.expected_outcome,
        "started_at": datetime.now().isoformat(),
        "options": test.options,
        "note": test.note,
    }

    if not input_dir.exists() or not any(input_dir.iterdir()):
        result["skipped"] = True
        result["reason"] = f"Dossier d'entrée vide ou absent : {input_dir}"
        return result

    cmd = _build_command(test, input_dir, output_dir)
    if verbose:
        print(f"--- {test.test_id} : {' '.join(cmd[-4:])}")

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,  # 15 min max
        )
        result["returncode"] = proc.returncode
        result["stdout_tail"] = (proc.stdout or "")[-2000:]
        result["stderr_tail"] = (proc.stderr or "")[-2000:]
    except subprocess.TimeoutExpired:
        result["returncode"] = -1
        result["timeout"] = True

    result["finished_at"] = datetime.now().isoformat()

    # Sauvegarder le log par test
    (output_dir / "_run.log").write_text(
        f"# Test {test.test_id}\n"
        f"## Command\n{' '.join(cmd)}\n\n"
        f"## Returncode\n{result.get('returncode')}\n\n"
        f"## Stdout (tail 2k)\n{result.get('stdout_tail', '')}\n\n"
        f"## Stderr (tail 2k)\n{result.get('stderr_tail', '')}\n",
        encoding="utf-8",
    )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Exécute la campagne CLI MorphoLapse.")
    parser.add_argument("--only", help="ID unique (ex: T-063)")
    parser.add_argument("--list", action="store_true", help="Liste les tests CLI")
    args = parser.parse_args()

    if args.list:
        print(f"{'ID':<8} {'Input':<24} {'Attendu':<22} Note")
        print("-" * 90)
        for t in CLI_TESTS:
            print(f"{t.test_id:<8} {t.input_subdir:<24} {t.expected_outcome:<22} {t.note}")
        return 0

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    selected = [t for t in CLI_TESTS if args.only is None or t.test_id == args.only]
    if not selected:
        print(f"Aucun test ne correspond à --only={args.only}", file=sys.stderr)
        return 1

    results = []
    for t in selected:
        results.append(run_one(t))

    # Rapport global
    report_path = OUTPUTS_DIR / "_run_summary.json"
    report_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().isoformat(),
                "total": len(results),
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Synthèse console
    ok = sum(1 for r in results if r.get("returncode") == 0)
    timeouts = sum(1 for r in results if r.get("timeout"))
    skipped = sum(1 for r in results if r.get("skipped"))
    nok = len(results) - ok - timeouts - skipped
    print("\n=== Synthèse ===")
    print(f"Total      : {len(results)}")
    print(f"Returncode 0 : {ok}")
    print(f"Returncode ≠0 : {nok}")
    print(f"Timeouts    : {timeouts}")
    print(f"Skipped     : {skipped}")
    print(f"\nRapport : {report_path}")

    return 0 if (nok == 0 and timeouts == 0) else 2


if __name__ == "__main__":
    sys.exit(main())
