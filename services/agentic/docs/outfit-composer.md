# Outfit Composer API

## `POST /api/v1/wardrobe/outfits/compose`

Generates a virtual try-on outfit image by dressing the user in selected wardrobe items. The AI replaces the user's clothing in the provided photo with the selected items and returns the generated outfit with full metadata.

---

## Request

**Content-Type:** `application/json`

### Body

| Field | Type | Required | Description |
|---|---|---|---|
| `item_ids` | `UUID[]` | ✅ | IDs of wardrobe items to wear. Must be non-empty. Items must already exist (uploaded via `/wardrobe/upload`). |
| `user_image_url` | `string` | ✅ | Full URL of the user's photo. The AI uses this as the base — face, body, and pose are preserved. |

### Example

```json
{
  "item_ids": [
    "d6005bb2-d9dd-49c7-913a-3dc0e4a0c6e6",
    "215c1500-f771-4909-ad57-e10c5b15a72e"
  ],
  "user_image_url": "https://your-server.com/api/v1/wardrobe/files/wardrobe/no-bg/efdc7555.png"
}
```

---

## Response

**Status:** `201 Created`
**Content-Type:** `application/json`

### Top-level fields

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | `UUID` | ❌ | Outfit ID |
| `user_id` | `UUID` | ❌ | Owner user ID |
| `name` | `string` | ✅ | Auto-generated outfit name (e.g. `"White Tee + Navy Jeans + White Sneakers"`) |
| `preview_image_url` | `string` | ✅ | URL of the generated try-on image. Display this as the outfit card cover. |
| `occasion` | `string` | ✅ | `casual` · `smart-casual` · `formal` · `streetwear` · `activewear` · `party` |
| `season` | `string` | ✅ | `spring` · `summer` · `fall` · `winter` · `all-season` |
| `vibe` | `string` | ✅ | Style vibe derived from the items (e.g. `"clean minimal"`) |
| `mood` | `string` | ✅ | Mood tag (e.g. `"confident"`) |
| `source` | `string` | ❌ | Always `"ai_generated"` for this endpoint |
| `items` | `Item[]` | ❌ | Full data of every item included in the outfit (see below) |
| `created_at` | `ISO 8601` | ❌ | Creation timestamp |
| `updated_at` | `ISO 8601` | ❌ | Last update timestamp |

### `items[]` — each item object

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | `UUID` | ❌ | Item ID |
| `user_id` | `UUID` | ❌ | Owner user ID |
| `clean_image_url` | `string` | ✅ | Background-removed item image. Use this for item thumbnails. |
| `original_image_url` | `string` | ✅ | Original uploaded image (with background) |
| `name` | `string` | ✅ | Descriptive item name (e.g. `"Slim-fit washed navy denim jeans"`) |
| `category` | `string` | ✅ | `top` · `bottom` · `dress` · `outerwear` · `shoes` · `bag` · `accessory` · `jewellery` |
| `subcategory` | `string` | ✅ | Specific type (e.g. `"slim-fit straight-leg denim jeans"`) |
| `brand` | `string` | ✅ | Brand name if detected, otherwise `null` |
| `colors` | `string[]` | ✅ | List of color descriptors (e.g. `["washed navy blue"]`) |
| `season` | `string[]` | ✅ | Applicable seasons (e.g. `["spring", "fall"]`) |
| `occasion` | `string` | ✅ | Same enum as outfit-level occasion |
| `style_tags` | `string[]` | ✅ | Style keywords (e.g. `["denim", "minimalist", "slim"]`) |
| `pattern` | `string` | ✅ | `solid` · `striped` · `plaid` · `floral` · `geometric` · `animal` · `graphic` — or `null` |
| `vibe` | `string` | ✅ | Style vibe (e.g. `"clean minimal"`) |
| `mood` | `string` | ✅ | Mood tag (e.g. `"confident"`) |
| `size` | `string` | ✅ | Estimated size (e.g. `"estimated medium"`) |
| `enriched` | `boolean` | ❌ | Whether the item has been enriched with extra data |
| `enrichment_data` | `object` | ✅ | Extra enrichment payload, free-form |
| `created_at` | `ISO 8601` | ❌ | |
| `updated_at` | `ISO 8601` | ❌ | |

> **Note:** `embedding` is intentionally excluded from `items[]` in this response — it is an internal vector and not needed by the client.

### Example Response

```json
{
  "id": "a1b2c3d4-0000-0000-0000-000000000001",
  "user_id": "0e3db907-7d2b-420c-a20e-3b1d0b74ced0",
  "name": "White Tee + Navy Jeans + White Sneakers",
  "preview_image_url": "http://your-server.com/api/v1/wardrobe/files/wardrobe/outfits/abc123.png",
  "occasion": "casual",
  "season": "spring",
  "vibe": "clean minimal",
  "mood": "confident",
  "source": "ai_generated",
  "created_at": "2026-05-22T22:10:00Z",
  "updated_at": "2026-05-22T22:10:00Z",
  "items": [
    {
      "id": "d6005bb2-d9dd-49c7-913a-3dc0e4a0c6e6",
      "user_id": "0e3db907-7d2b-420c-a20e-3b1d0b74ced0",
      "clean_image_url": "http://your-server.com/api/v1/wardrobe/files/wardrobe/no-bg/abc.png",
      "original_image_url": "http://your-server.com/api/v1/wardrobe/files/wardrobe/original/abc.png",
      "name": "Oversized off-white cotton tee",
      "category": "top",
      "subcategory": "oversized crew-neck tee",
      "brand": null,
      "colors": ["off-white"],
      "season": ["spring", "summer"],
      "occasion": "casual",
      "style_tags": ["oversized", "minimalist", "cotton"],
      "pattern": "solid",
      "vibe": "clean minimal",
      "mood": "relaxed",
      "size": "estimated large",
      "enriched": false,
      "enrichment_data": null,
      "created_at": "2026-05-20T10:00:00Z",
      "updated_at": "2026-05-20T10:00:00Z"
    }
  ]
}
```

---

## Error Responses

| Status | `error` | Cause |
|---|---|---|
| `400` | `item_ids must not be empty` | Request sent with an empty `item_ids` array |
| `400` | `None of the items have a processed image` | All matched items lack a `clean_image_url` |
| `404` | `Items not found: [...]` | One or more `item_ids` do not exist in the database |
| `500` | `Image generation failed` | wan2.7-image API error |
| `500` | `Image storage failed` | RustFS upload error |
| `500` | `Embedding failed` | Embedding service error |

---

## Integration Notes

- **`user_image_url`** should be the background-removed photo of the user (returned from `POST /wardrobe/remove-background`). A plain background produces significantly better try-on results.
- **Items must be uploaded first** via `POST /wardrobe/upload` before their IDs can be used here.
- **Generation is slow** (10–30 seconds). Show a loading/processing state in the UI while polling or awaiting the response.
- **`preview_image_url`** is the main asset to display — render it as the outfit card image.
- **`clean_image_url`** on each item is the background-removed thumbnail — use it for the item chips/list within the outfit detail view.
