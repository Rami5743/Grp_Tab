"""A generator for a periodic-table-style poster of the finite simple groups."""

from .render import PosterConfig, Poster, register_fonts  # noqa: F401

__all__ = ["PosterConfig", "Poster", "register_fonts"]
