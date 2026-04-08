from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
from eval.run_eval import run_evaluation


def _run(dataset: Path, limit: int | None, use_embeddings: bool) -> dict:
    os.environ["KNOWLEDGE_EMBEDDINGS_ENABLED"] = "true" if use_embeddings else "false"
    return run_evaluation(
        dataset_path=dataset,
        limit=limit,
        use_llm=False,
        triage_only=True,
    )


def main() -> None:
    load_dotenv(override=False)
    parser = argparse.ArgumentParser(description="Compara retrieval lexical vs hybrid (embeddings)")
    parser.add_argument("--dataset", default="eval/conversations.jsonl")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    dataset = Path(args.dataset)
    lexical = _run(dataset, args.limit, use_embeddings=False)
    print(f"lexical pass_rate: {lexical['pass_rate']:.3f}")
    print(f"lexical sources_ok: {lexical['check_accuracy'].get('sources_ok', 0.0):.3f}")

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set; skipping hybrid run.")
        return

    hybrid = _run(dataset, args.limit, use_embeddings=True)
    print(f"hybrid pass_rate: {hybrid['pass_rate']:.3f}")
    print(f"hybrid sources_ok: {hybrid['check_accuracy'].get('sources_ok', 0.0):.3f}")
    print(f"delta pass_rate: {hybrid['pass_rate'] - lexical['pass_rate']:+.3f}")


if __name__ == "__main__":
    main()
