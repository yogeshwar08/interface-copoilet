import argparse
import json
import os
import sys
from pathlib import Path

# Ensure project root is in PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.evaluation.evaluator import evaluator



def main():
    parser = argparse.ArgumentParser(description="Run Automated Evaluation on Enterprise Copilot Golden Benchmark")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of test samples (useful for fast CI)")
    parser.add_argument("--save", action="store_true", default=True, help="Save markdown and json evaluation reports")
    parser.add_argument("--threshold-router", type=float, default=0.85, help="Minimum acceptable router accuracy")
    parser.add_argument("--threshold-guardrail", type=float, default=0.90, help="Minimum acceptable guardrail accuracy")
    parser.add_argument("--threshold-faithfulness", type=float, default=0.80, help="Minimum acceptable faithfulness")
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("🚀 RUNNING AUTOMATED COPILOT EVALUATION (RAGAS / DeepEval Methodology)")
    print("=" * 70)
    if args.limit:
        print(f"Sampling {args.limit} test cases for quick validation...")
    else:
        print("Evaluating entire Golden Set (50+ enterprise test cases)...")

    report = evaluator.run_benchmark(limit=args.limit)

    print("\n" + report.to_markdown())

    if args.save:
        output_dir = Path("eval_results")
        output_dir.mkdir(exist_ok=True)

        md_path = output_dir / "evaluation_report.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report.to_markdown())

        json_path = output_dir / "evaluation_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "total_samples": report.total_samples,
                    "router_accuracy": report.router_accuracy,
                    "avg_faithfulness": report.avg_faithfulness,
                    "avg_answer_relevance": report.avg_answer_relevance,
                    "avg_context_precision": report.avg_context_precision,
                    "guardrail_accuracy": report.guardrail_accuracy,
                    "samples": [
                        {
                            "id": s.sample_id,
                            "question": s.question,
                            "category": s.category,
                            "expected_route": s.expected_route,
                            "actual_route": s.actual_route,
                            "route_correct": s.route_correct,
                            "faithfulness": s.faithfulness_score,
                            "relevance": s.answer_relevance_score,
                            "precision": s.context_precision_score,
                            "guardrail_correct": s.guardrail_correct,
                        }
                        for s in report.samples
                    ],
                },
                f,
                indent=2,
            )

        print(f"\n📁 Evaluation reports saved to: {output_dir.resolve()}")

    # Threshold checks for CI gating
    failed = False
    if report.router_accuracy < args.threshold_router:
        print(f"❌ CI GATING FAILURE: Router accuracy {report.router_accuracy:.2%} is below threshold {args.threshold_router:.2%}")
        failed = True
    if report.guardrail_accuracy < args.threshold_guardrail:
        print(f"❌ CI GATING FAILURE: Guardrail accuracy {report.guardrail_accuracy:.2%} is below threshold {args.threshold_guardrail:.2%}")
        failed = True

    if failed:
        sys.exit(1)

    print("\n🎉 All evaluation gating thresholds passed successfully!")


if __name__ == "__main__":
    main()
