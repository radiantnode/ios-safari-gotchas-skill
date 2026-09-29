# python sheet.py frames/ sheet.png 03072 03103 ...   the bottom of each frame, stacked
import sys
from PIL import Image, ImageDraw
S, TOP, BOT = 3, 740, 932                   # scale; the band to keep, in pt
d, out, names = sys.argv[1].rstrip("/"), sys.argv[2], sys.argv[3:]
tiles = []
for n in names:
    im = Image.open(f"{d}/{n}.png").convert("RGB")
    im = im.crop((0, TOP * S, im.width, BOT * S)).resize((im.width // 2, (BOT - TOP) * S // 2))
    ImageDraw.Draw(im).rectangle((0, 0, 70, 22), fill=(255, 255, 0))
    ImageDraw.Draw(im).text((4, 4), n, fill=(0, 0, 0))
    tiles.append(im)
sheet = Image.new("RGB", (tiles[0].width, sum(t.height + 4 for t in tiles)), (255, 0, 255))
y = 0
for t in tiles: sheet.paste(t, (0, y)); y += t.height + 4
sheet.save(out)
