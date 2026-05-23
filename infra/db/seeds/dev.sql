BEGIN;

INSERT INTO users_shadow (id, display_name)
VALUES ('11111111-1111-1111-1111-111111111111', 'DRIP Demo User')
ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name, updated_at = now();

INSERT INTO stores (id, name, slug, website_url)
VALUES
    ('22222222-2222-2222-2222-222222222201', 'Zara', 'zara', 'https://www.zara.com'),
    ('22222222-2222-2222-2222-222222222202', 'Amazon Fashion', 'amazon', 'https://www.amazon.com/fashion'),
    ('22222222-2222-2222-2222-222222222203', 'Shein', 'shein', 'https://www.shein.com'),
    ('22222222-2222-2222-2222-222222222204', 'AliExpress', 'aliexpress', 'https://www.aliexpress.com')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, slug = EXCLUDED.slug, website_url = EXCLUDED.website_url, updated_at = now();

INSERT INTO taxonomy_tags (id, tag_type, slug, label)
VALUES
    ('aaaaaaaa-0000-0000-0000-000000000001', 'color', 'black', 'Black'),
    ('aaaaaaaa-0000-0000-0000-000000000002', 'color', 'white', 'White'),
    ('aaaaaaaa-0000-0000-0000-000000000003', 'color', 'denim-blue', 'Denim Blue'),
    ('aaaaaaaa-0000-0000-0000-000000000004', 'style', 'streetwear', 'Streetwear'),
    ('aaaaaaaa-0000-0000-0000-000000000005', 'style', 'minimal', 'Minimal'),
    ('aaaaaaaa-0000-0000-0000-000000000006', 'occasion', 'casual-dinner', 'Casual Dinner'),
    ('aaaaaaaa-0000-0000-0000-000000000007', 'occasion', 'class', 'Class'),
    ('aaaaaaaa-0000-0000-0000-000000000008', 'vibe', 'high-energy', 'High Energy'),
    ('aaaaaaaa-0000-0000-0000-000000000009', 'season', 'spring', 'Spring'),
    ('aaaaaaaa-0000-0000-0000-000000000010', 'season', 'fall', 'Fall')
ON CONFLICT (tag_type, slug) DO UPDATE SET label = EXCLUDED.label;

INSERT INTO wardrobe_items (
    id, user_id, category, name, brand, size, price_cents, currency, purchased_from, notes, background_removal_status, wear_count
)
VALUES
    ('44444444-4444-4444-4444-444444444401', '11111111-1111-1111-1111-111111111111', 'top', 'White oversized tee', 'Uniqlo', 'M', 2490, 'USD', 'Mall', 'Clean base for layered outfits', 'processed', 4),
    ('44444444-4444-4444-4444-444444444402', '11111111-1111-1111-1111-111111111111', 'bottom', 'Black straight jeans', 'Levi''s', '32', 8990, 'USD', 'Levi''s', 'Works with streetwear and minimal fits', 'processed', 7),
    ('44444444-4444-4444-4444-444444444403', '11111111-1111-1111-1111-111111111111', 'shoes', 'White low sneakers', 'Adidas', '42', 7490, 'USD', 'Adidas', 'Safe daily sneaker', 'processed', 9),
    ('44444444-4444-4444-4444-444444444404', '11111111-1111-1111-1111-111111111111', 'outerwear', 'Washed denim jacket', 'Pull&Bear', 'M', 6990, 'USD', 'Pull&Bear', 'Good for spring nights', 'processed', 2)
ON CONFLICT (id) DO UPDATE SET
    category = EXCLUDED.category,
    name = EXCLUDED.name,
    brand = EXCLUDED.brand,
    size = EXCLUDED.size,
    price_cents = EXCLUDED.price_cents,
    notes = EXCLUDED.notes,
    updated_at = now(),
    deleted_at = NULL;

INSERT INTO store_products (
    id, store_id, external_id, title, brand, category, description, product_url, price_cents, currency, available
)
VALUES
    ('33333333-3333-3333-3333-333333333301', '22222222-2222-2222-2222-222222222201', 'zara-bomber-001', 'Textured black bomber jacket', 'Zara', 'outerwear', 'A structured black bomber for streetwear looks.', 'https://www.zara.com/demo/textured-black-bomber', 7990, 'USD', true),
    ('33333333-3333-3333-3333-333333333302', '22222222-2222-2222-2222-222222222202', 'amazon-sneaker-001', 'Chunky white fashion sneakers', 'Amazon Essentials', 'shoes', 'Budget-friendly white sneakers with bold silhouette.', 'https://www.amazon.com/demo/chunky-white-sneakers', 4890, 'USD', true),
    ('33333333-3333-3333-3333-333333333303', '22222222-2222-2222-2222-222222222203', 'shein-cargo-001', 'Relaxed black cargo pants', 'Shein', 'bottom', 'Relaxed cargos for high-energy music vibes.', 'https://www.shein.com/demo/relaxed-black-cargo-pants', 3290, 'USD', true),
    ('33333333-3333-3333-3333-333333333304', '22222222-2222-2222-2222-222222222204', 'ali-chain-001', 'Silver layered chain accessory', 'AliExpress', 'accessory', 'Low-cost accessory to complete a market outfit.', 'https://www.aliexpress.com/demo/silver-layered-chain', 1290, 'USD', true)
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    brand = EXCLUDED.brand,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    product_url = EXCLUDED.product_url,
    price_cents = EXCLUDED.price_cents,
    available = EXCLUDED.available,
    updated_at = now(),
    deleted_at = NULL;

INSERT INTO media_assets (id, owner_type, owner_id, asset_type, cloudinary_public_id, url, width, height, processing_status)
VALUES
    ('55555555-5555-5555-5555-555555555501', 'wardrobe_item', '44444444-4444-4444-4444-444444444401', 'processed', 'drip/demo/white-tee', 'https://res.cloudinary.com/demo/image/upload/drip-white-tee.png', 900, 1200, 'processed'),
    ('55555555-5555-5555-5555-555555555502', 'wardrobe_item', '44444444-4444-4444-4444-444444444402', 'processed', 'drip/demo/black-jeans', 'https://res.cloudinary.com/demo/image/upload/drip-black-jeans.png', 900, 1200, 'processed'),
    ('55555555-5555-5555-5555-555555555503', 'store_product', '33333333-3333-3333-3333-333333333301', 'preview', 'drip/demo/zara-bomber', 'https://res.cloudinary.com/demo/image/upload/drip-zara-bomber.png', 900, 1200, 'processed'),
    ('55555555-5555-5555-5555-555555555504', 'store_product', '33333333-3333-3333-3333-333333333304', 'preview', 'drip/demo/ali-chain', 'https://res.cloudinary.com/demo/image/upload/drip-ali-chain.png', 900, 1200, 'processed')
ON CONFLICT (id) DO NOTHING;

INSERT INTO entity_tags (entity_type, entity_id, tag_id)
VALUES
    ('wardrobe_item', '44444444-4444-4444-4444-444444444401', 'aaaaaaaa-0000-0000-0000-000000000002'),
    ('wardrobe_item', '44444444-4444-4444-4444-444444444401', 'aaaaaaaa-0000-0000-0000-000000000005'),
    ('wardrobe_item', '44444444-4444-4444-4444-444444444402', 'aaaaaaaa-0000-0000-0000-000000000001'),
    ('wardrobe_item', '44444444-4444-4444-4444-444444444402', 'aaaaaaaa-0000-0000-0000-000000000004'),
    ('store_product', '33333333-3333-3333-3333-333333333301', 'aaaaaaaa-0000-0000-0000-000000000001'),
    ('store_product', '33333333-3333-3333-3333-333333333301', 'aaaaaaaa-0000-0000-0000-000000000004'),
    ('store_product', '33333333-3333-3333-3333-333333333304', 'aaaaaaaa-0000-0000-0000-000000000008')
ON CONFLICT DO NOTHING;

INSERT INTO outfits (id, user_id, name, outfit_type, occasion, source, explanation, score)
VALUES
    ('66666666-6666-6666-6666-666666666601', '11111111-1111-1111-1111-111111111111', 'Owned streetwear base', 'owned', 'casual-dinner', 'manual', 'White tee, black jeans, and white sneakers match a minimal streetwear vibe.', 0.88),
    ('66666666-6666-6666-6666-666666666602', '11111111-1111-1111-1111-111111111111', 'Hybrid night-out layer', 'hybrid', 'casual-dinner', 'manual', 'Use owned jeans and sneakers, then add the Zara bomber for a stronger high-energy look.', 0.93)
ON CONFLICT (id) DO UPDATE SET explanation = EXCLUDED.explanation, score = EXCLUDED.score, updated_at = now(), deleted_at = NULL;

INSERT INTO outfit_components (id, outfit_id, slot, position, wardrobe_item_id, store_product_id)
VALUES
    ('77777777-7777-7777-7777-777777777701', '66666666-6666-6666-6666-666666666601', 'top', 1, '44444444-4444-4444-4444-444444444401', NULL),
    ('77777777-7777-7777-7777-777777777702', '66666666-6666-6666-6666-666666666601', 'bottom', 2, '44444444-4444-4444-4444-444444444402', NULL),
    ('77777777-7777-7777-7777-777777777703', '66666666-6666-6666-6666-666666666601', 'shoes', 3, '44444444-4444-4444-4444-444444444403', NULL),
    ('77777777-7777-7777-7777-777777777704', '66666666-6666-6666-6666-666666666602', 'bottom', 1, '44444444-4444-4444-4444-444444444402', NULL),
    ('77777777-7777-7777-7777-777777777705', '66666666-6666-6666-6666-666666666602', 'outerwear', 2, NULL, '33333333-3333-3333-3333-333333333301')
ON CONFLICT (id) DO NOTHING;

INSERT INTO swipe_sessions (id, user_id, context, status)
VALUES (
    '88888888-8888-8888-8888-888888888801',
    '11111111-1111-1111-1111-111111111111',
    '{"music_vibe":"high-energy streetwear","calendar_event":"casual dinner"}',
    'active'
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO swipe_events (id, session_id, user_id, outfit_id, store_product_id, action)
VALUES
    ('99999999-9999-9999-9999-999999999901', '88888888-8888-8888-8888-888888888801', '11111111-1111-1111-1111-111111111111', '66666666-6666-6666-6666-666666666602', NULL, 'right'),
    ('99999999-9999-9999-9999-999999999902', '88888888-8888-8888-8888-888888888801', '11111111-1111-1111-1111-111111111111', NULL, '33333333-3333-3333-3333-333333333304', 'wishlist')
ON CONFLICT (id) DO NOTHING;

INSERT INTO seed_runs (name, checksum)
VALUES ('backend-dev-demo-v1', '20260522-backend-dev-demo-v1')
ON CONFLICT (name) DO UPDATE SET checksum = EXCLUDED.checksum, created_at = now();

COMMIT;
