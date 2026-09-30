---
name: ios-safari-gotchas
description: "Use when a page misbehaves in iPhone Safari (iOS 27, Liquid Glass) and desktop or headless tests can't show it: a flat color band or wrong tint behind the bottom toolbar, a dark footer cut off by a light strip, a flat strip under the collapsed toolbar, the wrong status-bar color or theme-color not working, a sticky or fixed hero sized to the viewport, safe-area insets that read 0 despite viewport-fit=cover, 100vh/dvh/svh/lvh confusion, scroll-linked JS that flashes during a flick or rubber-band, a transition stuck at first paint, a hairline at a seam under a sticky bar, a hero, overlay or animation that stops at the toolbar in some Safari tab layouts (Compact/Bottom/Top) but not others, a hero that pushes the next section a screen down, a reveal whose text turns ahead of it, headless timings that disagree with the phone, or a probe that keeps returning the same answer. Measured rules, fixes and simctl checks in the iOS simulator; read it before touching anything tied to a screen edge or scroll."
---

# iOS Safari Gotchas

Each of these was found on a real iPhone and then pinned down in the iOS simulator by
changing one thing at a time. Headless WebKit (Playwright) reproduced **none** of the
first three, and two of them ignore every property you would reach for first. When a
symptom below matches, don't reason from CSS — measure. The recipe is in
`references/verifying.md`.

A habit that would have saved most of the time: **iOS takes its colors from what is
painted, never from what you declare.** `theme-color` is ignored; the status bar and the
strip under the toolbar read the page itself, and keep reading it after load (§2, §10).
Flat fill (§1) is the exception: decided once, kept for the life of the page.

---

## 1. The strip behind the bottom toolbar

**Symptom.** Below the page, behind Safari's floating toolbar, there is a flat band of one
color with the page cut off at a hard edge above it. On other pages of the same site the
content runs on down behind a translucent toolbar. The band's color may be "right" on the
first screen and wrong on every screen after it.

**What is happening.** Safari keeps a strip at the foot of the screen for its chrome,
outside the layout viewport (no `env()` value describes it; the layout viewport starts
under the status bar and `100lvh` still stops ~58pt short of the screen's bottom edge — the
numbers are in §4, and how deep the strip is depends on the tab layout, §12). It paints
that strip one of two ways:

- **Overdraw** — it keeps painting the page there, under a translucent bar. The default.
- **Flat fill** — it stops the page at the layout viewport and fills the strip with one
  color, chosen at load, kept for the whole document.

It picks flat fill when **an element that is `position: sticky` or `position: fixed` is
the size of the dynamic viewport** (`inset: 0`, `100dvh`) — it reads that element as the
page's ground rather than as one section of it. `body { position: fixed; inset: 0 }`, the
classic scroll-lock shell, is exactly this. The fill color is that element's own paint,
never `theme-color`: a red 100dvh stage with a green `theme-color` filled red (iOS 27.0
simulator). A transparent stage with nothing opaque inside it did not flat-fill at all.

**It is a one-way ratchet.** The decision is taken the moment such an element exists and
is kept for the life of the page: two seconds of a fixed viewport-sized box — a loading
splash, a scroll lock, a modal shell — leaves every later screen in flat fill, including
screens reached by in-app navigation that never had such an element themselves. On a
single-page app this looks like "only routes loaded directly are fine." A modal backdrop
counts: a fixed `inset: 0` dim or a `<dialog>` opened mid-page flipped the strip to flat
fill in the dimmed color, on the phone and in the simulator (`probes/resample/`).

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
element's bottom edge already lands on that color:

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

Changing the fill *color* is not a fix. It turns a black band into a white one.

**Verify.** Put a loud color under the fold (`body { background: #ff00ff }`) and
screenshot mid-page in the simulator: magenta in the strip = overdraw, any flat color =
flat fill. If ablating a real page gets nowhere, build the suspect up on minimal pages
instead; eight of them found this rule after seventeen ablations had not
(`references/verifying.md`, "Bisecting").

---

## 2. The color behind the status bar

**Symptom.** The area behind the clock and battery is the wrong color for the page —
light over a dark masthead, say — while another page with a similar top gets it right.

**What is happening.** iOS samples what is painted at the top of the page, **and keeps
sampling**: a header recolored or inserted after load, a new `body` color, a fixed dim or
a `<dialog>` re-tinted the status bar within about 2s (iOS 27, a real 15 Pro Max with
website tinting on and off, and the simulator). What it counts, from the rule in
[joe-bell/apple-web-app](https://skills.sh/joe-bell/skills/apple-web-app) (WebKit source),
confirmed on the phone and the simulator by `probes/rule/`: the element at a point 4px
inside the top edge, if it spans at least 90% of the width. Alpha of 0.75 or more counts as
opaque; below that the color is blended over `body`. A narrower element, one stuck 8px
down, or a narrow fixed pill at the top center sends it to the fallback: `body`'s color —
or, on a real phone with "Allow Website Tinting" on, **black** on 10 of 14 loads of a
blurred-header page, whatever the tag said (0 of 3 with tinting off; never in the
simulator). Identical copies disagreed, so treat the black as a race.

**`theme-color` is never the answer on iOS 27.** Across those eleven loads the tag was
green, white, blue, dark slate, `body`'s own color, or absent, and its color never
appeared. Pages whose sample succeeded were pixel-identical with and without it on the
phone and in the simulator, in the status bar, the toolbar and the strip. Keep the tag for
other browsers if you like, but it is not a lever here, and a failed sample is not
something to design around: make the sample succeed (the fix below).

Also measured on real sites: a **`backdrop-filter`** on the top element failed the sample
even over an opaque ground; a **translucent sticky header** failed until painted solid; a
**fixed video or poster** at the top failed while present.

On a third site (iOS 27, iPhone 17 Pro) even a solid, unfiltered sticky header did not win
the sample. The rule above is the first thing to check there: a header under 90% wide, not
touching the top, or a narrow fixed element at the top center.

Once the page scrolls, on a page with nothing sticky the content shows through, frosted.
With a painted sticky header (translucent red, blurred) the sampled color stayed, bars
expanded or collapsed. A transparent sticky stage was mixed: frosted after a programmatic
scroll with the bars expanded, the sampled color after a swipe collapsed them (unresolved,
iOS 27.0 simulator). On a real phone the frost keeps a cast of the sampled color (magenta
read `d88adf`); in the simulator it was neutral gray. Read the status bar at `scrollY` 0.

**Fix, in order.** Give the element under the status bar a solid `background-color`, full
width, touching the top edge — that is what the sampler reads most reliably. If it still falls back, remove that element's
`backdrop-filter` (invisible behind a ≥ 95%-opaque ground anyway). If a media layer is
what sits there, accept the fallback and make `body`'s background match the ground (§10).

**Diagnose, don't assume.** Paint the top element one loud color and `body` a different
one, on their own probe path: the status bar then tells you whether you got a sample or a
fallback. Probe colors that match the page's own ground tell you nothing.

---

## 3. Safari caches these decisions per URL

Both colors above are remembered **per URL path**. Probing variants through query strings
(`?variant=b`) returns the first load's answer every time and sends you down false
trails — it did here for a dozen probes. Serve each variant under its own path
(`/p/variant-b/`).

Also: the simulator's first shot after launching Safari is unreliable, and a freshly
booted device can time out or crash every page (`references/verifying.md`, "The loop").

---

## 4. Viewport units and insets — the real numbers

The tables — per phone, per tab layout, portrait and landscape, simulator and a real
15 Pro Max — are in `references/viewport-numbers.md`. Read them before sizing anything to
the viewport. What they establish:

- **The strip below the layout viewport is set by the tab layout, not the phone**: 98pt
  with the Compact bar, 158pt with the Bottom bar (§12).
- **The layout viewport starts 59–62pt down**, under the status bar, so
  `screen.height - innerHeight` over-estimates the bottom strip: safe at an edge.
- **`100lvh` stops 58pt above the screen's bottom edge** in every layout.
- **Portrait insets all read 0.** Landscape sides are 59–62px by model, bottom 20;
  Playwright fakes 47.
- **`vh` overshoots** by 40pt portrait, 110pt landscape.
- **`dvh` for a viewport-sized stage, not `svh`**, which stops 110pt short in landscape.
- **No `min-height` on a viewport-sized element**: a 22rem floor overrode a 292px
  landscape viewport and put a clipping bug back.
- Playwright's WebKit models none of `svh`, `dvh` or `env()`. Check them in the simulator.

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
*previous* color for a second or more, then snaps. WebKit only.

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
- **Expecting a color change after load to be ignored.** The status bar and a plain strip
  follow it within about 2s (§2, §10); only a ratcheted flat fill keeps its color (§1).

---

## 9. Testing pitfalls that produce false results

Headless WebKit fires no `scroll` event for `scrollTo()` and barely advances animations,
and an eyeballed screenshot is a guess where a sampled pixel is a fact. Read
`references/testing-pitfalls.md` before trusting a headless result or building a harness.

---

## 10. The strip's color is `body`'s — and so is the status bar's, unless the top claims it

**Symptom.** A page that ends on a dark full-bleed band shows a light strip under the band
at the foot of the screen with the toolbar expanded — the band cut off at a hard edge. Or,
after "fixing" that with a dark ground: with the toolbar collapsed to its pill, *every*
screen of *every* page shows a flat dark strip under the pill with the page cut off above
it, and the status bar is black on pages that are light.

**What is happening.** This is the strip from §1 on an ordinary page — no viewport-sized
sticky, no ratchet. Safari still keeps a strip at the foot of the screen below the layout
viewport (98pt with the Compact bar, 158pt with the Bottom bar — §4, §12).
With the toolbar **expanded** the page paints on down into it, and only past the document's
end does Safari paint something else: `body`'s background color. With the toolbar
**collapsed** to its pill the page was seen, on a phone, to stop at the layout viewport with
the whole strip in `body`'s color, on every screen — so a `body` that is dark cut every
page off, and a `body` that is light cut a dark footer off.

That collapsed-pill reading is from a real phone on a real page and has not been pinned
down. In the iOS 27.0 simulator it does not reproduce. Seven probe pages were collapsed to
the pill by a swipe, on an 18 Pro (Compact) and a 15 Pro Max (Bottom). They had nothing
sticky, a translucent blurred sticky header, or a transparent sticky 100dvh stage. Every
one painted its stripes under the pill to the screen's last row, with no `body` strip.
Only an *opaque* 100dvh sticky stage changed it, and that was §1's flat fill in the
stage's own color, not `body`'s. A real iPhone 15 Pro Max (Bottom bar, collapsed to the
pill) agreed: stripes to the last row on the plain page, the blurred-header page and the
transparent-stage page. So the flat strip in the original report came from something on
that page, most likely an opaque viewport-sized sticky or fixed element (§1). Look for one
before building on the flat strip.

Measured (iOS 27, iPhone 17 Pro, sampling the strip at max scroll): **nothing else reaches
it.** A background on `html` — no. `theme-color` — no. A `position: fixed` sheet hung below
the viewport (`bottom: -220px`) — clipped to the layout viewport, no. A solid, unfiltered
sticky header — no. A gradient on `body` with no `background-color` — Safari gives up and
paints **both ends white**. Only `body`'s computed `background-color`, and it is re-read
**live**: set it 3s after load and the strip follows.

The status bar falls back to the same color, **also live** (§2): a `body` change re-tinted
it within about 2s on a real 15 Pro Max, tinting on and off, and in the simulator. An
earlier reading on a 17 Pro, that it kept its load-time color, did not reproduce on any
probe. So a `body` swap for the strip recolors the status bar too, unless something at the
top wins the sample.

**Fix.** Claim the top with a sampled element (§2's rule), move the page's ground to a
wrapper (`.page`), and make `body` follow whatever is at the bottom edge of the layout
viewport, every frame, on coarse pointers only. Each half is measured
(`probes/resample/`); the combination has not been probed as one page, so check it:

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
.masthead { position: sticky; top: 0; background: var(--light); }   /* holds the status bar */
body      { background: var(--light); }   /* the strip under the toolbar follows this */
.page     { background: var(--light); }   /* what the page is actually seen on */
```

Three guards, each of which was a bug without it:

- **Gate the first change on a gesture** — the first `touchstart`, `wheel` or `keydown`
  after `load`, with a ~3s fallback for a page reloaded at the bottom and left alone. Not
  on `scroll`: a reload restores the scroll position and fires `scroll` with no finger on
  the glass, and a swap timed from `load` landed while the page opened, turning the status
  bar dark on some reloads and not others.
- **Hold the release.** The edge jitters for a frame or two at the end of a flick and past
  the end of the document; a binary compare flickered the strip between the two colors.
- **Reset on `pagehide`, re-arm on `pageshow`** so a page restored from the back-forward
  cache does not open on the dark `body`.

Desktop is untouched by the gate: the only place `body` shows there is the rubber-band
past either end, which stays the page's own ground.

**Verify.** `references/verifying.md`, "Swap after load", "Reload from the bottom" and
"Collapsing the toolbar": only a swipe collapses the bars, never `scrollTo`, and with them
expanded every variant paints through mid-page. When the simulator and the phone disagree,
trust the phone and say so.

---

## 11. A hairline of ground at a measured seam

**Symptom.** A 1px line of the page's own ground color along the top edge of a full-bleed
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
different color, so the eye lands on it. The bug itself is everywhere.

**Fix.** Publish the height with its fraction intact —
`bar.getBoundingClientRect().height`, never `offsetHeight` or `clientHeight` — or pull a
pixel further than measured and let the bar cover the overlap. Rounding *up* is the safe
direction at a seam; rounding down is the one that shows ground.

**Or keep it, and then draw it.** Between Safari's chrome and a dark first act this line
is the only edge saying where the page begins, and it is worth having on purpose — where
it is a 1px rule in the ground color at the section's top, under the bar's own gradient,
which lands on the same value the rounding produced. Scope it to `(pointer: coarse)`: on a
desktop there is no chrome up there for it to answer, and the accident never happened
there anyway, because the bar was always a whole number of pixels tall.

**Verify.** Sample the pixel column down the gutter and print only the transitions, in
device rows and CSS px (`references/verifying.md`, "A transition map down one column").
The whole difference is one row; "looks the same" is not a reading. A line that moves
when the bar's height changes is this bug, not a design.

---

## 12. The page runs on under the toolbar to the screen's edge — how far depends on the tab layout

**Symptom.** Something meant to cover the whole screen — a hero sized "a bit past the
viewport", a clip-path reveal or color sweep, an overlay — stops in a hard line at the top
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

Anything that animates *to* that edge — a circle's radius, the moment a color is handed to
`body` (§10) — must measure the same edge, e.g. with a hidden probe inside the section that
inherits `--over`, not from `innerHeight`.

**What the overhang covers has to wait for the effect too.** Once the section is no taller
than its content, the next section's ground and text sit on the first screen, down behind
the toolbar, and turn ahead of the sweep unless held: the layer must carry the old state's
ground, and the text under it must keep its old ink until the edge reaches it. The rules,
the edge-distance code for a circle reveal and the filmed timings are in
`references/reveal-ink.md`.

**Verify.** First ask which tab layout the reporter uses; it changes the answer. Set the
same layout in the simulator (it defaults to Compact), then sample the bottom rows of your
page mid-animation: stripes to the last row and no band of the next section behind the bar
is the pass. For the order in which things turn, film it (`references/verifying.md`,
"Safari's tab layout" and "Filming an effect").
