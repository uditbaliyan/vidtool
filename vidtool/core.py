from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

POSITIONS = {
    "top-left": "{m}:{m}",
    "top-right": "W-w-{m}:{m}",
    "bottom-left": "{m}:H-h-{m}",
    "bottom-right": "W-w-{m}:H-h-{m}",
    "center": "(W-w)/2:(H-h)/2",
    "top": "(W-w)/2:{m}",
    "bottom": "(W-w)/2:H-h-{m}",
}


class FFmpegNotFound(RuntimeError):
    pass


def _atempo_chain(speed: float) -> str:
    """atempo only accepts 0.5-2.0 per stage, so chain stages for bigger changes."""
    parts = []
    while speed > 2.0:
        parts.append("atempo=2.0")
        speed /= 2.0
    while speed < 0.5:
        parts.append("atempo=0.5")
        speed /= 0.5
    parts.append(f"atempo={speed:.4f}")
    return ",".join(parts)


class VideoEditor:
    """Chainable video editor. Nothing runs until .save() is called.

    >>> (VideoEditor("in.mp4").flip("h").zoom(1.1).logo("logo.png")
    ...     .reencode(codec="h264", crf=23).save("out.mp4"))
    """

    CODECS = {"h264": "libx264", "h265": "libx265", "vp9": "libvpx-vp9", "av1": "libaom-av1"}

    def __init__(self, input_path: str | Path):
        self.input = Path(input_path)
        if not self.input.exists():
            raise FileNotFoundError(self.input)
        self.ffmpeg = shutil.which("ffmpeg")
        if not self.ffmpeg:
            raise FFmpegNotFound("ffmpeg not found on PATH. Install it from https://ffmpeg.org")
        self._vf: list[str] = []
        self._speed = 1.0
        self._mute = False
        self._start: float | None = None
        self._end: float | None = None
        self._logo: dict | None = None
        self._enc = dict(codec="h264", crf=23, preset="medium", audio_bitrate="128k")
        self._fps: float | None = None

    # ---- edits (each returns self so calls can be chained) ----
    def flip(self, direction: str = "h"):
        """'h' mirror left-right, 'v' upside-down, 'both' = 180 degrees."""
        d = direction.lower()
        if d in ("h", "horizontal", "both"):
            self._vf.append("hflip")
        if d in ("v", "vertical", "both"):
            self._vf.append("vflip")
        if d not in ("h", "horizontal", "v", "vertical", "both"):
            raise ValueError("direction must be 'h', 'v' or 'both'")
        return self

    def rotate(self, degrees: int):
        """Rotate by 90, 180 or 270 degrees clockwise."""
        m = {90: ["transpose=1"], 180: ["hflip", "vflip"], 270: ["transpose=2"], 0: []}
        if degrees % 360 not in m:
            raise ValueError("degrees must be a multiple of 90")
        self._vf += m[degrees % 360]
        return self

    def zoom(self, factor: float = 1.1):
        """Center zoom-in (crop then scale back to the original size). 1.1 = 10%."""
        if factor < 1:
            raise ValueError("zoom factor must be >= 1")
        if factor > 1:
            self._vf.append(
                f"crop=trunc(iw/{factor}/2)*2:trunc(ih/{factor}/2)*2,"
                f"scale={'iw*%s' % factor}:{'ih*%s' % factor}:flags=lanczos,"
                "scale=trunc(iw/2)*2:trunc(ih/2)*2"
            )
        return self

    def resize(self, width: int = -2, height: int = -2):
        """Resize; use -2 for 'keep aspect ratio' on one side."""
        self._vf.append(f"scale={width}:{height}:flags=lanczos")
        return self

    def crop(self, w: int, h: int, x: int = 0, y: int = 0):
        self._vf.append(f"crop={w}:{h}:{x}:{y}")
        return self

    def color(self, brightness=0.0, contrast=1.0, saturation=1.0):
        """brightness -1..1, contrast 0..2, saturation 0..3."""
        self._vf.append(f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}")
        return self

    def blur(self, sigma: float = 3.0):
        self._vf.append(f"gblur=sigma={sigma}")
        return self

    def speed(self, factor: float):
        """2.0 = twice as fast, 0.5 = half speed."""
        if factor <= 0:
            raise ValueError("speed must be > 0")
        self._speed = factor
        return self

    def fps(self, value: float):
        self._fps = value
        return self

    def trim(self, start: float | None = None, end: float | None = None):
        """Keep only [start, end] seconds of the source."""
        self._start, self._end = start, end
        return self

    def mute(self):
        self._mute = True
        return self

    def text(self, content: str, size: int = 36, color: str = "white",
             position: str = "bottom", margin: int = 20):
        safe = content.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\u2019")
        xy = POSITIONS[position].format(m=margin).replace("W", "w").replace("H", "h")
        xy = xy.replace("w-w", "w-tw").replace("h-h", "h-th").replace("(w-w)", "(w-tw)").replace("(h-h)", "(h-th)")
        x, y = xy.split(":")
        self._vf.append(
            f"drawtext=text='{safe}':fontsize={size}:fontcolor={color}:x={x}:y={y}:"
            "box=1:boxcolor=black@0.4:boxborderw=8"
        )
        return self

    def logo(self, image: str | Path, position: str = "top-right",
             scale: float = 0.15, opacity: float = 1.0, margin: int = 20):
        """Overlay a logo/watermark. scale = logo width as a fraction of video width."""
        if position not in POSITIONS:
            raise ValueError(f"position must be one of {list(POSITIONS)}")
        if not Path(image).exists():
            raise FileNotFoundError(image)
        self._logo = dict(path=str(image), position=position, scale=scale,
                          opacity=opacity, margin=margin)
        return self

    def reencode(self, codec: str = "h264", crf: int = 23, preset: str = "medium",
                 audio_bitrate: str = "128k"):
        """Lower crf = better quality/bigger file (h264: 18 great, 23 default, 28 small)."""
        if codec not in self.CODECS:
            raise ValueError(f"codec must be one of {list(self.CODECS)}")
        self._enc = dict(codec=codec, crf=crf, preset=preset, audio_bitrate=audio_bitrate)
        return self

    # ---- build & run ----
    def build_command(self, output: str | Path, overwrite: bool = True) -> list[str]:
        cmd = [self.ffmpeg, "-hide_banner", "-loglevel", "error", "-stats",
               "-y" if overwrite else "-n"]
        if self._start is not None:
            cmd += ["-ss", str(self._start)]
        if self._end is not None:
            cmd += ["-to", str(self._end)]
        cmd += ["-i", str(self.input)]
        if self._logo:
            cmd += ["-i", self._logo["path"]]

        vf = list(self._vf)
        if self._speed != 1.0:
            vf.append(f"setpts=PTS/{self._speed}")
        if self._fps:
            vf.append(f"fps={self._fps}")
        base = ",".join(vf) if vf else "null"

        if self._logo:
            L = self._logo
            pos = POSITIONS[L["position"]].format(m=L["margin"])
            fc = (
                f"[0:v]{base}[base];"
                f"[1:v]format=rgba,colorchannelmixer=aa={L['opacity']}[lg];"
                f"[lg][base]scale2ref=w=main_w*{L['scale']}:h=ow/mdar[lg2][base2];"
                f"[base2][lg2]overlay={pos}[v]"
            )
            cmd += ["-filter_complex", fc, "-map", "[v]"]
        else:
            cmd += ["-vf", base, "-map", "0:v"]

        if self._mute:
            cmd += ["-an"]
        else:
            cmd += ["-map", "0:a?"]
            if self._speed != 1.0:
                cmd += ["-af", _atempo_chain(self._speed)]
            cmd += ["-c:a", "aac", "-b:a", self._enc["audio_bitrate"]]

        e = self._enc
        cmd += ["-c:v", self.CODECS[e["codec"]]]
        if e["codec"] in ("h264", "h265"):
            cmd += ["-crf", str(e["crf"]), "-preset", e["preset"], "-pix_fmt", "yuv420p"]
            if e["codec"] == "h265":
                cmd += ["-tag:v", "hvc1"]
        elif e["codec"] == "vp9":
            cmd += ["-crf", str(e["crf"]), "-b:v", "0"]
        else:
            cmd += ["-crf", str(e["crf"]), "-b:v", "0", "-cpu-used", "6"]
        if str(output).lower().endswith((".mp4", ".mov")):
            cmd += ["-movflags", "+faststart"]
        cmd.append(str(output))
        return cmd

    def save(self, output: str | Path, overwrite: bool = True, dry_run: bool = False) -> Path:
        cmd = self.build_command(output, overwrite)
        if dry_run:
            print(" ".join(cmd))
            return Path(output)
        res = subprocess.run(cmd)
        if res.returncode != 0:
            raise RuntimeError(f"ffmpeg failed (exit {res.returncode})")
        return Path(output)
