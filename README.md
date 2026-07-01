# Opportunity Intelligence Engine (OIE)

Pipeline modular para descubrir oportunidades comerciales a partir de ofertas de trabajo.
API-first, con checkpointing, reanudación, observabilidad y ejecución determinista.

---

## Requisitos

- Python 3.12+
- pip

```bash
python -m pip install -r requirements.txt
```

---

## Variables de entorno

| Variable | Descripción | Ejemplo |
|---|---|---|
| `OIE_RUNS_PATH` | Directorio donde se guardan los runs | `runs` |
| `OIE_CONFIG_PATH` | Path al yaml de configuración base | `config/queries.yaml` |
| `SERPAPI_KEY` | API key de SerpAPI | |
| `OPENAI_API_KEY` | API key de OpenAI | |
| `APOLLO_API_KEY` | API key de Apollo | |
| `HUNTER_API_KEY` | API key de Hunter | |
| `HUBSPOT_BEARER_TOKEN` | Token de HubSpot | |

---

## Arrancar el servidor

```bash
source .env && \
OIE_RUNS_PATH=runs \
OIE_CONFIG_PATH=config/queries.yaml \
PYTHONPATH=src uvicorn oie.api.main:app --reload
```

URLs locales:

| | URL |
|---|---|
| API | http://127.0.0.1:8000 |
| Swagger UI | http://127.0.0.1:8000/docs |
| ReDoc | http://127.0.0.1:8000/redoc |
| OpenAPI JSON | http://127.0.0.1:8000/openapi.json |

---

## Pipeline ejecutable

```
collect_jobs → normalize_jobs → company_gate → urgency_gate → job_intelligence → domain_gate
```

| `stage_name` | Clase | Descripción |
|---|---|---|
| `collect_jobs` | `CollectJobsStage` | Recolecta ofertas de trabajo vía SerpAPI / static |
| `normalize_jobs` | `NormalizeJobsStage` | Normaliza y limpia los datos |
| `company_gate` | `JobGateStage` | Filtro AI: descarta staffing, competitors, job boards |
| `urgency_gate` | `UrgencyGateStage` | AI evalúa frescura y urgencia, filtra jobs >6 meses |
| `job_intelligence` | `JobIntelligenceStage` | Enriquecimiento AI: tech_stack, signals, seniority, domain |
| `domain_gate` | `CompanyGateStage` | Agrega por empresa y aplica filtros post-aggregate |

Stages no ejecutables individualmente retornan `{"detail": "Stage not executable"}`.

---

## Crear un run — UI

El usuario final solo necesita especificar **países** y **keywords**.
El resto de la configuración viene preconfigurada en el servidor vía `OIE_CONFIG_PATH`.

### Request mínimo para UI

```json
POST /runs

{
  "config": {
    "queries": [
      { "name": "React Remote", "q": "React remote" },
      { "name": "Backend Remote", "q": "backend engineer remote" },
      { "name": "Desarrollador Remoto", "q": "desarrollador remoto" }
    ],
    "sources": {
      "google_jobs": {
        "enabled": true,
        "location_mode": "matrix",
        "locations": ["United States", "Mexico", "Colombia"],
        "num_pages": 1
      },
      "discovery": {
        "linkedin_serpapi": { "enabled": true, "num_pages": 1 }
      }
    }
  }
}
```

### Nota sobre Google Jobs y geografía

Google Jobs devuelve resultados solo cuando la query coincide con el idioma del mercado:
- `"United States"`, `"Canada"` → queries en inglés
- `"Mexico"`, `"Colombia"`, `"Argentina"` → queries en español (`"desarrollador remoto"`, `"ingeniero remoto"`)

### Keywords disponibles (ejemplos del config base)

| Keyword | Query |
|---|---|
| Software Engineer | `software engineer remote` |
| Backend Engineer | `backend engineer remote` |
| Frontend Developer | `frontend developer remote` |
| Fullstack Engineer | `full stack engineer remote` |
| React | `React remote` |
| Angular | `Angular remote` |
| Node.js | `Node.js remote` |
| .NET | `.NET remote` |
| Cloud / AWS / Azure | `cloud remote`, `AWS remote`, `Azure remote` |
| Desarrollador (LATAM) | `desarrollador remoto` |
| Ingeniero (LATAM) | `ingeniero remoto` |

### Países disponibles (config base)

United States, Canada, Mexico, Colombia, Peru, Ecuador, Chile, Argentina, Panama, Guatemala

### Sin credenciales — desarrollo y pruebas

Usar `static_jobs` con `no_llm: true` para probar sin consumir APIs:

```json
POST /runs

{
  "config": {
    "collectors": {
      "static_jobs": {
        "jobs": [
          {
            "title": "Senior Python Engineer",
            "company": "Acme Corp",
            "location": "Remote",
            "job_url": "https://acme.com/jobs/1",
            "description": "We are hiring a senior Python engineer.",
            "detected_at": "2026-01-01"
          }
        ]
      }
    }
  },
  "flags": { "no_llm": true }
}
```

### Response de creación

```json
{
  "run_id": "20260701_020222_503c27bf",
  "status": "pending",
  "current_stage": null,
  "manifest_path": "runs/.../manifest.json",
  "configuration_path": "runs/.../configuration.json"
}
```

---

## Ejecutar el pipeline

### Pipeline completo

```
POST /runs/{run_id}/execute

{}
```

### Desde un stage específico

```json
{ "start_stage": "company_gate" }
```

### Rerun desde un stage (borra checkpoint anterior)

```json
{ "start_stage": "company_gate", "rerun": true }
```

### Response

```json
{
  "run_id": "20260701_020222_503c27bf",
  "status": "completed",
  "jobs_count": 42,
  "companies_count": 0,
  "leads_count": 0
}
```

---

## Ejecutar un stage individual

```
POST /runs/{run_id}/stages/{stage_name}/execute

{}
```

### Response

```json
{
  "stage": "collect_jobs",
  "status": "completed",
  "input_count": 42,
  "processed_count": 42,
  "output_count": 38,
  "rejected_count": 4,
  "errors": [],
  "processing_time_seconds": 1.23
}
```

---

## Monitorear un run

```
GET /runs                          — lista todos los runs
GET /runs/{run_id}                 — detalle completo del run
GET /runs/{run_id}/status          — status actual
GET /runs/{run_id}/stages          — estado de cada stage
GET /runs/{run_id}/errors          — errores del run
GET /runs/{run_id}/metrics         — métricas del run
GET /runs/{run_id}/configuration   — configuración persistida
```

### Response — lista de stages

```json
[
  { "stage": "collect_jobs",    "status": "completed" },
  { "stage": "normalize_jobs",  "status": "completed" },
  { "stage": "company_gate",    "status": "completed" },
  { "stage": "urgency_gate",    "status": "completed" },
  { "stage": "job_intelligence","status": "completed" },
  { "stage": "domain_gate",     "status": "completed" }
]
```

### Statuses posibles

| Status | Descripción |
|---|---|
| `pending` | No ejecutado |
| `running` | En ejecución |
| `completed` | Completado exitosamente |
| `partial_success` | Algunos items fallaron |
| `failed` | Error en ejecución |
| `cancelled` | Cancelado manualmente |
| `skipped` | Saltado |
| `waiting_for_user` | Esperando input |
| `company_pipeline_completed` | Pipeline de empresas completo |

---

## Inspeccionar artifacts de un stage

```
GET /runs/{run_id}/stages/{stage_name}/checkpoint   — snapshot de progreso
GET /runs/{run_id}/stages/{stage_name}/metrics      — tiempos y conteos
GET /runs/{run_id}/stages/{stage_name}/output       — registros producidos
GET /runs/{run_id}/stages/{stage_name}/errors       — errores del stage
GET /runs/{run_id}/stages/{stage_name}/summary      — resumen del stage
```

---

## Controlar un run

```
POST   /runs/{run_id}/cancel   — cancelar
POST   /runs/{run_id}/pause    — pausar
POST   /runs/{run_id}/resume   — reanudar
DELETE /runs/{run_id}          — eliminar
```

---

## Scheduling

```
POST   /runs/{run_id}/schedule        — crear schedule
PUT    /runs/{run_id}/schedule        — actualizar schedule
GET    /runs/{run_id}/schedule        — leer schedule
GET    /runs/{run_id}/schedule/status — estado del schedule
DELETE /runs/{run_id}/schedule        — eliminar schedule
```

### Ejemplo

```json
{
  "frequency": "weekly",
  "duration": "permanent",
  "scheduled_times": ["09:00"],
  "scheduled_days": ["monday", "wednesday"],
  "enabled": true
}
```

| Campo | Valores |
|---|---|
| `frequency` | `daily`, `weekly`, `monthly` |
| `duration` | `permanent`, `1 week`, `2 weeks`, `1 month` |
| `scheduled_times` | lista de `HH:MM` |
| `scheduled_days` | días de la semana opcionales |

---

## HubSpot Delivery

```
GET    /runs/{run_id}/hubspot-delivery   — leer config
PUT    /runs/{run_id}/hubspot-delivery   — crear/actualizar
DELETE /runs/{run_id}/hubspot-delivery   — eliminar
```

```json
{
  "hubspot_user_id": "123",
  "hubspot_owner_id": "456",
  "hubspot_company_id": "tekton-company-001",
  "hubspot_credentials_ref": "hubspot/tekton/juan"
}
```

`hubspot_bearer_token` nunca se devuelve en responses — se almacena pero no se expone.

---

## ICP Profiles

```
GET    /runs/{run_id}/icp-profiles                  — listar
POST   /runs/{run_id}/icp-profiles                  — agregar
PUT    /runs/{run_id}/icp-profiles                  — reemplazar todos
DELETE /runs/{run_id}/icp-profiles/{profile_id}     — eliminar uno
```

```json
{
  "profile_id": "asd-midmarket",
  "service_line": "ASD",
  "name": "ASD Midmarket",
  "enabled": true
}
```

---

## Artifacts disponibles por run

```
manifest.json              — estado del run
configuration.json         — config persistida
commercial_pipeline.csv    — pipeline comercial
commercial.md              — reporte comercial en Markdown
executive_summary.json     — resumen ejecutivo
run_analytics.json         — analytics completo
run_readiness_report.json  — reporte de readiness
run_metrics_summary.json   — métricas del run
top_opportunities_export   — top oportunidades
```

### Endpoints de outputs

```
GET /runs/{run_id}/outputs                  — lista outputs disponibles
GET /runs/{run_id}/outputs/{output_name}    — contenido del output
GET /runs/{run_id}/artifact-paths           — paths de artifacts del manifest
GET /runs/{run_id}/artifacts                — catálogo de artifacts
GET /runs/{run_id}/readiness                — reporte de readiness
GET /runs/{run_id}/analytics                — analytics
GET /runs/{run_id}/executive-summary        — resumen ejecutivo
GET /runs/{run_id}/commercial-report        — reporte comercial
GET /runs/{run_id}/commercial-pipeline      — pipeline comercial
GET /runs/{run_id}/top-opportunities        — top oportunidades
```

Formatos soportados: `csv`, `json`, `jsonl`, `markdown`, `text`

---

## Flags útiles

| Flag | Efecto |
|---|---|
| `no_llm: true` | Desactiva OpenAI — útil sin credenciales |
| `dry_run: true` | No ejecuta providers externos |

---

## Testing

```bash
PYTHONPATH=src pytest -q                          # suite completa
PYTHONPATH=src pytest tests/api -q                # solo API
PYTHONPATH=src pytest tests/api/test_runs.py -q   # solo runs
```

---

## Verificación rápida

```bash
PYTHONPATH=src python -m py_compile src/oie/api/routers/runs.py
PYTHONPATH=src pytest -q
```

---

## Estructura del repositorio

```
src/oie/
  api/
    main.py
    routers/runs.py
    schemas/runs.py
  orchestration/
    pipeline_stages.py
    stage_runner.py
    stage_base.py
    run_context.py
    run_manifest.py
    run_repository.py
    job_gate_stage.py
    urgency_gate_stage.py
    job_intelligence_stage.py
    company_gate_stage.py
  services/
    job_gate_service.py
    urgency_service.py
    job_intelligence_service.py
    hiring_signals_service.py
  collectors/
    static_jobs_collector.py
    google_jobs_collector.py
    linkedin_serpapi_collector.py
config/
  queries.yaml
tests/
  api/test_runs.py
  orchestration/test_stage_runner.py
```

---

## Git workflow

```bash
git status --short
git add <archivos>
git commit -m "<mensaje>"
git push
```
