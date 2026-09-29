---
name: ios-safari-gotchas
description: "Use when a page misbehaves in iPhone Safari (iOS 26/27, Liquid Glass) and desktop or headless tests can't show it: a flat colour band or wrong tint behind the bottom toolbar, a dark footer cut off by a light strip, a flat strip under the collapsed toolbar, the wrong status-bar colour or theme-color not working, a sticky or fixed hero sized to the viewport, safe-area insets that read 0 despite viewport-fit=cover, 100vh/dvh/svh/lvh confusion, scroll-linked JS that flashes during a flick or rubber-band, a transition stuck at first paint, a hairline at a seam under a sticky bar, a hero, overlay or animation that stops at the toolbar in some Safari tab layouts (Compact/Bottom/Top) but not others, a hero that pushes the next section a screen down, a reveal whose text turns ahead of it, headless timings that disagree with the phone, or a probe that keeps returning the same answer. Measured rules, fixes and simctl checks in the iOS simulator; read it before touching anything tied to a screen edge or scroll."
---

# iOS Safari Gotchas

Each of these was found on a real iPhone and then pinned down in the iOS simulator by
changing one thing at a time. Headless WebKit (Playwright) reproduced **none** of the
first three, and two of them ignore every property you would reach for first. When a
symptom below matches, don't reason from CSS — measure. The recipe is in
`references/verifying.md`.

A habit that would have saved most of the time: **iOS decides several colours once, at
load, from what is painted at that moment, and keeps them for the life of the page.**
Anything you change afterwards is ignored, and so is anything you *declare* — it samples
what it sees.

---

## 1. The strip behind the bottom toolbar

**Symptom.** Below the page, behind Safari's floating toolbar, there is a flat band of one
colour with the page cut off at a hard edge above it. On other pages of the same site the
content runs on down behind a translucent toolbar. The band's colour may be "right" on the
first screen and wrong on every screen after it.

**What is happening.** Safari keeps a strip at the foot of the screen for its chrome,
outside the layout viewport (no `env()` value describes it; the layout viewport starts
under the status bar and `100lvh` still stops ~58pt short of the screen's bottom edge — the
numbers are in §4, and how deep the strip is depends on the tab layout, §12). It paints
that strip one of two ways:

- **Overdraw** — it keeps painting the page there, under a translucent bar. The default.
- **Flat fill** — it stops the page at the layout viewport and fills the strip with one
  colour, chosen at load, kept for the whole document.

It picks flat fill when **an element that is `position: sticky` or `position: fixed` is
the size of the dynamic viewport** (`inset: 0`, `100dvh`) — it reads that element as the
page's ground rather than as one section of it. `body { position: fixed; inset: 0 }`, the
classic scroll-lock shell, is exactly this. The fill colour is that element's own paint,
never `theme-color`: a red 100dvh stage with a green `theme-color` filled red (iOS 27.0
simulator). A transparent stage with nothing opaque inside it did not flat-fill at all.

**It is a one-way ratchet.** The decision is taken the moment such an element exists and
is kept for the life of the page: two seconds of a fixed viewport-sized box — a loading
splash, a scroll lock, a modal shell — leaves every later screen in flat fill, including
screens reached by in-app navigation that never had such an element themselves. On a
single-page app this looks like "only routes loaded directly are fine."

**Measured tolerance** (iPhone, iOS 27, 714pt dynamic viewport): flat fill holds at
`100dvh`, `100svh`, `calc(100dvh - 1px)`, `+8px`, `+24px`. Overdraw returns at `-8px`,
`-16px`, `+48px`, and `100lvh` — for sticky and for fixed alike. `html { overflow: hidden }`
on its own does not trigger it.

**What does not touch it** — don't spend time here: `<meta name="theme-color">` (set to
magenta, removed — no change), a background on `html` or `body`, `color-scheme`, making
the sticky element transparent (it takes the opaque child instead), and any change after
load (setting the background 3s in does nothing). That list is for the *ratchet*. Outside
it — an ordinary page with no viewport-sized sticky — `body`'s background is exactly what
the strip reads, live, and it is the way to control it. See §10.

**Fix.** Stop sizing the sticky element to exactly the viewport. The cheapest escape is to
make it slightly short and let the parent's ground show under it — invisible if the
element's bottom edge already lands on that colour:

```css
.stage {
  position: sticky; top: 0;
  /* short of the viewport on purpose — see iOS Safari Gotchas §1 */
  height: calc(100vh  - max(12px, 1.5vh));   /* fallback */
  height: calc(100dvh - max(12px, 1.5dvh));
}
```

The `max()` covers both a fixed-pixel and a proportional tolerance; both were inside what
was measured. For a fixed shell that must cover the screen (a scroll lock, a game board),
go the other way: size the fixed root to `100lvh` or taller — the extra runs under the
toolbar, which is where you wanted it anyway — and lay the visible UI out in a *static*
child at `100dvh` so bottom-anchored controls stay put. Never lock scrolling by fixing
`body`; fix a child sized past the viewport instead.

Changing the fill *colour* is not a fix. It turns a black band into a white one.

**Verify.** Put a loud colour under the fold (`body { background: #ff00ff }`) and
screenshot mid-page in the simulator. Magenta in the strip = overdraw. Any flat colour =
still flat fill. When ablating one property at a time on a real page gets nowhere, build
the suspect construct up on a minimal page instead — apply it for two seconds, remove it,
scroll — with a no-construct control and a sticky-100dvh positive control. Eight such
pages found the rule above in one simulator window after seventeen on-page ablations
had not. Details in `references/verifying.md`.

---

## 2. The colour behind the status bar

**Symptom.** The area behind the clock and battery is the wrong colour for the page —
light over a dark masthead, say — while another page with a similar top gets it right.

**What is happening.** iOS samples what is painted at the top of the page, at load, and
latches it. When the sample fails it falls back to `body`'s background colour.
**`theme-color` plays no part on iOS 27**: with a translucent, blurred sticky header (the
failing case below) and `theme-color` `#00ff00`, the status bar read `body`'s magenta,
pixel for pixel the same as without the tag, and no green appeared in the status bar,
the toolbar or the strip on any of seven probe pages (iOS 27.0 simulator, "Allow Website
Tinting" on). Keep the tag for other browsers if you like, but it is not a lever here.

What makes the sample fail differs by page, and the same three probes settle it every time
(loud colours, distinct paths — see §3):
- A **`backdrop-filter`** on the element at the top. Measured on one site: a masthead at
  96% near-black with `blur(12px)` → light status bar; filter removed → sampled to the
  bar's own colour; opaque with the filter kept → still light.
- A **sticky header with a translucent ground**, blur or not. Measured on another site:
  removing the blur changed nothing; making the header static made the sample succeed;
  and painting the sticky header a solid `background-color` (`#0000ff` as a probe) made the
  sample read exactly that colour, blur kept.
- A **fixed media layer** (video/poster) at the top: hidden, the sample succeeds; present,
  it falls back.

On a third site (iOS 27, iPhone 17 Pro) none of that mattered: the status bar followed
`body`'s background colour, full stop — a solid, unfiltered sticky header did not win the
sample back, `theme-color` did not override it, and it was read once, at load, and never
again. That is the same colour the bottom strip reads live, and the timing difference is
what makes §10 possible.

**Fix, in order.** Give the element under the status bar a solid `background-color` — that
is what the sampler reads most reliably. If it still falls back, remove that element's
`backdrop-filter` (invisible behind a ≥ 95%-opaque ground anyway). If a media layer is
what sits there, accept the fallback and make `body`'s background match the ground (§10).

**Diagnose, don't assume.** Paint the top element one loud colour and `body` a different
one, on their own probe path: the status bar then tells you whether you got a sample or a
fallback. Probe colours that match the page's own ground tell you
nothing.

---

## 3. Safari caches these decisions per URL

Both colours above are remembered **per URL path**. Probing variants through query strings
(`?variant=b`) returns the first load's answer every time and sends you down false
trails — it did here for a dozen probes. Serve each variant under its own path
(`/p/variant-b/`).

Also: the first screenshot after launching Safari in the simulator is unreliable (blank,
or the start page). Launch Safari, wait, then open the URL and wait again. On a device that
has just booted, `simctl openurl` can fail with "Operation timed out" and leave a white
page that never paints — or "This webpage was reloaded because a problem occurred" on
every URL, example.com included. That is the simulator, not your page: terminate Safari,
launch it, wait ~10s, then open the URL.

---

## 4. Viewport units and insets — the real numbers

Measured on an iPhone 17 Pro, iOS 27, mobile Safari:

```
                portrait        landscape
insets T/R/B/L  0 / 0 / 0 / 0   0 / 62 / 20 / 62
100svh          714             292
100lvh          754             402
100dvh          714             292   (402 once Safari hides its chrome)
100vh           754             402
client w x h    402 x 714       874 x 292
```

And portrait by Safari tab layout (iOS 27.0 simulator, toolbar expanded unless noted) —
see §12:

```
                         15 Pro Max               18 Pro Max   18 Pro
                         Compact  Bottom  pill*   Compact      Bottom
screen.height            932      932     932     956          874
page top (y=0 on screen) 59       59      59      62           62
innerHeight / 100dvh     775      715     815     796          654
100svh                   775      715     715     796          654
100lvh / 100vh           815      815     815     836          754
page drawn down to       932      932     932     956          874    (the screen's last row)
strip below innerHeight  98       158     58      98           158
insets T/B               0/0      0/0     0/0     0/0          0/0
```
`*` the Bottom bar collapsed to its pill by one swipe (injected touch; `scrollTo` never
collapses the bars). `innerHeight` and `dvh` follow the bars; `svh` and `lvh` do not.

- **The strip below the layout viewport is set by the tab layout, not the phone**: 98pt
  with the Compact bar, 158pt with the Bottom bar, on every phone measured.
- **The layout viewport starts under the status bar**: page y=0 is 59pt down on a 15 Pro
  Max, 62pt on both 18s. What shows above it is `body`'s colour (§2, §10). So
  `screen.height - innerHeight` is the strip at the bottom *plus* the status bar — an
  over-estimate by 59–62pt, which is the safe direction for anything that must reach the
  edge.
- **`100lvh` stops 58pt above the screen's bottom edge** in every column above (e.g.
  932 − 59 − 815), whatever the tab layout. It is not "the screen".
- **Portrait reports all four `env(safe-area-inset-*)` as 0.** Safari reserves its own
  chrome rather than handing the page an inset. Insets only become real in landscape, and
  the real side value is 62px — Playwright's device descriptors fake 47.
- **`vh` overshoots** by 40pt portrait, 110pt landscape. A `vh`-sized hero hangs its bottom
  content that far below the screen.
- **`dvh` for a viewport-sized stage; not `svh`.** In landscape Safari hides its chrome
  almost entirely and an `svh` stage stops 110pt short, with the parent's ground exposed.
- **No `min-height` on a viewport-sized element.** A 22rem floor silently overrode a
  292px landscape viewport and put a clipping bug back.
- Playwright's WebKit models none of `svh`, `dvh`, or `env()`. Anything depending on them
  is checked in the simulator, not the sweep.

---

## 5. Scroll-linked JS during a flick

**Symptom.** State that follows scroll position (a header that inverts over a dark band,
say) paints a frame or more behind the page during momentum scrolling — a flash.

**What is happening.** Scrolling runs on the compositor; the `scroll` event is delivered
late during a fling. A handler that computes state in that event is behind the frame that
was already painted.

**Fix.** Drive the check from `requestAnimationFrame` while the page is moving. rAF runs
in step with the frames and reads the position each will paint. Start the loop on
`touchstart` and `wheel` too, so it is already up when the fling begins, and stand it down
after a few still frames.

```js
let running = false, still = 0, seen = -1;
const frame = () => {
  if (scrollY === seen) still++; else { still = 0; seen = scrollY; }
  sync();
  if (still > 10) { running = false; return; }
  requestAnimationFrame(frame);
};
const follow = () => { still = 0; if (!running) { running = true; requestAnimationFrame(frame); } };
addEventListener('scroll', follow, { passive: true });
addEventListener('touchstart', follow, { passive: true });
addEventListener('wheel', follow, { passive: true });
```

**And make the state asymmetric.** Take the safe state the instant the geometry says so;
give it up only after the geometry has said otherwise for a beat (~120ms), with a timeout
so the release still lands after the loop stops. One odd frame then can't flash.

---

## 6. The rubber band

**Symptom.** Scroll-position logic misfires exactly at the end of a hard flick to the top
(or bottom).

**What is happening.** iOS lets the page overscroll past its own limits and reports the
position outside the document: `scrollY < 0` at the top, `> max` at the bottom. Every
`getBoundingClientRect()` moves with it, so an element still filling the screen measures
as having slipped. Making the scroll handling *faster* (§5) makes this land sooner, not go
away — "it's a timing issue" was the user's read, and it was the bounce.

**Fix.** Take the overscroll back out before measuring:

```js
const bounce = () => {
  const max = document.documentElement.scrollHeight - innerHeight;
  return scrollY < 0 ? scrollY : (scrollY > max ? scrollY - max : 0);
};
const b = bounce();
const r = el.getBoundingClientRect();
const top = r.top + b, bottom = r.bottom + b;   // where it would be at rest
```

---

## 7. Transitions started before first paint

**Symptom.** An element whose state is set by a script before first paint shows its
*previous* colour for a second or more, then snaps. WebKit only.

**What is happening.** WebKit starts a CSS transition for the opening state — which is not
a change and should not animate — and parks it at `currentTime: 0`. Measured still
unresolved at 1s, done by 3s.

**Fix.** Settle the first state with transitions off, force a layout read to commit it,
then re-enable:

```js
el.setAttribute('data-boot', '');
applyInitialState();
void el.offsetHeight;
el.removeAttribute('data-boot');
```
```css
[data-boot] .thing { transition: none; }
```

---

## 8. Things that looked like fixes and were not

- **CSS scroll-driven animations for the state swap.** Every mechanism passed in
  isolation in WebKit (`scroll(root)`, `var()` in `animation-range`, custom-property
  keyframes) — and on the real page the timeline sat inactive (`progress` 0, then `null`).
  Cross-element named view timelines via `timeline-scope` did not drive at all in WebKit.
  Keep a JS path; treat scroll timelines as an enhancement you verify on device.
- **Changing a latched colour dynamically.** Ignored, both for the strip and the status
  bar.
- **Fixing the colour of the flat fill instead of the mode.** See §1.

---

## 9. Testing pitfalls that produce false results

Headless WebKit fires no `scroll` event for `scrollTo()` and barely advances animations,
harnesses that scroll inside rAF measure their own ordering, and a screenshot you eyeball
is a guess where a sampled pixel is a fact. Read `references/testing-pitfalls.md` before
trusting any headless result or building a harness for §5–§7.

---

## 10. The strip's colour is `body`'s — and so is the status bar's, once

**Symptom.** A page that ends on a dark full-bleed band shows a light strip under the band
at the foot of the screen with the toolbar expanded — the band cut off at a hard edge. Or,
after "fixing" that with a dark ground: with the toolbar collapsed to its pill, *every*
screen of *every* page shows a flat dark strip under the pill with the page cut off above
it, and the status bar is black on pages that are light.

**What is happening.** This is the strip from §1 on an ordinary page — no viewport-sized
sticky, no ratchet. Safari still keeps a strip at the foot of the screen below the layout
viewport (98pt with the Compact bar, 158pt with the Bottom bar — §4, §12).
With the toolbar **expanded** the page paints on down into it, and only past the document's
end does Safari paint something else: `body`'s background colour. With the toolbar
**collapsed** to its pill the page was seen, on a phone, to stop at the layout viewport with
the whole strip in `body`'s colour, on every screen — so a `body` that is dark cut every
page off, and a `body` that is light cut a dark footer off.

That collapsed-pill reading is from a real phone on a real page and has not been pinned
down. A plain probe page (stripes, magenta `body`, nothing sticky) collapsed to the pill by
a swipe in the iOS 27.0 simulator painted its stripes under the pill to the screen's last
row, with no `body` strip at all. Before building on the flat strip, check whether
something on the page — a sticky or fixed element (§1) — is what flattens it there.

Measured (iOS 27, iPhone 17 Pro, sampling the strip at max scroll): **nothing else reaches
it.** A background on `html` — no. `theme-color` — no. A `position: fixed` sheet hung below
the viewport (`bottom: -220px`) — clipped to the layout viewport, no. A solid, unfiltered
sticky header — no. A gradient on `body` with no `background-color` — Safari gives up and
paints **both ends white**. Only `body`'s computed `background-color`, and it is re-read
**live**: set it 3s after load and the strip follows.

The status bar reads the same colour — but **once, at load, and never again** (§2, third
case). That asymmetry is the whole trick: what the page loads with is what the status bar
keeps; what `body` is afterwards is what the strip shows.

**Fix.** Move the page's ground to a wrapper (`.page`), and make `body` follow whatever is
at the bottom edge of the layout viewport, every frame, on coarse pointers only:

```js
// inside the rAF loop from §5, alongside the top-edge check
let under = false;
for (const el of document.querySelectorAll('[data-dark]')) {
  const r = el.getBoundingClientRect(), top = r.top + b, bottom = r.bottom + b;   // b: §6
  // the last element in the document owns everything below its top, bounce included;
  // a band with page after it must also still reach the edge. 2px of slack: at max
  // scroll the band's bottom and the viewport's agree only to the subpixel, and an
  // exact compare went light at the very end and flickered on the way there.
  if (top <= innerHeight + 2 && (el === last || bottom >= innerHeight - 2)) under = true;
}
ground(armed && under);   // asymmetric like §5: take dark at once, release after ~120ms
```

```css
body  { background: var(--light); }   /* what the status bar latches */
.page { background: var(--light); }   /* what the page is actually seen on */
```

Three guards, each of which was a bug without it:

- **Gate the first change on a gesture** — the first `touchstart`, `wheel` or `keydown`
  after `load`, with a ~3s fallback for a page reloaded at the bottom and left alone. Not
  on `scroll`: a reload restores the scroll position and fires `scroll` with no finger on
  the glass, and with everything cached `load` comes early enough that Safari's UI is still
  taking colour updates when a swap timed from it lands. It latched the dark colour on some
  reloads and not others.
- **Hold the release.** The edge jitters for a frame or two at the end of a flick and past
  the end of the document; a binary compare flickered the strip between the two colours.
- **Reset on `pagehide`, re-arm on `pageshow`** so a page restored from the back-forward
  cache does not hand the status bar the dark colour to latch.

Desktop is untouched by the gate: the only place `body` shows there is the rubber-band
past either end, which stays the page's own ground.

**Verify.** `references/verifying.md`, "Swap after load" and "Reload from the bottom". The
collapsed pill needs a swipe: injected touch (`idb ui swipe`, or a simulator tool's swipe)
collapses the bars in the simulator; a programmatic `scrollTo` never does, and with the
toolbar expanded the page paints through mid-page in *every* variant, so a one-time swap
looks fine there. When the simulator and the phone disagree, trust the phone and say so.

---

## 11. A hairline of ground at a measured seam

**Symptom.** A 1px line of the page's own ground colour along the top edge of a full-bleed
section that is supposed to run *under* a sticky bar. It comes and goes with the bar's
height — there at one phone width, gone at another, never on desktop — and no headless
screenshot shows it, because at 1x the fraction that causes it rounds away.

**What is happening.** The section is pulled up under the bar by a negative margin taken
from the bar's measured height:

```js
const h = bar.offsetHeight;                 // 84  — the bar is 84.1875
root.style.setProperty('--masthead-real', h + 'px');
```

`offsetHeight` is an integer. A bar whose real height is fractional — a row that wraps, a
variable font's line box, a border on a subpixel boundary — leaves the difference
uncovered, and what shows through is whatever is painted behind the section. Here 0.19px,
which at 3x is one device row of antialiasing: an exact hairline. Measured: `92,95,96` in
a field of `21,24,26`, the page's ground seen through the bar's 66% vignette.

Only the visibility is iOS's doing — a fifth of a CSS pixel is paintable at 3x, and the
line sits directly under the strip Safari paints behind the status bar (§10), which is a
different colour, so the eye lands on it. The bug itself is everywhere.

**Fix.** Publish the height with its fraction intact —
`bar.getBoundingClientRect().height`, never `offsetHeight` or `clientHeight` — or pull a
pixel further than measured and let the bar cover the overlap. Rounding *up* is the safe
direction at a seam; rounding down is the one that shows ground.

**Or keep it, and then draw it.** Between Safari's chrome and a dark first act this line
is the only edge saying where the page begins, and it is worth having on purpose — where
it is a 1px rule in the ground colour at the section's top, under the bar's own gradient,
which lands on the same value the rounding produced. Scope it to `(pointer: coarse)`: on a
desktop there is no chrome up there for it to answer, and the accident never happened
there anyway, because the bar was always a whole number of pixels tall.

**Verify.** Sample the pixel column down the gutter and print only the transitions, in
device rows and CSS px (`references/verifying.md`, "A transition map down one column").
The whole difference is one row; "looks the same" is not a reading. A line that moves when the bar's height changes is this bug, not a design.

---

## 12. The page runs on under the toolbar to the screen's edge — how far depends on the tab layout

**Symptom.** Something meant to cover the whole screen — a hero sized "a bit past the
viewport", a clip-path reveal or colour sweep, an overlay — stops in a hard line at the top
edge of Safari's bottom bar, with the next section (or `body`) showing behind the bar. It
reproduces on one person's phone and not on yours, or not in the simulator, and the phone
model turns out not to be the difference. Or, once it does reach the edge: the next section
now starts a screen below the hero's content, or its text and ground turn ahead of the
sweep behind the toolbar.

**What is happening.** iOS 27 Safari draws the page past the layout viewport, under its
translucent bottom chrome, to the screen's last row — with the Compact bar, the Bottom bar,
and the Bottom bar collapsed to its pill (Settings › Apps › Safari › Tabs; the third choice,
Top, has not been measured). What changes with the layout is how tall the layout
viewport is, so the depth of that strip below `innerHeight` changes with it: **98pt with
the Compact bar, 158pt with the Bottom bar**, on every phone measured (§4). Anything sized
off the viewport plus a constant is tuned to whichever layout it was tested in.

Measured on a 15 Pro Max: a hero at `max(100lvh, 100svh + 96px)` ended 2pt short of the
screen's edge in Compact — invisible — and **58pt short in Bottom** (there `100lvh` wins,
874pt on screen), so a day/night sweep stopped at the bar's top edge on the reporter's
phone. An 18 Pro Max in the simulator looked fine because it was in Compact, the
simulator's default. `100lvh` is no escape: it is the same in every layout and stops 58pt
above the edge (§4).

**Fix.** Size the overhang from the screen, once at load and again on rotation — not as the
bars collapse, or it jumps with the toolbar:

```js
const coarse = matchMedia('(pointer: coarse)');
const land = matchMedia('(orientation: landscape)');
const reach = () => {
  if (!coarse.matches) return;
  // screen.width/height don't swap on rotation; pick the side that is vertical now
  const sh = land.matches ? Math.min(screen.width, screen.height) : Math.max(screen.width, screen.height);
  // counts the status bar too (59–62pt), so it errs long — the safe side at an edge
  hero.style.setProperty('--over', `${Math.max(96, Math.ceil(sh - innerHeight) + 8)}px`);
};
reach();
land.addEventListener('change', () => setTimeout(reach, 350));   // let innerHeight settle
```

Put that reach on the layer the effect paints in, not on the section that holds it. A hero
given `min-height: max(100lvh, 100svh + var(--over))` is taller than its content in the
flow, so everything after it moves down by the difference: 320pt of bare ground under a
hero's last content on a 390×844 page with the 96px fallback, and ~130pt more with the
Bottom bar's measured overhang (~225px on a 15 Pro Max). Let the section keep its own
height and hang the layer past it instead:

```css
.hero {
  position: relative;          /* its content's height, nothing more */
  --over: 96px;                /* no-JS fallback: 2pt short with the Compact bar, 58pt with Bottom */
}
.hero__layer {                 /* what the reveal, sweep or overlay paints in */
  position: absolute;
  inset: 0 0 auto;
  height: max(100%, 100vh);
  height: max(100%, 100lvh, calc(100svh + var(--over)));   /* svh: must not move as bars collapse */
  overflow: hidden;
  background: var(--before);   /* the old state's ground; see below */
}
.hero ~ section { position: relative; z-index: 1; }   /* the content it overhangs stays on top */
```

The `z-index` is not optional: a positioned layer paints over later siblings that are not
positioned, so without it the overhang covers the next section's text.

Anything that animates *to* that edge — a circle's radius, the moment a colour is handed to
`body` (§10) — must measure the same edge, e.g. with a hidden probe inside the section that
inherits `--over`, not from `innerHeight`.

**What the overhang covers has to wait for the effect too.** Once the section is no taller
than its content, the next section's ground and text sit on the first screen, down behind
the toolbar, and turn ahead of the sweep unless held: the layer must carry the old state's
ground, and the text under it must keep its old ink until the edge reaches it. The rules,
the edge-distance code for a circle reveal and the filmed timings are in
`references/reveal-ink.md`.

**Verify.** Ask which tab layout the reporter uses before anything else; it is one tap in
Settings and changes the answer. Then set the same layout in the simulator (it defaults to
Compact; `references/verifying.md`, "Safari's tab layout"), load a striped probe page and
read where the stripes stop, and sample the bottom rows of your page mid-animation. Stripes
to the last row and no band of the next section behind the bar is the pass. For the order
in which things turn (the strip, the band under the section, the text), film it instead
(`references/verifying.md`, "Filming an effect") and read the frames against each other.
