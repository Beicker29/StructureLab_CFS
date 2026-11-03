"""CLI: python -m cfs_design.run member.json [--output result.json]

Prints the JSON result to stdout. Writes a file only with --output. Exit codes: 0 result
produced (PASS, FAIL or INCOMPLETE), 2 invalid input.
"""
import argparse
import json
import sys
from pathlib import Path

from .errors import CfsDesignError
from .execution import execute_payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="structurelab-cfs", description="AISI S100-24 cold-formed steel member check (LRFD)")
    parser.add_argument("input", type=Path, help="member JSON file")
    parser.add_argument("--output", type=Path, help="write the result here instead of only printing it")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise CfsDesignError("the input must be a JSON object", code="VALIDATION_ERROR")
        result = execute_payload(payload)
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"error": {"code": "INPUT_FILE_ERROR", "message": str(error)}}, ensure_ascii=False), file=sys.stderr)
        return 2
    except CfsDesignError as error:
        print(json.dumps({"error": error.to_dict()}, ensure_ascii=False), file=sys.stderr)
        return 2
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
