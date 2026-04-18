# Operator Mode: Final Runtime-Proof Execution (Copy-Paste Run Order)

Use this in real GitHub + AWS environment to close all remaining external blockers.

## 0) Preconditions

- Repo admin access on GitHub.
- AWS account with ECS/ECR resources already created.
- Ability to set GitHub Actions Secret/Variables.

---

## 1) Configure GitHub Actions inputs

Go to:  
`https://github.com/Vansh-lab/vehicle-assessment---Vahannetra/settings/secrets/actions`

Set Secret:

- `AWS_ROLE_TO_ASSUME`

Go to:  
`https://github.com/Vansh-lab/vehicle-assessment---Vahannetra/settings/variables/actions`

Set Variables:

- `AWS_REGION`
- `BACKEND_IMAGE_REPO`
- `FRONTEND_IMAGE_REPO`
- `ECS_CLUSTER`
- `ECS_BACKEND_SERVICE`
- `ECS_FRONTEND_SERVICE`
- `BENCHMARK_URL_1` (required minimum 1 target)
- Optional: `BENCHMARK_URL_2..8`
- Optional: `BENCHMARK_ACCEPTABLE_CODES`

Expected result: all required keys visible in GitHub settings.

---

## 2) Local preflight validation

From repository root:

```bash
cd /home/runner/work/vehicle-assessment---Vahannetra/vehicle-assessment---Vahannetra/FDA_Project
export AWS_ROLE_TO_ASSUME='arn:aws:iam::<account-id>:role/<github-oidc-role>'
export AWS_REGION='ap-south-1'
export BACKEND_IMAGE_REPO='vahannetra-backend'
export FRONTEND_IMAGE_REPO='vahannetra-frontend'
export ECS_CLUSTER='vahannetra-prod'
export ECS_BACKEND_SERVICE='vahannetra-backend-svc'
export ECS_FRONTEND_SERVICE='vahannetra-frontend-svc'
export BENCHMARK_URL_1='https://<your-domain>/health'
make aws-preflight
```

Expected output:

- `✅ Preflight passed.`
- `Configured benchmark targets: <N>`

---

## 3) Success-path runtime proof (live deploy)

Go to Actions:

`https://github.com/Vansh-lab/vehicle-assessment---Vahannetra/actions/workflows/deploy-ecs.yml`

Run workflow on `main` or `master`.

Expected job results:

- `build-and-push` ✅
- `deploy` ✅
- `health-gates` ✅
- `rollback-on-failure` skipped (expected)

Evidence to save:

1. Workflow run URL
2. Backend/Frontend pushed image tags in logs
3. `aws ecs wait services-stable` success lines
4. Artifact: `ecs-timed-perf-evidence-<run_id>`
5. CSV content (`timed-benchmark.csv`)

---

## 4) Rollback-path runtime proof (intentional gate failure)

Set one benchmark URL to known failing endpoint or disallowed status-code target.  
Rerun same workflow.

Expected job results:

- `build-and-push` ✅
- `deploy` ✅
- `health-gates` ❌
- `rollback-on-failure` ✅

Evidence to save:

1. Health gate failure log line showing failed target/code
2. Rollback job lines restoring captured task definitions
3. Final ECS services stable wait success after rollback

Then restore benchmark URL(s) to valid endpoints and run once more to reconfirm green deploy.

---

## 5) CodeQL `action_required` remediation (repo/org admin)

Workflow:  
`https://github.com/Vansh-lab/vehicle-assessment---Vahannetra/actions/workflows/codeql.yml`

Observed blocker signature:

- workflow conclusion `action_required`
- `jobs.total_count = 0`

Admin checklist:

1. Repo Settings → Security → Code security and analysis:
   - enable CodeQL analysis / default setup or allow advanced setup workflow.
2. Org/Repo policies:
   - allow GitHub Advanced Security / code scanning where required by plan.
3. Actions policy:
   - verify `github/codeql-action` is allowed.
4. Pending approvals:
   - approve blocked workflow runs if policy requires manual approval.
5. Re-run CodeQL workflow.

Expected healthy result:

- Jobs are created for matrix languages (`javascript-typescript`, `python`)
- Workflow conclusion becomes `success` or `failure` with real job logs (not `action_required` with zero jobs)

---

## 6) Final closure criteria (single source)

- [ ] Success-path live ECS deploy evidence captured
- [ ] Rollback-path live recovery evidence captured
- [ ] Reconfirm final green deploy after rollback test
- [ ] CodeQL jobs actually execute (no zero-job `action_required`)
