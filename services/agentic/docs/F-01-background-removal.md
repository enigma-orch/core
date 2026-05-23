# F-01 — Background Removal

Single endpoint: user uploads a clothing image, receives a public URL pointing to
the processed PNG (transparent background) stored in RustFS.

---

## Endpoint

### `POST /api/v1/wardrobe/remove-background`

**Request** — `multipart/form-data`

| Field   | Type | Constraints                        |
|---------|------|------------------------------------|
| `image` | file | JPEG · PNG · WEBP · max 10 MB      |

**Responses**

| Status | Body                        | Notes                        |
|--------|-----------------------------|------------------------------|
| `200`  | `{ url: str }`              | RustFS URL to the result PNG |
| `413`  | `{ error, detail }`         | File exceeds 10 MB           |
| `415`  | `{ error, detail }`         | Unsupported content type     |
| `500`  | `{ error, detail }`         | Inference or upload failure  |

---

## File layout

```
app/
├── api/v1/wardrobe.py              # single route handler
├── services/background_removal.py  # inference + upload, fully in thread pool
├── schemas/wardrobe.py             # RemoveBackgroundResponse, ErrorResponse
├── infrastructure/storage.py       # RustFS/S3 client (boto3)
└── main.py                         # lifespan: loads model + ensures bucket
```

---

## Request lifecycle

```
POST /api/v1/wardrobe/remove-background
        │
        ▼
  validate content-type & size          (async, event loop)
        │
        ▼
  run_in_executor(_process_and_upload)  (thread pool, releases event loop)
        │
        ├── resize to ≤1024 px (LANCZOS)
        ├── rembg inference (u2net_cloth_seg, ONNX)
        ├── PNG encode (compress_level=1)
        └── upload to RustFS → return URL
        │
        ▼
  return { url }                        (async, event loop)
```

---

## Performance decisions

| Optimisation | Why |
|---|---|
| **Resize to max 1024 px** before inference | rembg infers at 320 px internally — applying the mask on a 4K image is where time is lost, not in the model |
| **`compress_level=1`** (PIL default is 6) | 3–5× faster PNG encode; file is ~15% larger, which is fine since storage is cheap |
| **Inference + upload in one executor call** | Avoids a second `run_in_executor` round-trip; the thread owns the full pipeline |
| **`ThreadPoolExecutor`** (not Process) | ONNX Runtime releases the GIL during inference, so threads are correct and cheaper than processes |
| **Workers = `min(4, cpu_count)`** | Prevents more concurrent ONNX sessions than cores; avoids thrashing |
| **CUDA provider → CPU fallback** | Zero-cost GPU acceleration if available; ORT auto-falls back |
| **`ensure_bucket` in lifespan** | Runs once at startup — not on every request |
| **Model loaded in lifespan executor** | Blocking ONNX load off the event loop, stored in `app.state.rembg_session` |

---

## Model

`u2net_cloth_seg` — clothing-specific segmentation. Downloaded by rembg on first
use to `~/.u2net/` and cached for subsequent runs.

| Model | Use case |
|---|---|
| `u2net` | General purpose |
| **`u2net_cloth_seg`** | **Clothing — used here** |
| `isnet-general-use` | High quality general |

---

## Error format

All non-2xx responses return:

```json
{ "error": "short reason", "detail": "optional longer message" }
```

Never raw Python exceptions.
