-- migrate:up

CREATE TABLE sizes (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    slug       VARCHAR(50) NOT NULL UNIQUE,
    category   VARCHAR(20) NOT NULL,
    label      VARCHAR(20) NOT NULL,
    sort_order INTEGER     NOT NULL DEFAULT 0
);

CREATE INDEX idx_sizes_category ON sizes (category, sort_order);

-- ── Tops (S → 2XL) ──────────────────────────────────────────────────────────
INSERT INTO sizes (slug, category, label, sort_order) VALUES
    ('tops-s',   'tops', 'S',   1),
    ('tops-m',   'tops', 'M',   2),
    ('tops-l',   'tops', 'L',   3),
    ('tops-xl',  'tops', 'XL',  4),
    ('tops-2xl', 'tops', '2XL', 5);

-- ── Outerwear (S → 2XL) ─────────────────────────────────────────────────────
INSERT INTO sizes (slug, category, label, sort_order) VALUES
    ('outerwear-s',   'outerwear', 'S',   1),
    ('outerwear-m',   'outerwear', 'M',   2),
    ('outerwear-l',   'outerwear', 'L',   3),
    ('outerwear-xl',  'outerwear', 'XL',  4),
    ('outerwear-2xl', 'outerwear', '2XL', 5);

-- ── Bottoms (waist 28 → 44) ──────────────────────────────────────────────────
INSERT INTO sizes (slug, category, label, sort_order) VALUES
    ('bottoms-28', 'bottoms', '28', 1),
    ('bottoms-29', 'bottoms', '29', 2),
    ('bottoms-30', 'bottoms', '30', 3),
    ('bottoms-31', 'bottoms', '31', 4),
    ('bottoms-32', 'bottoms', '32', 5),
    ('bottoms-33', 'bottoms', '33', 6),
    ('bottoms-34', 'bottoms', '34', 7),
    ('bottoms-36', 'bottoms', '36', 8),
    ('bottoms-38', 'bottoms', '38', 9),
    ('bottoms-40', 'bottoms', '40', 10),
    ('bottoms-42', 'bottoms', '42', 11),
    ('bottoms-44', 'bottoms', '44', 12);

-- ── Shoes (EU 8 → 28) ────────────────────────────────────────────────────────
INSERT INTO sizes (slug, category, label, sort_order) VALUES
    ('shoes-8',  'shoes', '8',  1),
    ('shoes-9',  'shoes', '9',  2),
    ('shoes-10', 'shoes', '10', 3),
    ('shoes-11', 'shoes', '11', 4),
    ('shoes-12', 'shoes', '12', 5),
    ('shoes-13', 'shoes', '13', 6),
    ('shoes-14', 'shoes', '14', 7),
    ('shoes-15', 'shoes', '15', 8),
    ('shoes-16', 'shoes', '16', 9),
    ('shoes-17', 'shoes', '17', 10),
    ('shoes-18', 'shoes', '18', 11),
    ('shoes-19', 'shoes', '19', 12),
    ('shoes-20', 'shoes', '20', 13),
    ('shoes-21', 'shoes', '21', 14),
    ('shoes-22', 'shoes', '22', 15),
    ('shoes-23', 'shoes', '23', 16),
    ('shoes-24', 'shoes', '24', 17),
    ('shoes-25', 'shoes', '25', 18),
    ('shoes-26', 'shoes', '26', 19),
    ('shoes-27', 'shoes', '27', 20),
    ('shoes-28', 'shoes', '28', 21);

-- migrate:down
DROP TABLE IF EXISTS sizes;
