"""Validate a secret-free, fixed-operation VPS discovery plan from stdin."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extensions.read_only_discovery_plan import (  # noqa: E402
    DiscoveryPlanValidationError,
    validate_read_only_discovery_plan,
)


def main() -> int:
    try:
        raw = json.load(sys.stdin)
        plan = validate_read_only_discovery_plan(raw)
    except (json.JSONDecodeError, DiscoveryPlanValidationError) as exc:
        field = exc.field if isinstance(exc, DiscoveryPlanValidationError) else "json"
        print(json.dumps({"valid": False, "field": field}, separators=(",", ":")))
        return 2
    except Exception:
        print('{"valid":false,"field":"plan"}')
        return 2
    print(json.dumps({
        "valid": True,
        "scope": plan.authorization["scope"],
        "target_role": plan.authorization["target_role"],
        "operations": [item["id"] for item in plan.operations],
    }, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
