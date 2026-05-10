from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from tqdm import tqdm


class DataPipelineRunner:
    """
    Orchestrateur global déterministe.

    Rôle :
    - lancer phase 1 ingestion ;
    - lancer phase 2 extraction ;
    - lancer phase 2.5 audit extraction ;
    - lancer phase 3 processing ;
    - stocker un rapport global.
    """

    def __init__(
        self,
        companies: str | None = None,
        years: str | None = None,
        max_pages: int = 2,
        limit: int | None = None,
        force: bool = False,
        verbose: bool = False,
        reports_dir: str = "data/pipeline_runs",
    ):
        self.companies = companies
        self.years = years
        self.max_pages = max_pages
        self.limit = limit
        self.force = force
        self.verbose = verbose

        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def build_common_args(self) -> list[str]:
        args = []

        if self.companies:
            args.extend(["--companies", self.companies])

        if self.years:
            args.extend(["--years", self.years])

        return args

    def run_command(self, name: str, command: list[str]) -> dict:
        start = time.time()

        result = {
            "phase": name,
            "command": " ".join(command),
            "status": "unknown",
            "returncode": None,
            "duration_seconds": None,
            "stdout": "",
            "stderr": "",
        }

        try:
            completed = subprocess.run(
                command,
                text=True,
                capture_output=True,
                check=False,
            )

            result["returncode"] = completed.returncode
            result["stdout"] = completed.stdout
            result["stderr"] = completed.stderr
            result["duration_seconds"] = round(time.time() - start, 2)

            if completed.returncode == 0:
                result["status"] = "success"
            else:
                result["status"] = "error"

            if self.verbose:
                print("\n" + "=" * 80)
                print(f"PHASE : {name}")
                print("=" * 80)
                print(completed.stdout)

                if completed.stderr:
                    print("\nSTDERR:")
                    print(completed.stderr)

            return result

        except Exception as e:
            result["status"] = "error"
            result["stderr"] = str(e)
            result["duration_seconds"] = round(time.time() - start, 2)
            return result

    def phase_ingestion(self) -> dict:
        command = [
            sys.executable,
            "-m",
            "app.ingest.run_all",
            "--only-brvm",
            "--max-pages",
            str(self.max_pages),
        ]

        command.extend(self.build_common_args())

        if self.limit is not None:
            command.extend(["--limit", str(self.limit)])

        if self.verbose:
            command.append("--verbose")

        return self.run_command("phase_1_ingestion", command)

    def phase_extraction(self) -> dict:
        command = [
            sys.executable,
            "-m",
            "app.extraction.run_extraction",
        ]

        command.extend(self.build_common_args())

        if self.force:
            command.append("--force")

        return self.run_command("phase_2_extraction", command)

    def phase_extraction_audit(self) -> dict:
        command = [
            sys.executable,
            "-m",
            "app.extraction.extraction_audit",
        ]

        command.extend(self.build_common_args())

        return self.run_command("phase_2_5_extraction_audit", command)

    def phase_processing(self) -> dict:
        command = [
            sys.executable,
            "-m",
            "app.processing.run_processing",
        ]

        command.extend(self.build_common_args())

        if self.force:
            command.append("--force")

        return self.run_command("phase_3_processing", command)

    def save_report(self, report: dict) -> Path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = self.reports_dir / f"pipeline_run_{timestamp}.json"

        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path

    def run(self, start_from: str = "ingestion", stop_after: str = "processing") -> dict:
        phases = [
            ("ingestion", self.phase_ingestion),
            ("extraction", self.phase_extraction),
            ("audit", self.phase_extraction_audit),
            ("processing", self.phase_processing),
        ]

        phase_names = [name for name, _ in phases]

        if start_from not in phase_names:
            raise ValueError(f"Unknown start_from={start_from}. Options: {phase_names}")

        if stop_after not in phase_names:
            raise ValueError(f"Unknown stop_after={stop_after}. Options: {phase_names}")

        start_idx = phase_names.index(start_from)
        stop_idx = phase_names.index(stop_after)

        if start_idx > stop_idx:
            raise ValueError("start_from must be before or equal to stop_after")

        selected_phases = phases[start_idx : stop_idx + 1]

        results = []

        with tqdm(total=len(selected_phases), desc="Pipeline phases", unit="phase") as pbar:
            for phase_name, phase_fn in selected_phases:
                pbar.set_description(f"Running {phase_name}")

                result = phase_fn()
                results.append(result)

                pbar.update(1)

                if result["status"] != "success":
                    break

        overall_status = "success"

        if any(r["status"] != "success" for r in results):
            overall_status = "error"

        report = {
            "overall_status": overall_status,
            "companies": self.companies or "all",
            "years": self.years or "all",
            "start_from": start_from,
            "stop_after": stop_after,
            "phases": results,
        }

        report_path = self.save_report(report)
        report["report_path"] = str(report_path)

        return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline global Phase 1 → Phase 3"
    )

    parser.add_argument(
        "--companies",
        type=str,
        default=None,
        help='Exemple: "ORAC" ou "ORANGE CI,SONATEL"',
    )

    parser.add_argument(
        "--years",
        type=str,
        default=None,
        help='Exemple: "2024,2025" ou "2024-2026"',
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=2,
        help="Nombre de pages BRVM à parcourir pendant ingestion.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limite de rapports à traiter pendant ingestion.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reconstruction extraction/processing.",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Affiche les sorties détaillées des sous-commandes.",
    )

    parser.add_argument(
        "--start-from",
        type=str,
        default="ingestion",
        choices=["ingestion", "extraction", "audit", "processing"],
    )

    parser.add_argument(
        "--stop-after",
        type=str,
        default="processing",
        choices=["ingestion", "extraction", "audit", "processing"],
    )

    args = parser.parse_args()

    runner = DataPipelineRunner(
        companies=args.companies,
        years=args.years,
        max_pages=args.max_pages,
        limit=args.limit,
        force=args.force,
        verbose=args.verbose,
    )

    report = runner.run(
        start_from=args.start_from,
        stop_after=args.stop_after,
    )

    print("\nPIPELINE TERMINÉ")
    print("=" * 60)
    print(f"Status global : {report['overall_status']}")
    print(f"Entreprises   : {report['companies']}")
    print(f"Années        : {report['years']}")
    print(f"Rapport       : {report['report_path']}")
    print("=" * 60)

    for phase in report["phases"]:
        print(
            f"{phase['phase']} | {phase['status']} | "
            f"{phase['duration_seconds']}s"
        )

    if report["overall_status"] != "success":
        print("\nUne phase a échoué. Vérifie le rapport JSON.")
        sys.exit(1)


if __name__ == "__main__":
    main()