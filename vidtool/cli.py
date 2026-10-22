import argparse
import sys

from .core import POSITIONS, VideoEditor


def main(argv=None):
    p = argparse.ArgumentParser(prog="vidtool", description="Basic video editing powered by FFmpeg.")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--flip", choices=["h", "v", "both"])
    p.add_argument("--rotate", type=int, choices=[90, 180, 270])
    p.add_argument("--zoom", type=float, help="center zoom factor, e.g. 1.1")
    p.add_argument("--resize", metavar="WxH", help="e.g. 1280x720 or 1280x-2 (keep ratio)")
    p.add_argument("--crop", metavar="W:H:X:Y")
    p.add_argument("--speed", type=float)
    p.add_argument("--fps", type=float)
    p.add_argument("--trim", metavar="START:END", help="seconds, e.g. 5:20 (either side optional)")
    p.add_argument("--mute", action="store_true")
    p.add_argument("--brightness", type=float, default=0.0)
    p.add_argument("--contrast", type=float, default=1.0)
    p.add_argument("--saturation", type=float, default=1.0)
    p.add_argument("--blur", type=float)
    p.add_argument("--text")
    p.add_argument("--logo", help="path to logo image (png with transparency works best)")
    p.add_argument("--logo-pos", default="top-right", choices=list(POSITIONS))
    p.add_argument("--logo-scale", type=float, default=0.15, help="logo width as fraction of video width")
    p.add_argument("--logo-opacity", type=float, default=1.0)
    p.add_argument("--codec", default="h264", choices=["h264", "h265", "vp9", "av1"])
    p.add_argument("--crf", type=int, default=23)
    p.add_argument("--preset", default="medium")
    p.add_argument("--dry-run", action="store_true", help="print the ffmpeg command only")
    a = p.parse_args(argv)

    v = VideoEditor(a.input)
    if a.trim:
        s, _, e = a.trim.partition(":")
        v.trim(float(s) if s else None, float(e) if e else None)
    if a.crop:
        w, h, x, y = (int(n) for n in a.crop.split(":"))
        v.crop(w, h, x, y)
    if a.flip: v.flip(a.flip)
    if a.rotate: v.rotate(a.rotate)
    if a.zoom: v.zoom(a.zoom)
    if a.resize:
        w, _, h = a.resize.partition("x")
        v.resize(int(w), int(h or -2))
    if (a.brightness, a.contrast, a.saturation) != (0.0, 1.0, 1.0):
        v.color(a.brightness, a.contrast, a.saturation)
    if a.blur: v.blur(a.blur)
    if a.speed: v.speed(a.speed)
    if a.fps: v.fps(a.fps)
    if a.mute: v.mute()
    if a.text: v.text(a.text)
    if a.logo: v.logo(a.logo, a.logo_pos, a.logo_scale, a.logo_opacity)
    v.reencode(a.codec, a.crf, a.preset)
    try:
        v.save(a.output, dry_run=a.dry_run)
    except Exception as ex:
        print(f"error: {ex}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
