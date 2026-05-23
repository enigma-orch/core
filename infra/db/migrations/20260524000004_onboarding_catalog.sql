-- migrate:up

CREATE TABLE vibes (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        VARCHAR(100) NOT NULL UNIQUE,
    label       VARCHAR(100) NOT NULL,
    description TEXT,
    emoji       VARCHAR(10),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE color_palettes (
    id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    slug     VARCHAR(100) NOT NULL UNIQUE,
    label    VARCHAR(100) NOT NULL,
    swatches TEXT[]       NOT NULL DEFAULT '{}'
);

CREATE TABLE stores (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        VARCHAR(100) NOT NULL UNIQUE,
    name        VARCHAR(255) NOT NULL,
    logo_url    TEXT,
    website_url TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Vibes seed ──────────────────────────────────────────────────────────────
INSERT INTO vibes (slug, label, description, emoji) VALUES
    ('streetwear',     'Streetwear',      'Bold graphics, oversized fits, sneaker culture',       '🧢'),
    ('minimal',        'Minimal',         'Clean lines, neutral palette, quiet confidence',        '🤍'),
    ('old-money',      'Old Money',       'Timeless tailoring, muted tones, understated luxury',  '🏛️'),
    ('y2k',            'Y2K',             'Low-rise, metallics, playful throwback energy',         '✨'),
    ('dark-academia',  'Dark Academia',   'Plaid, leather, earthy tones, intellectual edge',      '📚'),
    ('sporty',         'Sporty',          'Athletic silhouettes, functional fabric, clean look',  '⚡'),
    ('elegant',        'Elegant',         'Structured cuts, monochromatic, elevated basics',       '🌹'),
    ('bold',           'Bold',            'Saturated colors, statement pieces, maximalist energy','🔥'),
    ('coastal',        'Coastal',         'Linen, stripes, breezy summer ease',                   '🌊'),
    ('edgy',           'Edgy',            'Leather, chains, asymmetric cuts, dark palette',       '🖤'),
    ('cottagecore',    'Cottagecore',     'Florals, soft textures, romantic and earthy tones',    '🌸'),
    ('business-casual','Business Casual', 'Smart separates, polished but relaxed',                '💼');

-- ── Color palettes seed ─────────────────────────────────────────────────────
INSERT INTO color_palettes (slug, label, swatches) VALUES
    ('monochrome',    'Monochrome',     ARRAY['#000000','#4a4a4a','#9b9b9b','#ffffff']),
    ('earth-tones',   'Earth Tones',   ARRAY['#8B5E3C','#C49A6C','#D4B896','#E8D5B7']),
    ('pastels',       'Pastels',        ARRAY['#FFB3BA','#FFDFBA','#FFFFBA','#BAFFC9','#BAE1FF']),
    ('neutrals',      'Neutrals',       ARRAY['#F5F0EB','#D4C5B0','#A89880','#6B5B4E']),
    ('bold-primaries','Bold Primaries', ARRAY['#E63946','#457B9D','#2A9D8F','#E9C46A']),
    ('jewel-tones',   'Jewel Tones',    ARRAY['#2E4057','#048A81','#8338EC','#A4262C']),
    ('warm-nudes',    'Warm Nudes',     ARRAY['#C9956C','#D4A57A','#E8C4A0','#F5DEB3']),
    ('dark-moody',    'Dark Moody',     ARRAY['#1A1A2E','#16213E','#2D4739','#3D2B1F']);

-- ── Stores seed ─────────────────────────────────────────────────────────────
INSERT INTO stores (slug, name, website_url) VALUES
    ('zara',              'Zara',              'https://www.zara.com'),
    ('hm',                'H&M',               'https://www.hm.com'),
    ('asos',              'ASOS',              'https://www.asos.com'),
    ('uniqlo',            'Uniqlo',            'https://www.uniqlo.com'),
    ('nike',              'Nike',              'https://www.nike.com'),
    ('adidas',            'Adidas',            'https://www.adidas.com'),
    ('pull-and-bear',     'Pull&Bear',         'https://www.pullandbear.com'),
    ('mango',             'Mango',             'https://www.mango.com'),
    ('urban-outfitters',  'Urban Outfitters',  'https://www.urbanoutfitters.com'),
    ('free-people',       'Free People',       'https://www.freepeople.com'),
    ('shein',             'SHEIN',             'https://www.shein.com'),
    ('revolve',           'Revolve',           'https://www.revolve.com'),
    ('nordstrom',         'Nordstrom',         'https://www.nordstrom.com'),
    ('forever-21',        'Forever 21',        'https://www.forever21.com'),
    ('cos',               'COS',               'https://www.cos.com');

-- migrate:down
DROP TABLE IF EXISTS stores;
DROP TABLE IF EXISTS color_palettes;
DROP TABLE IF EXISTS vibes;
