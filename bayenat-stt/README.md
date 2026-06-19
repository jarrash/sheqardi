# Bayenat / بيّنات — Audio Evidence STT MVP

> تحويل الأدلة الصوتية إلى نصوص موثقة قابلة للمراجعة باستخدام عدّة محركات تحويل صوت إلى نص ومقارنة نتائجها.
>
> Turn audio evidence into **verifiable, reviewable** transcripts using multiple
> speech-to-text engines, cross-engine comparison, and a chain-of-custody report.

This is an **MVP** — not a final forensic product — but it is structured so the
forensic features (diarization, PDF reports, blockchain timestamping, auth/RBAC,
audit logs, multi-tenant SaaS, Arabic UI) can be layered on cleanly.

---

## How it works

```
upload audio ──> validate + save ──> sha256(audio)
            ──> [ faster-whisper | whisper | third-engine ]  (fail-soft, concurrent)
            ──> compare transcripts (similarity + agreement)
            ──> pick final transcript ──> sha256(final text)
            ──> write JSON chain-of-custody report + SQLite record
            ──> return JSON
```

- **Three engines**, each behind a common interface (`app/engines/`). A failing
  engine never aborts the request as long as another engine succeeds.
- **Final transcript** is the one with the highest *mean agreement* with the
  others (ties break toward the longer/more complete text) — deliberately **not**
  "just the longest".
- Every run produces a **JSON report** under `app/storage/reports/` and a row in
  SQLite for later audit.

---

## Project structure

```
bayenat-stt/
├── app/
│   ├── main.py                 # FastAPI app + lifespan (storage + DB init)
│   ├── config.py               # Pydantic settings (env-driven)
│   ├── api/routes.py           # POST /api/v1/transcribe, GET /health
│   ├── engines/                # base + faster-whisper + whisper + third (placeholder)
│   ├── services/               # audio, hash, transcription, comparison, report
│   ├── models/                 # schemas (Pydantic) + database (SQLite)
│   └── storage/                # uploads/ and reports/
└── tests/                      # hash, comparison, API (engines stubbed)
```

---

## Quick start

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open the interactive Swagger UI and try the endpoint:

```
http://127.0.0.1:8000/docs
```

> **Tip — avoid the multi-GB download while testing.** The default models are
> `large-v3`. For a quick local run set smaller models first:
>
> ```bash
> export FASTER_WHISPER_MODEL=small
> export WHISPER_MODEL=small
> ```
>
> The heavy ML libraries (`faster-whisper`, `openai-whisper`, `torch`) are only
> needed for **real** transcription. The API starts and the **tests pass**
> without them — engines load lazily and tests stub them out.

---

## API

### `POST /api/v1/transcribe`

Multipart form fields:

| Field         | Type   | Required | Default | Notes                          |
|---------------|--------|----------|---------|--------------------------------|
| `file`        | file   | yes      | —       | `mp3`, `wav`, or `m4a` (≤ 200 MB) |
| `language`    | string | no       | `ar`    | language code                  |
| `case_id`     | string | no       | —       | metadata                       |
| `evidence_id` | string | no       | —       | metadata                       |

Example response:

```json
{
  "case_id": "C-1",
  "evidence_id": "E-9",
  "audio_hash": "sha256...",
  "final_text_hash": "sha256...",
  "final_transcript": "...",
  "confidence_score": 87.5,
  "agreement_score": 0.875,
  "engines": [
    { "engine_name": "faster-whisper-large-v3", "language": "ar", "text": "...", "processing_time_seconds": 12.4 },
    { "engine_name": "whisper-large-v3", "language": "ar", "text": "...", "processing_time_seconds": 20.1 },
    { "engine_name": "third-engine", "language": "ar", "text": "...", "processing_time_seconds": 0.0 }
  ],
  "report_path": "app/storage/reports/....json"
}
```

`curl` example:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/transcribe \
  -F "file=@evidence.wav" \
  -F "language=ar" \
  -F "case_id=C-1" \
  -F "evidence_id=E-9"
```

### `GET /health`

Liveness probe.

---

## Configuration

All settings are environment-driven (see `.env.example`):

| Variable                | Default      | Description                                    |
|-------------------------|--------------|------------------------------------------------|
| `DEFAULT_LANGUAGE`      | `ar`         | default language code                          |
| `MAX_FILE_SIZE_MB`      | `200`        | upload size limit                              |
| `ALLOWED_EXTENSIONS`    | `mp3,wav,m4a`| accepted audio extensions                      |
| `FASTER_WHISPER_MODEL`  | `large-v3`   | faster-whisper model size                      |
| `WHISPER_MODEL`         | `large-v3`   | openai-whisper model size                      |
| `DEVICE`                | `auto`       | `auto` / `cpu` / `cuda`                         |
| `THIRD_ENGINE_ENABLED`  | `false`      | enable the third (placeholder) engine          |

---

## The third engine

`app/engines/third_engine.py` is a **safe placeholder**: while disabled it
returns a "skipped" result and never breaks a request. To plug in a real backend
(e.g. **NVIDIA Parakeet**, a **HuggingFace** Arabic model, or an external **STT
API**), implement `_transcribe` and set `THIRD_ENGINE_ENABLED=true`.

---

## Testing

```bash
pytest
```

Tests cover hashing, the comparison/selection logic (including the tie-break and
single/zero-engine edge cases), and the full API flow with engines stubbed — so
no models are downloaded.

---

## Docker

```bash
docker build -t bayenat-stt .
docker run -p 8000:8000 bayenat-stt
```

---

## Roadmap (future, out of scope for this MVP)

- Speaker diarization
- PDF report generation
- Blockchain timestamping
- User authentication & Role-Based Access Control
- Audit logs
- Evidence chain-of-custody dashboard
- Arabic UI dashboard
- SaaS multi-tenant architecture
