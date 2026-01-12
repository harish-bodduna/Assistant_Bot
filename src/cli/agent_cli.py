from __future__ import annotations

import argparse

from src.orchestration.agent import build_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the orchestration agent for a single query.")
    parser.add_argument("--query", required=True, help="User query")
    args = parser.parse_args()

    agent = build_agent()
    result = agent.run(args.query)
    print(result)


if __name__ == "__main__":
    main()

