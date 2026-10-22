# vidtool
 
Setup: unzip it, run cd vidtool, then pip install .

Python:

python
from vidtool import VideoEditor

(VideoEditor("in.mp4")
    .flip("h")
    .zoom(1.1)
    .logo("logo.png", position="bottom-right", scale=0.12, opacity=0.8)
    .reencode(codec="h264", crf=23)
    .save("out.mp4"))

Command line:

bash
vidtool in.mp4 out.mp4 --flip h --zoom 1.1 --logo logo.png --logo-pos bottom-right
vidtool in.mp4 out.mp4 --codec h265 --crf 28 --resize 1280x-2
vidtool in.mp4 out.mp4 --trim 5:20 --speed 1.5 --mute
vidtool in.mp4 out.mp4 --flip h --dry-run   # prints the ffmpeg command only

What it can do:

Re-encode: h264, h265, vp9 or av1, with quality (crf) and speed preset settings.
Flip and rotate: horizontal, vertical or both, plus 90/180/270° rotation.
Zoom, crop and resize: center zoom, crop, and resize that keeps the aspect ratio.
Trim, speed, fps and mute: audio pitch stays correct when you change the speed.
Color and blur: brightness, contrast, saturation and blur.
Overlays: a text overlay, and a logo overlay where you choose the corner or center, the size as a fraction of video width, and the opacity. PNGs with transparency work best.
