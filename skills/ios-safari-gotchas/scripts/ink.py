# python ink.py frames/   one line per frame; << marks ink that disagrees with its ground
import sys, glob
from PIL import Image
S = 3                                        # the screenshots' device scale
POINTS = {"bar L": (4, 895), "bar C": (215, 928)}          # single pixels, in pt
BANDS = {"text L": (20, 215, 918, 932),      # x0, x1, y0, y1 in pt: one line of text,
         "text R": (215, 420, 918, 932)}     # split so a passing edge shows in one half
lum = lambda c: 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
hexc = lambda c: "%02x%02x%02x" % c
def band(im, x0, x1, y0, y1):
    px = sorted((im.getpixel((x, y)) for y in range(y0 * S, y1 * S, 2)
                 for x in range(x0 * S, x1 * S, 2)), key=lum)
    g = lum(px[len(px) // 2])                # the ground: the median
    ink = px[-1] if g < 110 else px[0]       # the ink: the extreme away from the ground
    gk = "DARK" if g < 60 else "LIGHT" if g > 170 else "mid"
    ik = "light" if lum(ink) > 150 else "dark" if lum(ink) < 90 else "grey"
    bad = (gk == "DARK" and ik != "light") or (gk == "LIGHT" and ik != "dark")
    return f"{gk:5} {ik:5} {hexc(ink)}{' <<' if bad else ''}"
print("ms   ", *POINTS, *(f"| {k}" for k in BANDS))
for p in sorted(glob.glob(sys.argv[1].rstrip("/") + "/*.png")):
    im = Image.open(p).convert("RGB")
    print(p.rsplit("/", 1)[-1][:-4],
          *(hexc(im.getpixel((x * S, y * S))) for x, y in POINTS.values()),
          *(f"| {band(im, *b)}" for b in BANDS.values()))
