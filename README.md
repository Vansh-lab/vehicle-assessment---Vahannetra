# VahanNetra AI

**AI-first vehicle damage assessment, triage, garage pricing intelligence, and report automation platform.**

```text
 __      __      _                          _              
 \ \    / /__ _ | |__   __ _  _ _   _ _  __| |_ _ _ __ _  
  \ \/\/ / _` || / / | / _` || ' \ | ' \/ _` | '_/ _` | 
   \_/\_/\__,_||_\_\ |_|\__,_||_||_||_||_\__,_|_| \__,_| 
                       V A H A N N E T R A   A I
```

## Architecture
- Frontend: React + Vite (web workflow, inspection, advanced analytics)
- API: FastAPI async routers
- Worker: Celery (queue workloads, webhook delivery)
- DB: PostgreSQL/PostGIS
- Cache/Broker: Redis
- Storage: S3-compatible key layout (`jobs/{job_id}/...`)
- Reporting: ReportLab/jsPDF
- Integrations: VAHAN + insurer connector contracts with demo fallback

## Quick Start (5 commands)
```bash
cd FDA_Project
cp .env.example .env
chmod +x setup.sh
./setup.sh
make smoke
```

## Full API Endpoint Table
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | health/degraded check |
| POST | `/api/v1/analyze` | image/multi-image analysis |
| POST | `/api/v1/analyze/video` | video analysis with frame extraction |
| POST | `/api/v1/analyze/url` | URL based intake |
| GET | `/api/v1/results/{job_id}` | async job result |
| GET | `/api/v1/garages/nearby` | nearby garages + pricing + market comparison |
| GET | `/api/v1/garages/{garage_id}/pricing` | garage pricing details |
| GET | `/api/v1/garages/insurance-centers` | nearby insurance help centers |
| GET | `/api/v1/vehicles/lookup` | plate/VIN lookup (demo fallback) |
| POST | `/api/v1/vehicles` | register vehicle |
| GET | `/api/v1/vehicles/{vehicle_id}/history` | vehicle inspection history |
| POST | `/api/v1/webhooks/register` | register webhook |
| GET | `/api/v1/webhooks` | list webhooks |
| GET | `/api/v1/webhooks/dlq` | dead-letter events |
| GET | `/inspections/{id}/report.pdf` | professional report export |

## AI Models
| Model | Expected size | Typical role | Target inference |
|---|---:|---|---:|
| YOLOv9 (custom/compatible) | 80-200MB | damage detection | <500ms GPU / <8s CPU demo |
| EfficientNet-B4 | ~75MB | severity/class refinement | <250ms GPU |
| SAM2 (optional) | ~847MB | segmentation assist | <400ms GPU |

## Required API Keys (optional with graceful fallback)
- AWS S3 (artifact storage): https://aws.amazon.com/
- Anthropic Claude (LLM summaries): https://console.anthropic.com/
- Google Maps (optional): https://console.cloud.google.com/
- VAHAN enterprise (real): https://vahan.parivahan.gov.in/vahan4dashboard

## Model Weights Download
```bash
cd FDA_Project/vehicle_assessment_backend
python scripts/download_models.py --model all
```

## Environment Variables
See `FDA_Project/.env.example` for complete table including App, DB, Redis, AWS, Model, Claude, Google Maps, and VAHAN settings.

## Running Tests
```bash
cd FDA_Project
make test
```

## Production Deployment
- Docker stack: `FDA_Project/docker-compose.yml`
- Kubernetes manifests: `FDA_Project/k8s/`
- ECS/ECR deploy workflow: `.github/workflows/deploy-ecs.yml`
- Preflight runbook: `FDA_Project/aws-runtime-proof-runbook.md`

## Performance Benchmarks (target)
- Analyze queue API response: `<200ms`
- AI pipeline GPU: `<500ms`
- AI pipeline CPU demo: `<8s`
- PDF generation: `<3s`
- GPS + nearby services: `<1.5s`
- 30s video frame extraction: `<5s`

## Video Recording Guide
1. Open New Inspection screen.
2. Enable camera.
3. Record up to 30 seconds.
4. Preview and tap **Use this video**.
5. Submit for `/api/v1/analyze/video` pipeline.

## Pricing Comparison Feature
- Garage cards include INR min-max prices for scratch/dent/paint/major.
- Market average delta and verdict shown per row.
- Cheapest sorting uses detected damage type.

## CPU Fallback (No GPU)
- If model weights are missing/unavailable, detector fallback mode runs with safe defaults.
- External APIs unavailable => demo/mock data returned.
- S3 credentials unavailable => storage abstraction still returns key contracts.

## Honest “Cannot Build Instantly” Table
| Feature | Why not instant | Practical path |
|---|---|---|
| Real VAHAN enterprise | Government onboarding lead-time | Apply via VAHAN enterprise portal |
| Real insurer filing rails | Partner + compliance dependency | Contract insurer APIs + certifications |
| Fully trained proprietary weights | large labeled dataset + GPU training time | staged dataset + scheduled training pipeline |

## License
MIT
