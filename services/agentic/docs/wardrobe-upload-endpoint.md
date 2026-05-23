# Wardrobe Upload Endpoint

## Overview

Upload one or more clothing item images to the Drip wardrobe service. For each image the backend removes the background, runs AI vision analysis, generates a vector embedding, and persists an `Item` record. The response returns the saved item data (without embeddings) alongside both the original and background-removed image URLs.

---

## Request

**Method:** `POST`

**URL:** `http://localhost:8000/api/v1/wardrobe/upload`

**Content-Type:** `multipart/form-data`

**Form field:** `images` — one or more files, repeated for each image.

Accepted file types: `image/jpeg`, `image/png`, `image/webp`  
Maximum file size: 10 MB per image

### curl example

```bash
curl -X POST http://localhost:8000/api/v1/wardrobe/upload \
  -F "images=@shirt.jpg" \
  -F "images=@pants.png"
```

---

## Response

**Status:** `200 OK`

**Content-Type:** `application/json`

Returns a JSON **array** — one object per uploaded image, in the same order as the upload.

### Response object fields

| Field | Type | Description |
|---|---|---|
| `id` | `string (UUID)` | Unique item ID |
| `name` | `string \| null` | AI-generated item name |
| `category` | `string \| null` | top, bottom, dress, shoes, bag, outerwear, accessory, jewellery |
| `subcategory` | `string \| null` | Specific type e.g. crewneck sweatshirt |
| `brand` | `string \| null` | Brand if clearly visible, otherwise null |
| `colors` | `string[] \| null` | List of detected colors |
| `season` | `string[] \| null` | Applicable seasons |
| `occasion` | `string \| null` | casual, smart-casual, formal, streetwear, activewear, party |
| `style_tags` | `string[] \| null` | Style descriptors |
| `pattern` | `string \| null` | solid, striped, plaid, floral, geometric, animal, graphic |
| `vibe` | `string \| null` | Style vibe |
| `mood` | `string \| null` | Mood descriptor |
| `size` | `string \| null` | Estimated size |
| `enrichment_data` | `object \| null` | `{ "confidence": float, "search_query": string }` |
| `original_image_url` | `string \| null` | URL of the original uploaded image |
| `clean_image_url` | `string \| null` | URL of the background-removed PNG |
| `created_at` | `string (ISO 8601)` | Timestamp of record creation |

### Example response

```json
[
  {
    "id": "677ed257-a08f-4585-be54-1b298afbe820",
    "name": "Olive Green Cargo Pants",
    "category": "bottom",
    "subcategory": "cargo trousers",
    "brand": null,
    "colors": ["olive green"],
    "season": ["spring", "fall"],
    "occasion": "casual",
    "style_tags": ["utility", "streetwear"],
    "pattern": "solid",
    "vibe": "urban utility",
    "mood": "grounded",
    "size": "estimated medium",
    "enrichment_data": {
      "confidence": 0.97,
      "search_query": "men's olive green wide leg cargo pants"
    },
    "original_image_url": "http://localhost:8000/api/v1/wardrobe/files/wardrobe/original/ee19decc.jpg",
    "clean_image_url": "http://localhost:8000/api/v1/wardrobe/files/wardrobe/no-bg/026357ad.png",
    "created_at": "2026-05-22T18:00:00Z"
  }
]
```

---

## Error responses

| Status | Meaning |
|---|---|
| `400` | No images provided, empty file, or file exceeds 10 MB |
| `415` | Unsupported file type (not JPEG, PNG, or WEBP) |
| `500` | AI detection, background removal, or storage failure |

```json
{ "error": "Processing failed", "detail": "<reason>" }
```
