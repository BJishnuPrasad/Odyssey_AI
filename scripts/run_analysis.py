"""Run the same analysis used by the API, with persistent history."""
import argparse
import uuid
from backend import database as db
from backend.analysis import execute
from backend.settings import RUNTIME


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution", type=int, choices=[100, 250, 500], default=250)
    parser.add_argument("--slope-weight", type=float, default=0.55)
    args = parser.parse_args()
    if not 0.1 <= args.slope_weight <= 0.9:
        parser.error("slope-weight must be between 0.1 and 0.9")
    db.initialize(recover=False)
    if any(run['status'] in ('queued', 'running') for run in db.list_runs()):
        parser.error('Another run is active. Wait for completion or restart the API to recover an interrupted run.')
    run_id = uuid.uuid4().hex
    parameters = {"resolution_m": args.resolution, "slope_weight": args.slope_weight}
    db.create_run(run_id, parameters)
    db.update_run(run_id, status="running")
    def progress(percent, stage):
        print(f"{percent}% {stage}", flush=True)
        db.update_run(run_id, progress=percent, stage=stage)
    try:
        summary = execute(RUNTIME / "runs" / run_id, parameters, progress)
        db.update_run(run_id, status="completed", progress=100, stage="Complete", summary=summary, finished_at=db.now())
        print(f"Run {run_id}: {summary['coverage_percent']}% terrain coverage; {summary['heritage_sites']} heritage records", flush=True)
    except Exception as exc:
        db.update_run(run_id, status="failed", stage="Failed", error=str(exc), finished_at=db.now())
        raise


if __name__ == "__main__":
    main()
