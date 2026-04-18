# AWS Runtime Proof Runbook (ECS/ECR + Rollback + Perf Evidence)

This runbook closes the **real AWS runtime proof** pending item for `.github/workflows/deploy-ecs.yml` by defining exact steps, required inputs, and expected evidence.

## 1) Scope

Workflow under proof:

- `.github/workflows/deploy-ecs.yml`

Proof goals:

1. Live deploy to ECS after ECR image push.
2. Health-gate execution with 8 target checks.
3. Timed perf evidence artifact upload (`perf/timed-benchmark.csv`).
4. Verified rollback path when health gate fails.

---

## 2) Required GitHub inputs matrix

### 2.1 Secrets (Repository → Settings → Secrets and variables → Actions)

| Name | Required | Used by | Notes |
|---|---|---|---|
| `AWS_ROLE_TO_ASSUME` | Yes | `aws-actions/configure-aws-credentials@v4` | IAM role ARN for GitHub OIDC trust |

### 2.2 Variables (Repository → Settings → Secrets and variables → Actions)

| Name | Required | Example | Notes |
|---|---|---|---|
| `AWS_REGION` | Yes | `ap-south-1` | Region where ECS/ECR exist |
| `BACKEND_IMAGE_REPO` | Yes | `vahannetra-backend` | ECR repo name |
| `FRONTEND_IMAGE_REPO` | Yes | `vahannetra-frontend` | ECR repo name |
| `ECS_CLUSTER` | Yes | `vahannetra-prod` | ECS cluster name |
| `ECS_BACKEND_SERVICE` | Yes | `vahannetra-backend-svc` | ECS service name |
| `ECS_FRONTEND_SERVICE` | Yes | `vahannetra-frontend-svc` | ECS service name |
| `BENCHMARK_URL_1..8` | At least one required | `https://app.example.com/health` | Workflow fails if all are empty |
| `BENCHMARK_ACCEPTABLE_CODES` | Recommended | `200,201,202,204,301,302,401,403` | CSV of allowed HTTP status codes |

---

## 3) Preflight checks (local)

From repo root:

```bash
cd /home/runner/work/vehicle-assessment---Vahannetra/vehicle-assessment---Vahannetra/FDA_Project
bash scripts/aws_deploy_preflight.sh
```

This validates:

- required env values are set,
- at least one benchmark URL is configured,
- acceptable status code list format is valid.

---

## 4) Live execution (GitHub Actions)

1. Ensure branch is `main` or `master` (workflow `push` trigger), or run manually using `workflow_dispatch`.
2. Trigger run:
   - GitHub UI: Actions → **Deploy ECS/ECR** → **Run workflow**
3. Wait until jobs complete:
   - `build-and-push`
   - `deploy`
   - `health-gates`
   - (optional) `rollback-on-failure` if health gate fails

---

## 5) Required evidence to capture

Collect and store these links/artifacts for audit:

1. **Workflow run URL**.
2. **ECR image refs** from `build-and-push` logs (backend + frontend SHA tags).
3. **ECS stable wait success** from `deploy` logs.
4. **Artifact**: `ecs-timed-perf-evidence-<run_id>` containing `timed-benchmark.csv`.
5. **CSV rows** showing target, HTTP code, total time, connect time, TTFB.

---

## 6) Rollback proof execution

Run two controlled executions:

### A) Success-path proof

- Configure valid `BENCHMARK_URL_*` endpoints.
- Confirm workflow conclusion is success.

### B) Rollback-path proof

- Intentionally set one benchmark URL to a failing endpoint (or expected non-acceptable code).
- Confirm `health-gates` fails.
- Confirm `rollback-on-failure` executes and waits services stable.
- Capture rollback log lines with previous task definition restoration.

After proof, revert benchmark URL values to valid targets.

---

## 7) Acceptance checklist

- [ ] Required secret and variables configured.
- [ ] Preflight script passes.
- [ ] Success-path run completed with perf artifact.
- [ ] Rollback-path run completed with service restoration evidence.
- [ ] Final run re-validated in success state after rollback test.

---

## 8) Notes on current blocker classes

- If workflow cannot assume role: check `AWS_ROLE_TO_ASSUME` trust policy for GitHub OIDC subject/repo/branch conditions.
- If all benchmark URLs are empty: workflow intentionally fails by design.
- If benchmark URL returns a code outside `BENCHMARK_ACCEPTABLE_CODES`: health gate fails and rollback path should execute.
