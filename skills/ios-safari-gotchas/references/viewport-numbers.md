# Viewport units and insets: the measured numbers

Detail for SKILL.md §4. Section numbers refer to SKILL.md. Units are CSS px (= pt on these
phones). Simulator figures are iOS 27.0; real-phone figures are marked.

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

Landscape on a real iPhone 15 Pro Max (iOS 27, Bottom bar): window 320 with Safari's
chrome showing, 430 (the screen's full short side) once it hides; `svh` 320, `dvh` 320 →
430, `lvh`/`vh` 430; insets 0 / 59 / 20 / 59. In landscape Safari swaps to a top bar with
a tab row, and with website tinting on it paints that whole bar in `body`'s color.

And portrait by Safari tab layout (iOS 27.0 simulator, toolbar expanded unless noted;
the 15 Pro Max Bottom and pill columns match a real phone exactly) — see §12:

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
  Max, 62pt on both 18s. What shows above it is `body`'s color (§2, §10). So
  `screen.height - innerHeight` is the strip at the bottom *plus* the status bar — an
  over-estimate by 59–62pt, which is the safe direction for anything that must reach the
  edge.
- **`100lvh` stops 58pt above the screen's bottom edge** in every column above (e.g.
  932 − 59 − 815), whatever the tab layout. It is not "the screen".
- **Portrait reports all four `env(safe-area-inset-*)` as 0.** Safari reserves its own
  chrome rather than handing the page an inset. Insets only become real in landscape, and
  the side value follows the phone's status-bar depth: 62px on a 17 Pro, 59px on a 15 Pro
  Max. Playwright's device descriptors fake 47.
- **`vh` overshoots** by 40pt portrait, 110pt landscape. A `vh`-sized hero hangs its bottom
  content that far below the screen.
- **`dvh` for a viewport-sized stage; not `svh`.** In landscape Safari hides its chrome
  almost entirely (entirely, on a 15 Pro Max) and an `svh` stage stops 110pt short, with
  the parent's ground exposed.
- **No `min-height` on a viewport-sized element.** A 22rem floor silently overrode a
  292px landscape viewport and put a clipping bug back.
- Playwright's WebKit models none of `svh`, `dvh`, or `env()`. Anything depending on them
  is checked in the simulator, not the sweep.
