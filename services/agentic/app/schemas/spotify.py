"""Schemas for Spotify taste data surfaced to the shuffle and outfit compose pipelines."""
from __future__ import annotations

from pydantic import BaseModel


class PlaylistSummary(BaseModel):
    id: str
    name: str
    track_count: int
    image_url: str | None = None


class TrackSummary(BaseModel):
    id: str
    name: str
    artists: list[str]
    # Audio features — None when Spotify hasn't computed them yet.
    valence: float | None = None
    energy: float | None = None
    danceability: float | None = None
    tempo: float | None = None


class AudioProfile(BaseModel):
    """Averaged audio features across the user's top/recent tracks."""
    avg_valence: float | None = None
    avg_energy: float | None = None
    avg_danceability: float | None = None
    avg_tempo: float | None = None


class SpotifyTasteProfile(BaseModel):
    """Full music taste snapshot returned by GET /users/me/spotify/taste.

    Consumed downstream by:
    - shuffle engine  (music_taste_boost in services/shuffle.py)
    - outfit composer (_context_prompt_block in api/v1/outfit_compose.py)
    """
    playlists: list[PlaylistSummary]
    top_tracks: list[TrackSummary]       # short-term top tracks (~4 weeks)
    top_genres: list[str]                # deduplicated genres from top artists
    audio_profile: AudioProfile          # averaged fingerprint of top_tracks
