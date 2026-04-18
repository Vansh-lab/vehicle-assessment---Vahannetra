#!/usr/bin/env bash
set -euo pipefail

required_vars=(
  AWS_ROLE_TO_ASSUME
  AWS_REGION
  BACKEND_IMAGE_REPO
  FRONTEND_IMAGE_REPO
  ECS_CLUSTER
  ECS_BACKEND_SERVICE
  ECS_FRONTEND_SERVICE
)

missing=0
for key in "${required_vars[@]}"; do
  if [[ -z "${!key:-}" ]]; then
    echo "❌ Missing required variable: $key"
    missing=1
  fi
done

benchmark_count=0
for i in {1..8}; do
  key="BENCHMARK_URL_${i}"
  value="${!key:-}"
  if [[ -n "$value" ]]; then
    benchmark_count=$((benchmark_count + 1))
    if [[ ! "$value" =~ ^https?:// ]]; then
      echo "❌ $key must be an absolute http/https URL: $value"
      missing=1
    fi
  fi
done

if [[ "$benchmark_count" -eq 0 ]]; then
  echo "❌ At least one BENCHMARK_URL_1..8 must be configured"
  missing=1
fi

codes="${BENCHMARK_ACCEPTABLE_CODES:-200,201,202,204,301,302,401,403}"
if [[ ! "$codes" =~ ^[0-9]{3}(,[0-9]{3})*$ ]]; then
  echo "❌ BENCHMARK_ACCEPTABLE_CODES must be comma-separated 3-digit codes: $codes"
  missing=1
fi

if [[ "$missing" -ne 0 ]]; then
  echo
  echo "Preflight failed. Export required variables and run again."
  exit 1
fi

echo "✅ Preflight passed."
echo "Configured benchmark targets: $benchmark_count"
echo "Acceptable codes: $codes"
