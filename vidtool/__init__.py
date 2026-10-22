"""vidtool - basic video editing (re-encode, flip, zoom, logo...) on top of FFmpeg."""
from .core import VideoEditor, FFmpegNotFound

__all__ = ["VideoEditor", "FFmpegNotFound"]
__version__ = "0.1.0"
