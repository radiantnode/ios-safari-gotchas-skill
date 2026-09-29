# Verifying on the real thing

Headless WebKit models none of the gotchas in §1–§4 or §12. The iOS simulator does (so this
needs a Mac), and it runs without Simulator.app: boot a device, open a URL in mobile Safari, take a screenshot,
sample pixels. Everything below is `xcrun simctl` plus Python with Pillow (on the host or in
a `python` container), and ffmpeg in a container for films. Taps, swipes and rotation need injected input — `idb ui tap|swipe|
rotate`, or a simulator-control tool if the harness has one; `simctl` has none.

## Needs

- Xcode — the command-line tools alone have no `simctl` or simulator runtimes.
- An iOS runtime: `xcrun simctl list runtimes` (install with
  `xcodebuild -downloadPlatform iOS` if empty).
- A device: `xcrun simctl create probe "iPhone 17" <runtime-id>` once; reuse it.
- Your built site served on a host port, e.g. nginx in Docker on `:8099`. Point Safari at
  `http://127.0.0.1:<port>` — `localhost` resolved but did not connect from inside the
  simulator. A site on another machine works by its LAN or proxy name.
- The same Safari tab layout as the phone you are chasing (§12, "Safari's tab layout"
  below). The simulator defaults to Compact.
- `python3 -c "import PIL"` for the samplers.

## The loop

```sh
U=$(xcrun simctl list devices | awk '/probe/{match($0,/[0-9A-F-]{36}/); print substr($0,RSTART,RLENGTH); exit}')
xcrun simctl boot "$U"; xcrun simctl bootstatus "$U" -b
# Just after boot both of these can fail with "Operation timed out" and leave Safari on a
# white page that never paints, or crash every page ("This webpage was reloaded because a
# problem occurred"): retry, and if it persists terminate Safari and start again.
for i in 1 2 3 4 5 6; do xcrun simctl launch "$U" com.apple.mobilesafari && break; sleep 5; done
sleep 15     # first shot after launch is junk otherwise

shoot () {  # url, name
  xcrun simctl openurl "$U" "$1"; sleep 26
  xcrun simctl io "$U" screenshot "shots/$2.png"
}
```

Three rules that cost a day when ignored:

1. **One path per variant.** Safari remembers the latched colors per URL path. Query
   strings inherit the first load's answer. Copy the page to `/p/<variant>/index.html`
   for every probe.
2. **Wait for load.** ~25s per shot in the simulator is not excessive. If a sample comes
   back pure white or pure black across the whole column, the page hadn't painted — reshoot.
   The first one or two shots after launching Safari are often blank regardless: open a
   throwaway page first. After `simctl erase`, loads take 60–75s for a while; wait longer.
3. **Reset when you must re-measure a path.** `xcrun simctl erase <udid>` (device shut
   down first) clears Safari's latched answers for every path. It also clears permissions:
   a page that asks for location will then block on a system dialog you cannot tap —
   pre-grant it with `xcrun simctl privacy <udid> grant location-always com.apple.mobilesafari`.

## Landing at a scroll offset

To read colors mid-page without disturbing the toolbar, give the served copy a way to land
there by itself (a real swipe also collapses the bars, which is a different state — see
"Collapsing the toolbar" below):

```html
<script>addEventListener('load',()=>{const y=+new URL(location).searchParams.get('y')||0;
if(y)setTimeout(()=>scrollTo(0,y),500);});</script>
```

Note this scroll fires *no* `scroll` event in headless WebKit and may not in the simulator
either — fine for reading colors, useless for exercising scroll handlers.

## Reading the strip behind the toolbar (§1)

Sample the left margin, clear of the toolbar, from the bottom up until the color changes.
With the Compact bar x=20 (3x px) is clear; the Bottom bar spans nearly the full width, so
use x=4 there, and expect the bar's frosting to tint what you read. The bottom color is the strip; the distance to the change is its height; the
color just above it is the page's own edge.

```python
from PIL import Image
import sys
for path in sys.argv[1:]:
    im = Image.open(path).convert('RGB'); w, h = im.size
    col = [im.getpixel((20, y)) for y in range(h - 1, 0, -1)]
    base = col[0]
    edge = next((i for i, c in enumerate(col) if max(abs(a-b) for a, b in zip(c, base)) > 12), None)
    print(f"{path:30} strip={base} height={edge}px above-edge={col[edge] if edge else None}")
```

**Tell the two modes apart** by putting a loud ground under the fold in the probe copy:

```css
body { background: #ff00ff }
```

Screenshot mid-page. Strip magenta → overdraw (the page is painting through the chrome).
Strip any flat color with magenta cut off above it → flat fill. This is the only reliable
test; the page's own ground is usually the same color as the fallback fill, so without
the magenta both modes look identical from outside.

Mid-page, not at the end: past the document's end the strip is `body`'s color in *both*
modes (§10), so magenta at max scroll tells you nothing about the mode.

## Swap after load (§10)

Which end re-reads `body`, and which one latched. Load light, go dark 3s later, then to
the end:

```html
<script>
setTimeout(() => {
  document.body.style.background = '#0E1113';
  const e = Date.now() + 8000;
  (function l(){ scrollTo(0, 1e7); if (Date.now() < e) setTimeout(l, 120); })();
}, 3000);
</script>
```

Sample the status bar and the strip. Strip dark, status bar light = the trick in §10 is
available. The scroll loop rather than one `scrollTo`: a single call at load+500ms lands
on a stale maximum and the readout shows `scrollY` as the number you asked for.

## Reload from the bottom (§10)

Reproduces scroll restoration, which no `openurl` does — same document, same path:

```html
<script>
if (!sessionStorage.rl) {
  sessionStorage.rl = '1';
  setTimeout(() => { scrollTo(0, 1e7); setTimeout(() => location.reload(), 2500); }, 3000);
}
</script>
```

The second load restores the position and fires `scroll` with no gesture. Sample the status
bar. In the simulator the swap always lost the race and the bar stayed light; a real phone
with a cached reload is faster, and that is where a `load`-timed swap latched dark.

## A readout that survives the screenshot

A fixed box in the corner, refreshed on an interval, is worth more than any log:

```html
<div id="r" style="position:fixed;left:8px;top:8px;z-index:99;background:#fff;color:#000;font:12px/1.3 monospace;padding:4px"></div>
<script>setInterval(() => { document.getElementById('r').textContent =
  'y ' + Math.round(scrollY) + '/' + Math.round(document.documentElement.scrollHeight - innerHeight) +
  ' iH ' + innerHeight + ' body ' + getComputedStyle(document.body).backgroundColor; }, 300);</script>
```

On a 17 Pro with the Compact bar, `innerHeight` 714 is the toolbar showing and 754 is it
collapsed; other phones and the Bottom layout differ (`viewport-numbers.md`). `foot.bottom === innerHeight`
at max scroll is what makes an exact compare flicker.

## Reading the status bar (§2)

```python
pts = [(20, 60), (20, 150), (w - 20, 60), (w // 2, 30)]   # 3x screenshots; 62pt bar ≈ 186px
print([im.getpixel(p) for p in pts])
```

All four should agree. Compare against the color of whatever the page paints at its top.

## A transition map down one column (§11)

For anything that is an *edge* rather than a field — a seam, a hairline, where one band
stops and the next starts — sample a column in the gutter and print only the rows where
the color changes. Every edge on the page then arrives as a list, in device rows and in
CSS px, and a 1px line is as legible as a 200px band:

```python
x, prev = 60, None
for y in range(900):                       # 3x: 900 rows ≈ the top 300pt
    v = im.getpixel((x, y))[:3]
    if v != prev: print(f"{y:4} (css {y/3:6.1f})  {v}"); prev = v
```

```
   0 (css    0.0)  (14, 16, 19)     Safari's status strip — body's color
 186 (css   62.0)  (92, 95, 96)     the seam
 189 (css   63.0)  (22, 24, 26)     the film
```

Run it on both builds and diff the two lists: that is the whole before-and-after, and it
does not care what the film happened to be showing. Without PIL, the same thing in a
Playwright container — draw the PNG to a canvas and read `getImageData` — is a dozen
lines and runs where the browsers already are.

## Bisecting, and the minimal-page ledger

For a construct suspected of ratcheting the page into flat fill, the page that finds it in
one window: a `#ff00ff` ground, 4000px of striped filler so the fold has content, a small
script that applies ONE construct at load, removes it after 2s, then scrolls to 1500. Ship
eight of them at distinct paths — a control with no construct, `sticky` 100dvh as the
positive control, then `body` fixed inset:0, a fixed child at 100dvh, at 100lvh, at
lvh+120px, `html` overflow hidden — and read the strip on each. Stripes continuing into
the strip = no ratchet; a uniform 294px band with the stripes cut off above it = ratchet.
The control must read stripes-through and `sticky` must read flat, or the rig is wrong.

When a real page misbehaves and a minimal one doesn't, build *up* from the minimal page
toward the real structure (sticky, then the viewport height, then an opaque child, then
media) rather than *down* from the real page by deleting things — the real page has too
many interacting parts, and the per-URL cache will lie to you on the way down. Each
minimal variant is one file and one 25-second shot.

## Ready-made probes

Two sets are already hosted:
- https://radiantnode.github.io/ios-safari-gotchas-skill/ is the striped edge probe with a live
  readout of the viewport units, insets and a guess at the tab layout.
- https://radiantnode.github.io/ios-safari-gotchas-skill/probes/ has the single-variable color
  probes behind §1, §2 and §10, with the results recorded for the simulator and a real iPhone.

Each color-probe path gives one honest reading per device (rule 1). To rerun one, serve a copy
under a new path.

## Emulating late scroll delivery (§5), in Playwright WebKit

```js
await page.addInitScript((ms) => {
  const real = EventTarget.prototype.addEventListener;
  EventTarget.prototype.addEventListener = function (t, fn, o) {
    if (t === 'scroll' && typeof fn === 'function')
      return real.call(this, t, (e) => setTimeout(() => fn(e), ms), o);
    return real.call(this, t, fn, o);
  };
}, 120);
```

Then drive with `page.mouse.wheel()` in ~16ms steps, and record per frame in rAF *after*
the page's own loop is running. A scroll-event-driven state loses 1–3 frames per flick
under this; a rAF-driven one loses none. Run the same harness against the version you
expect to fail first — a test that cannot fail proves nothing.

## Safari's tab layout (§12)

Settings › Apps › Safari › Tabs: **Compact** (floating pill, the simulator's default),
**Bottom** (full-width bar at the foot) or **Top**. It is per device, and changes
`innerHeight`, `svh` and `dvh` by 60pt (§4). Ask which one the reporter uses before
anything else.

Set it in the simulator the way a person would — no `defaults` key for it turned up in
the Safari binaries (the setting sits in the shared cache). Launch `com.apple.Preferences`,
swipe the list up to **Apps**, tap it, tap the **S** in the index, tap **Safari**, swipe
down to **Tabs**, tap the layout. Settings takes taps late in the simulator, and search
there returns nothing until indexing has finished: wait ~3s after each tap and screenshot
before the next, or a late tap lands on whatever row has moved under it. Then terminate and
relaunch Safari.

## Where the page stops: a striped probe (§4, §12)

One static page answers "how far down does Safari draw the page, and where does `body`
show": a loud `body`, 40pt stripes, and a readout of the numbers.

```html
<!doctype html><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>html,body{margin:0}body{background:#ff00ff;font:15px/1.35 monospace}
.s{height:4000px;background:repeating-linear-gradient(#0af 0 20px,#fa0 20px 40px)}
#r{position:fixed;left:8px;top:120px;background:#fff;padding:6px;white-space:pre}
.m{position:absolute;top:0;width:0;visibility:hidden}</style>
<div class="s"></div><div id="r"></div>
<div class="m" id="svh" style="height:100svh"></div><div class="m" id="lvh" style="height:100lvh"></div>
<div class="m" id="dvh" style="height:100dvh"></div>
<div class="m" id="sb" style="height:env(safe-area-inset-bottom)"></div>
<script>const g=i=>document.getElementById(i).offsetHeight;
setInterval(()=>r.textContent=`screen ${screen.width}x${screen.height}\ninnerH ${innerHeight}`+
 `\nsvh ${g('svh')} lvh ${g('lvh')} dvh ${g('dvh')}\ninset B ${g('sb')}\ny ${Math.round(scrollY)}`,300)</script>
```

Read it off the screenshot: the first non-magenta row from the top, sampled clear of the
clock and the Dynamic Island (x=4 and x=30% of the width; the middle column hits the
island), is where the layout viewport starts. Stripes in the last row at x=4 mean the page
is drawn to the screen's edge; magenta there means `body` shows (past the document's end,
or in flat fill, §1). Serve it as a static file; a dev server that maps `/probe/` to
`index.html` only for its own routes may 404 the bare directory — ask for
`/probe/index.html`.

## Collapsing the toolbar

A swipe collapses Safari's bars; `scrollTo` never does. With injected touch, drag upward
through the middle of the page (e.g. 650pt → 350pt over ~0.35s) and wait 3s before the
shot. On the Bottom layout the bar becomes a pill and `innerHeight`/`dvh` jump to `lvh`
(`viewport-numbers.md`). Read the probe to confirm which state you actually shot.

## Filming an effect (§12)

A reveal or sweep lasts about a second, and screenshots come ~0.5s apart. Film it instead.
Record in the background, tap the control with injected touch, and stop the recorder with
SIGINT, which is what finalizes the file:

```sh
xcrun simctl io "$U" recordVideo --codec=h264 --force out.mp4 & P=$!
sleep 14                        # tap the control ~2s in; tap again ~5s later for the reverse
kill -INT $P; wait $P
```

Extract every frame the recorder wrote, named by its time in milliseconds — with ffmpeg in
Docker as below, or a local `ffmpeg`/`ffprobe` with the same arguments:

```sh
mkdir -p frames
docker run --rm -v "$PWD":/w jrottenberg/ffmpeg:6.1-alpine -loglevel error -i /w/out.mp4 \
  -fps_mode passthrough -frame_pts 1 -enc_time_base 0.001 /w/frames/%05d.png
# the timestamps alone:
docker run --rm --entrypoint ffprobe -v "$PWD":/w jrottenberg/ffmpeg:6.1-alpine -loglevel error \
  -select_streams v -show_entries frame=pts_time -of csv=p=0 /w/out.mp4
```

`-fps_mode passthrough` keeps exactly the recorded frames, `-enc_time_base 0.001` puts
their times in milliseconds, and `-frame_pts 1` names each file by that time: `03072.png`
is 3.072s in. Never resample with `-vf fps=10`: on a 100ms grid it kept almost none of the
burst of frames during the animation and made a one-second sweep look like a one-frame
flip.

Reading the film:

- **Frames come at a variable rate.** They arrived ~15ms apart while things moved, and none
  for seconds while the page was still. Whether that is "nothing changed" or "nothing was
  composited" is not known, so do not read a gap as proof of stillness.
- **Judge the order, not the speed.** The simulator's circle advanced in large jumps. What
  one frame shows together (the strip turned, the band above it not yet, the text still in
  the old ink) is the evidence; the milliseconds between frames are not a measure of
  smoothness.
- **Blame the page's own waits first.** Four films each had 350–380ms with no frames after
  the night→day tap, and no such gap after the day→night tap. The switch awaited the day
  photograph's decode before starting the circle; the simulator was not stalling.

Two samplers in this skill's `scripts/` folder. From the folder holding `frames/`, with
`$SKILL` set to this skill's directory:
`docker run --rm -v "$PWD":/w -v "$SKILL/scripts":/s -w /w python:3.12-slim sh -c 'pip -q install pillow >/dev/null; python /s/ink.py frames/'`
(or `python3 "$SKILL/scripts/ink.py" frames/` with Pillow installed):

- **`ink.py`** prints one line per frame: a few single pixels (the strip behind the toolbar,
  say) and, for each band of text, its ground (the median, DARK/LIGHT/mid) and its ink (the
  extreme away from the ground, light/dark/gray). `<<` marks a band whose ink disagrees
  with its ground. Split a line of text into halves so an edge passing along it shows in
  one half first. Coordinates are in pt at the top of the file; set them for the device and
  page.
- **`sheet.py frames/ sheet.png 03072 03103 …`** stacks the bottom band of the named frames
  into one image, labeled by time, to look at the handful of frames that `ink.py` flagged.

With no injected touch, a throwaway route per variant that clicks the control on a timer
(`/sweep/<n>/`, 3s after load) does the tapping. Use distinct paths, as ever (rule 1), and
delete the routes afterwards.

## Cleaning up

```sh
xcrun simctl shutdown "$U"       # keep the device; booting a fresh one takes minutes
```
