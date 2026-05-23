"""Derive a MoodEnum from Spotify audio features."""
from __future__ import annotations

from app.models.user import MoodEnum
from app.models.spotify import SpotifyTrack


def extract_mood(tracks: list[SpotifyTrack]) -> MoodEnum:
    """
    Average valence + energy from recent tracks and map to a mood.

    Spotify audio-feature ranges (0.0 – 1.0):
      valence  : musical positiveness
      energy   : intensity / activity
    """
    tracks_with_features = [t for t in tracks if t.valence is not None and t.energy is not None]

    if not tracks_with_features:
        return MoodEnum.UNKNOWN

    avg_valence = sum(t.valence for t in tracks_with_features) / len(tracks_with_features)
    avg_energy = sum(t.energy for t in tracks_with_features) / len(tracks_with_features)

    # Quadrant mapping
    if avg_valence >= 0.6 and avg_energy >= 0.6:
        return MoodEnum.HAPPY
    if avg_valence >= 0.6 and avg_energy < 0.4:
        return MoodEnum.RELAXED
    if avg_valence >= 0.5 and avg_energy >= 0.5:
        return MoodEnum.ENERGETIC
    if avg_valence < 0.4 and avg_energy >= 0.6:
        return MoodEnum.ANGRY
    if avg_valence < 0.4 and avg_energy < 0.4:
        return MoodEnum.SAD
    if avg_valence < 0.5 and avg_energy < 0.5:
        return MoodEnum.MELANCHOLIC
    if avg_energy < 0.35:
        return MoodEnum.CALM
    return MoodEnum.FOCUSED
