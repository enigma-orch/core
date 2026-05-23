\restrict dbmate

-- Dumped from database version 16.14 (Debian 16.14-1.pgdg12+1)
-- Dumped by pg_dump version 18.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: mood_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.mood_enum AS ENUM (
    'HAPPY',
    'SAD',
    'ENERGETIC',
    'CALM',
    'MELANCHOLIC',
    'ANGRY',
    'RELAXED',
    'FOCUSED',
    'UNKNOWN'
);


--
-- Name: visibility_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.visibility_enum AS ENUM (
    'PUBLIC',
    'FOLLOWERS',
    'LINK_ONLY',
    'PRIVATE'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: clothing_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clothing_items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    category character varying(50) NOT NULL,
    colors json DEFAULT '[]'::json NOT NULL,
    brand character varying(255),
    style_tags json DEFAULT '[]'::json NOT NULL,
    image_url text,
    is_favorite boolean DEFAULT false NOT NULL,
    times_worn integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: daily_outfit_picks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.daily_outfit_picks (
    user_id uuid NOT NULL,
    pick_date date NOT NULL,
    outfit_id uuid NOT NULL,
    spotify_context jsonb,
    weather_snapshot jsonb,
    reason text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: follows; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.follows (
    follower_id uuid NOT NULL,
    followee_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: galleries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.galleries (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    name text NOT NULL,
    description text,
    cover_image_url text,
    is_public boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: gallery_outfits; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gallery_outfits (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    gallery_id uuid NOT NULL,
    outfit_id uuid NOT NULL,
    "position" integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    original_image_url text,
    clean_image_url text,
    name text,
    category text,
    subcategory text,
    brand text,
    colors text[],
    season text[],
    occasion text,
    style_tags text[],
    pattern text,
    vibe text,
    mood text,
    size text,
    notes text,
    wear_count integer DEFAULT 0 NOT NULL,
    last_worn_at timestamp with time zone,
    enriched boolean DEFAULT false NOT NULL,
    enrichment_data jsonb,
    embedding public.vector(768),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: outfit_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.outfit_items (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    outfit_id uuid NOT NULL,
    item_id uuid NOT NULL,
    role text,
    "position" integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: outfit_likes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.outfit_likes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    outfit_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: outfit_shares; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.outfit_shares (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    outfit_id uuid NOT NULL,
    owner_id uuid NOT NULL,
    visibility public.visibility_enum DEFAULT 'PUBLIC'::public.visibility_enum NOT NULL,
    share_token text,
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: outfits; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.outfits (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    name text,
    preview_image_url text,
    occasion text,
    season text,
    vibe text,
    mood text,
    weather_context text,
    spotify_context jsonb,
    source text DEFAULT 'ai'::text NOT NULL,
    rating integer,
    worn_at timestamp with time zone,
    wear_count integer DEFAULT 0 NOT NULL,
    embedding public.vector(768),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_migrations (
    version character varying NOT NULL
);


--
-- Name: scraped_outfits; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scraped_outfits (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    image_url text NOT NULL,
    title character varying(500) NOT NULL,
    brand character varying(255),
    price double precision,
    source_url text NOT NULL,
    source_domain character varying(255),
    category character varying(100),
    tags text[],
    meta_data jsonb,
    is_liked boolean,
    seen_at timestamp with time zone,
    style_tags text[],
    weather_tags text[],
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    source_type text DEFAULT 'social'::text NOT NULL
);


--
-- Name: social_outbox; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.social_outbox (
    id bigint NOT NULL,
    occurred_at timestamp with time zone DEFAULT now() NOT NULL,
    event_type text NOT NULL,
    payload jsonb NOT NULL,
    processed_at timestamp with time zone,
    CONSTRAINT social_outbox_event_type_check CHECK ((event_type = ANY (ARRAY['follow.created'::text, 'follow.deleted'::text, 'outfit.shared'::text, 'outfit.share_revoked'::text])))
);


--
-- Name: social_outbox_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.social_outbox_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: social_outbox_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.social_outbox_id_seq OWNED BY public.social_outbox.id;


--
-- Name: spotify_tracks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.spotify_tracks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    spotify_track_id character varying(255) NOT NULL,
    track_name character varying(500) NOT NULL,
    artist_name character varying(500) NOT NULL,
    album_name character varying(500),
    album_image_url character varying(1000),
    played_at timestamp with time zone NOT NULL,
    valence double precision,
    energy double precision,
    danceability double precision,
    tempo double precision,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(255),
    display_name character varying(255),
    avatar_url text,
    mood public.mood_enum DEFAULT 'UNKNOWN'::public.mood_enum NOT NULL,
    location character varying(255),
    style_identity character varying(255),
    preferred_styles text[],
    preferred_colors text[],
    preferred_stores text[],
    budget_min integer,
    budget_max integer,
    tops_size character varying(50),
    bottoms_size character varying(50),
    shoes_size character varying(50),
    outerwear_size character varying(50),
    spotify_id character varying(255),
    spotify_access_token text,
    spotify_refresh_token text,
    spotify_token_expires_at timestamp with time zone,
    google_id character varying(255),
    google_access_token text,
    google_refresh_token text,
    google_token_expires_at timestamp with time zone,
    google_calendar_id character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    refresh_token_hash text,
    refresh_token_expires_at timestamp with time zone
);


--
-- Name: social_outbox id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.social_outbox ALTER COLUMN id SET DEFAULT nextval('public.social_outbox_id_seq'::regclass);


--
-- Name: clothing_items clothing_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clothing_items
    ADD CONSTRAINT clothing_items_pkey PRIMARY KEY (id);


--
-- Name: daily_outfit_picks daily_outfit_picks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.daily_outfit_picks
    ADD CONSTRAINT daily_outfit_picks_pkey PRIMARY KEY (user_id, pick_date);


--
-- Name: follows follows_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.follows
    ADD CONSTRAINT follows_pkey PRIMARY KEY (follower_id, followee_id);


--
-- Name: galleries galleries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.galleries
    ADD CONSTRAINT galleries_pkey PRIMARY KEY (id);


--
-- Name: gallery_outfits gallery_outfits_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gallery_outfits
    ADD CONSTRAINT gallery_outfits_pkey PRIMARY KEY (id);


--
-- Name: items items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_pkey PRIMARY KEY (id);


--
-- Name: outfit_items outfit_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outfit_items
    ADD CONSTRAINT outfit_items_pkey PRIMARY KEY (id);


--
-- Name: outfit_likes outfit_likes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outfit_likes
    ADD CONSTRAINT outfit_likes_pkey PRIMARY KEY (id);


--
-- Name: outfit_shares outfit_shares_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outfit_shares
    ADD CONSTRAINT outfit_shares_pkey PRIMARY KEY (id);


--
-- Name: outfit_shares outfit_shares_share_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outfit_shares
    ADD CONSTRAINT outfit_shares_share_token_key UNIQUE (share_token);


--
-- Name: outfits outfits_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outfits
    ADD CONSTRAINT outfits_pkey PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: scraped_outfits scraped_outfits_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scraped_outfits
    ADD CONSTRAINT scraped_outfits_pkey PRIMARY KEY (id);


--
-- Name: social_outbox social_outbox_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.social_outbox
    ADD CONSTRAINT social_outbox_pkey PRIMARY KEY (id);


--
-- Name: spotify_tracks spotify_tracks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.spotify_tracks
    ADD CONSTRAINT spotify_tracks_pkey PRIMARY KEY (id);


--
-- Name: gallery_outfits uq_gallery_outfit; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gallery_outfits
    ADD CONSTRAINT uq_gallery_outfit UNIQUE (gallery_id, outfit_id);


--
-- Name: outfit_items uq_outfit_items_outfit_item; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outfit_items
    ADD CONSTRAINT uq_outfit_items_outfit_item UNIQUE (outfit_id, item_id);


--
-- Name: outfit_likes uq_outfit_likes_user_outfit; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outfit_likes
    ADD CONSTRAINT uq_outfit_likes_user_outfit UNIQUE (user_id, outfit_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_google_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_google_id_key UNIQUE (google_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_spotify_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_spotify_id_key UNIQUE (spotify_id);


--
-- Name: idx_daily_outfit_picks_outfit; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_daily_outfit_picks_outfit ON public.daily_outfit_picks USING btree (outfit_id);


--
-- Name: idx_follows_followee; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_follows_followee ON public.follows USING btree (followee_id);


--
-- Name: idx_galleries_public; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_galleries_public ON public.galleries USING btree (is_public);


--
-- Name: idx_galleries_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_galleries_user_id ON public.galleries USING btree (user_id);


--
-- Name: idx_gallery_outfits_gallery; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gallery_outfits_gallery ON public.gallery_outfits USING btree (gallery_id);


--
-- Name: idx_gallery_outfits_outfit; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gallery_outfits_outfit ON public.gallery_outfits USING btree (outfit_id);


--
-- Name: idx_items_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_items_category ON public.items USING btree (user_id, category);


--
-- Name: idx_items_embedding; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_items_embedding ON public.items USING hnsw (embedding public.vector_cosine_ops);


--
-- Name: idx_items_last_worn; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_items_last_worn ON public.items USING btree (user_id, last_worn_at);


--
-- Name: idx_items_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_items_user_id ON public.items USING btree (user_id);


--
-- Name: idx_outfit_items_item; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_outfit_items_item ON public.outfit_items USING btree (item_id);


--
-- Name: idx_outfit_items_outfit; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_outfit_items_outfit ON public.outfit_items USING btree (outfit_id);


--
-- Name: idx_outfit_likes_outfit; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_outfit_likes_outfit ON public.outfit_likes USING btree (outfit_id);


--
-- Name: idx_outfit_likes_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_outfit_likes_user ON public.outfit_likes USING btree (user_id);


--
-- Name: idx_outfit_shares_outfit; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_outfit_shares_outfit ON public.outfit_shares USING btree (outfit_id);


--
-- Name: idx_outfit_shares_outfit_visibility; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_outfit_shares_outfit_visibility ON public.outfit_shares USING btree (outfit_id, visibility) WHERE (visibility = ANY (ARRAY['PUBLIC'::public.visibility_enum, 'FOLLOWERS'::public.visibility_enum]));


--
-- Name: idx_outfit_shares_owner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_outfit_shares_owner ON public.outfit_shares USING btree (owner_id);


--
-- Name: idx_outfit_shares_token; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_outfit_shares_token ON public.outfit_shares USING btree (share_token) WHERE (share_token IS NOT NULL);


--
-- Name: idx_outfits_embedding; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_outfits_embedding ON public.outfits USING hnsw (embedding public.vector_cosine_ops);


--
-- Name: idx_outfits_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_outfits_source ON public.outfits USING btree (user_id, source);


--
-- Name: idx_outfits_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_outfits_user_id ON public.outfits USING btree (user_id);


--
-- Name: idx_outfits_worn_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_outfits_worn_at ON public.outfits USING btree (user_id, worn_at);


--
-- Name: idx_scraped_outfits_user_retail; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scraped_outfits_user_retail ON public.scraped_outfits USING btree (user_id, created_at DESC) WHERE (source_type = 'retail'::text);


--
-- Name: idx_social_outbox_unprocessed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_social_outbox_unprocessed ON public.social_outbox USING btree (id) WHERE (processed_at IS NULL);


--
-- Name: idx_users_refresh_token_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_refresh_token_hash ON public.users USING btree (refresh_token_hash) WHERE (refresh_token_hash IS NOT NULL);


--
-- Name: ix_clothing_items_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_clothing_items_user_id ON public.clothing_items USING btree (user_id);


--
-- Name: ix_scraped_outfits_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scraped_outfits_user_id ON public.scraped_outfits USING btree (user_id);


--
-- Name: ix_spotify_tracks_played_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_spotify_tracks_played_at ON public.spotify_tracks USING btree (played_at);


--
-- Name: ix_spotify_tracks_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_spotify_tracks_user_id ON public.spotify_tracks USING btree (user_id);


--
-- Name: clothing_items clothing_items_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clothing_items
    ADD CONSTRAINT clothing_items_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: daily_outfit_picks daily_outfit_picks_outfit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.daily_outfit_picks
    ADD CONSTRAINT daily_outfit_picks_outfit_id_fkey FOREIGN KEY (outfit_id) REFERENCES public.outfits(id) ON DELETE CASCADE;


--
-- Name: daily_outfit_picks daily_outfit_picks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.daily_outfit_picks
    ADD CONSTRAINT daily_outfit_picks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: follows follows_followee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.follows
    ADD CONSTRAINT follows_followee_id_fkey FOREIGN KEY (followee_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: follows follows_follower_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.follows
    ADD CONSTRAINT follows_follower_id_fkey FOREIGN KEY (follower_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: galleries galleries_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.galleries
    ADD CONSTRAINT galleries_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: gallery_outfits gallery_outfits_gallery_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gallery_outfits
    ADD CONSTRAINT gallery_outfits_gallery_id_fkey FOREIGN KEY (gallery_id) REFERENCES public.galleries(id) ON DELETE CASCADE;


--
-- Name: gallery_outfits gallery_outfits_outfit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gallery_outfits
    ADD CONSTRAINT gallery_outfits_outfit_id_fkey FOREIGN KEY (outfit_id) REFERENCES public.outfits(id) ON DELETE CASCADE;


--
-- Name: items items_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: outfit_items outfit_items_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outfit_items
    ADD CONSTRAINT outfit_items_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE CASCADE;


--
-- Name: outfit_items outfit_items_outfit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outfit_items
    ADD CONSTRAINT outfit_items_outfit_id_fkey FOREIGN KEY (outfit_id) REFERENCES public.outfits(id) ON DELETE CASCADE;


--
-- Name: outfit_likes outfit_likes_outfit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outfit_likes
    ADD CONSTRAINT outfit_likes_outfit_id_fkey FOREIGN KEY (outfit_id) REFERENCES public.outfits(id) ON DELETE CASCADE;


--
-- Name: outfit_likes outfit_likes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outfit_likes
    ADD CONSTRAINT outfit_likes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: outfit_shares outfit_shares_outfit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outfit_shares
    ADD CONSTRAINT outfit_shares_outfit_id_fkey FOREIGN KEY (outfit_id) REFERENCES public.outfits(id) ON DELETE CASCADE;


--
-- Name: outfit_shares outfit_shares_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outfit_shares
    ADD CONSTRAINT outfit_shares_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: outfits outfits_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outfits
    ADD CONSTRAINT outfits_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: scraped_outfits scraped_outfits_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scraped_outfits
    ADD CONSTRAINT scraped_outfits_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: spotify_tracks spotify_tracks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.spotify_tracks
    ADD CONSTRAINT spotify_tracks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict dbmate


--
-- Dbmate schema migrations
--

INSERT INTO public.schema_migrations (version) VALUES
    ('20260522000001'),
    ('20260522000002'),
    ('20260523000001'),
    ('20260523000002'),
    ('20260523000003'),
    ('20260523114543'),
    ('20260523125103'),
    ('20260523200000'),
    ('20260524000001'),
    ('20260524000002'),
    ('20260524000003');
