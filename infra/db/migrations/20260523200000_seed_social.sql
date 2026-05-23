-- migrate:up

-- ── Seed users ──────────────────────────────────────────────────────────────
INSERT INTO users (id, email, display_name, avatar_url, mood, location, style_identity, created_at, updated_at)
VALUES
  ('a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1',
   'amira.benali@example.com', 'Amira Benali',
   'https://i.pravatar.cc/300?img=47',
   'HAPPY', 'Algiers', 'Street Chic', now(), now()),

  ('b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2',
   'yassine.kaci@example.com', 'Yassine Kaci',
   'https://i.pravatar.cc/300?img=12',
   'FOCUSED', 'Oran', 'Minimalist', now(), now()),

  ('c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3',
   'nadia.ouhaddou@example.com', 'Nadia Ouhaddou',
   'https://i.pravatar.cc/300?img=32',
   'CALM', 'Constantine', 'Elegant', now(), now()),

  ('d4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4',
   'khalil.mansouri@example.com', 'Khalil Mansouri',
   'https://i.pravatar.cc/300?img=15',
   'ENERGETIC', 'Algiers', 'Luxury Casual', now(), now()),

  ('e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5',
   'sonia.rahal@example.com', 'Sonia Rahal',
   'https://i.pravatar.cc/300?img=44',
   'RELAXED', 'Tlemcen', 'Boho Chic', now(), now())
ON CONFLICT (id) DO NOTHING;

-- ── Seed outfits ─────────────────────────────────────────────────────────────
INSERT INTO outfits (id, user_id, name, preview_image_url, occasion, season, vibe, mood, source, wear_count, created_at, updated_at)
VALUES
  ('f1000001-0000-0000-0000-000000000001',
   'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1',
   'Street Glow', 'https://picsum.photos/seed/amira-street/400/600',
   'casual', 'spring', 'bold', 'HAPPY', 'manual', 3, now() - interval '2 days', now()),

  ('f1000002-0000-0000-0000-000000000002',
   'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1',
   'Evening Edit', 'https://picsum.photos/seed/amira-evening/400/600',
   'evening', 'summer', 'chic', 'CALM', 'manual', 1, now() - interval '5 days', now()),

  ('f2000001-0000-0000-0000-000000000001',
   'b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2',
   'Clean Lines', 'https://picsum.photos/seed/yassine-clean/400/600',
   'work', 'all_season', 'minimal', 'FOCUSED', 'manual', 7, now() - interval '1 day', now()),

  ('f2000002-0000-0000-0000-000000000002',
   'b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2',
   'Weekend Ease', 'https://picsum.photos/seed/yassine-weekend/400/600',
   'casual', 'spring', 'relaxed', 'RELAXED', 'manual', 2, now() - interval '6 days', now()),

  ('f3000001-0000-0000-0000-000000000001',
   'c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3',
   'Garden Party', 'https://picsum.photos/seed/nadia-garden/400/600',
   'social', 'spring', 'feminine', 'HAPPY', 'manual', 4, now() - interval '3 days', now()),

  ('f3000002-0000-0000-0000-000000000002',
   'c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3',
   'Corporate Edge', 'https://picsum.photos/seed/nadia-corp/400/600',
   'work', 'fall', 'power', 'FOCUSED', 'manual', 5, now() - interval '8 days', now()),

  ('f4000001-0000-0000-0000-000000000001',
   'd4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4',
   'Rooftop Night', 'https://picsum.photos/seed/khalil-rooftop/400/600',
   'evening', 'summer', 'luxury', 'ENERGETIC', 'manual', 6, now() - interval '1 day', now()),

  ('f4000002-0000-0000-0000-000000000002',
   'd4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4',
   'Daytime Sharp', 'https://picsum.photos/seed/khalil-day/400/600',
   'casual', 'fall', 'sharp', 'FOCUSED', 'manual', 2, now() - interval '9 days', now()),

  ('f5000001-0000-0000-0000-000000000001',
   'e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5',
   'Desert Bloom', 'https://picsum.photos/seed/sonia-desert/400/600',
   'casual', 'summer', 'boho', 'HAPPY', 'manual', 3, now() - interval '4 days', now()),

  ('f5000002-0000-0000-0000-000000000002',
   'e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5',
   'Market Day', 'https://picsum.photos/seed/sonia-market/400/600',
   'casual', 'spring', 'earthy', 'RELAXED', 'manual', 1, now() - interval '11 days', now())
ON CONFLICT (id) DO NOTHING;

-- ── Outfit shares (all public) ────────────────────────────────────────────────
INSERT INTO outfit_shares (id, outfit_id, owner_id, visibility, created_at, updated_at)
VALUES
  (gen_random_uuid(), 'f1000001-0000-0000-0000-000000000001', 'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1', 'PUBLIC', now(), now()),
  (gen_random_uuid(), 'f1000002-0000-0000-0000-000000000002', 'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1', 'PUBLIC', now(), now()),
  (gen_random_uuid(), 'f2000001-0000-0000-0000-000000000001', 'b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2', 'PUBLIC', now(), now()),
  (gen_random_uuid(), 'f2000002-0000-0000-0000-000000000002', 'b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2', 'PUBLIC', now(), now()),
  (gen_random_uuid(), 'f3000001-0000-0000-0000-000000000001', 'c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3', 'PUBLIC', now(), now()),
  (gen_random_uuid(), 'f3000002-0000-0000-0000-000000000002', 'c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3', 'PUBLIC', now(), now()),
  (gen_random_uuid(), 'f4000001-0000-0000-0000-000000000001', 'd4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4', 'PUBLIC', now(), now()),
  (gen_random_uuid(), 'f4000002-0000-0000-0000-000000000002', 'd4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4', 'PUBLIC', now(), now()),
  (gen_random_uuid(), 'f5000001-0000-0000-0000-000000000001', 'e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5', 'PUBLIC', now(), now()),
  (gen_random_uuid(), 'f5000002-0000-0000-0000-000000000002', 'e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5', 'PUBLIC', now(), now());

-- ── Follows ──────────────────────────────────────────────────────────────────
INSERT INTO follows (follower_id, followee_id, created_at)
VALUES
  ('a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1', 'b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2', now()),
  ('a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1', 'c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3', now()),
  ('b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2', 'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1', now()),
  ('b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2', 'd4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4', now()),
  ('c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3', 'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1', now()),
  ('c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3', 'e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5', now()),
  ('d4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4', 'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1', now()),
  ('d4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4', 'b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2', now()),
  ('e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5', 'c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3', now()),
  ('e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5', 'd4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4', now())
ON CONFLICT DO NOTHING;

-- ── Outbox events (so Neo4j projector picks up seed follows immediately) ──────
INSERT INTO social_outbox (event_type, payload)
VALUES
  ('follow.created', '{"follower_id":"a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1","followee_id":"b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2"}'),
  ('follow.created', '{"follower_id":"a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1","followee_id":"c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3"}'),
  ('follow.created', '{"follower_id":"b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2","followee_id":"a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1"}'),
  ('follow.created', '{"follower_id":"b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2","followee_id":"d4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4"}'),
  ('follow.created', '{"follower_id":"c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3","followee_id":"a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1"}'),
  ('follow.created', '{"follower_id":"c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3","followee_id":"e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5"}'),
  ('follow.created', '{"follower_id":"d4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4","followee_id":"a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1"}'),
  ('follow.created', '{"follower_id":"d4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4","followee_id":"b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2"}'),
  ('follow.created', '{"follower_id":"e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5","followee_id":"c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3"}'),
  ('follow.created', '{"follower_id":"e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5","followee_id":"d4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4"}'),
  ('outfit.shared', '{"outfit_id":"f1000001-0000-0000-0000-000000000001","owner_id":"a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1","visibility":"PUBLIC"}'),
  ('outfit.shared', '{"outfit_id":"f2000001-0000-0000-0000-000000000001","owner_id":"b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2","visibility":"PUBLIC"}'),
  ('outfit.shared', '{"outfit_id":"f3000001-0000-0000-0000-000000000001","owner_id":"c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3","visibility":"PUBLIC"}'),
  ('outfit.shared', '{"outfit_id":"f4000001-0000-0000-0000-000000000001","owner_id":"d4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4","visibility":"PUBLIC"}'),
  ('outfit.shared', '{"outfit_id":"f5000001-0000-0000-0000-000000000001","owner_id":"e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5","visibility":"PUBLIC"}');

-- migrate:down
DELETE FROM social_outbox
  WHERE processed_at IS NULL
    AND event_type IN ('follow.created', 'outfit.shared')
    AND (payload->>'follower_id' IN (
          'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1',
          'b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2',
          'c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3',
          'd4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4',
          'e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5'
        )
        OR payload->>'owner_id' IN (
          'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1',
          'b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2',
          'c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3',
          'd4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4',
          'e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5'
        ));
DELETE FROM follows WHERE follower_id IN (
    'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1','b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2',
    'c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3','d4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4',
    'e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5');
DELETE FROM outfit_shares WHERE owner_id IN (
    'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1','b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2',
    'c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3','d4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4',
    'e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5');
DELETE FROM outfits WHERE user_id IN (
    'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1','b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2',
    'c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3','d4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4',
    'e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5');
DELETE FROM users WHERE id IN (
    'a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1','b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2',
    'c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3','d4d4d4d4-d4d4-d4d4-d4d4-d4d4d4d4d4d4',
    'e5e5e5e5-e5e5-e5e5-e5e5-e5e5e5e5e5e5');
