# Holding what the overhang covers until the effect reaches it

Detail for SKILL.md §12: a hero whose reveal or sweep layer hangs past the section, down
behind Safari's bottom toolbar. Section numbers refer to SKILL.md.

**What the overhang covers has to wait for the effect too.** Once the section is no taller
than its content, the next section's ground and text are on the first screen, and down in
the strip behind the toolbar. Two rules, each a visible fault on the phone without it:

- **The layer carries the old state's ground.** Otherwise what shows through it is the page's
  own ground, which changes on its own schedule. A `background-color` transition on the page
  turned the strip behind the Bottom bar halfway to the new color while a circle reveal was
  still in the top of the hero. With the old ground on the layer, the strip waits for the
  circle.
- **Text under the overhang keeps its old ink until the edge reaches it.** Hold it with an
  attribute that re-declares the old state's color tokens on that section. Release it when
  the edge first touches the section's text *on screen*: the union of its text boxes, from
  the first one's top down to the screen's bottom edge. A growing circle first touches that
  box at its nearest point to the center; a shrinking one first leaves it at its farthest.
  Then fade the ink quickly (150ms).

```js
// cx, cy: the circle's center; H: the screen's bottom edge, as measured above
const onScreen = (section, H) => {
  const qs = [...section.querySelectorAll('p, h2, h3, li')].map((e) => e.getBoundingClientRect());
  const top = Math.min(...qs.map((q) => q.top));
  return { l: Math.min(...qs.map((q) => q.left)), r: Math.max(...qs.map((q) => q.right)),
           t: top, b: Math.max(top, Math.min(H, Math.max(...qs.map((q) => q.bottom)))) };
};
const nearest = ({ l, r, t, b }, cx, cy) =>
  Math.hypot(Math.max(l - cx, 0, cx - r), Math.max(t - cy, 0, cy - b));
const farthest = ({ l, r, t, b }, cx, cy) =>
  Math.hypot(Math.max(Math.abs(l - cx), Math.abs(r - cx)), Math.max(Math.abs(t - cy), Math.abs(b - cy)));
// each frame: growing → release once radius >= nearest(box); shrinking → once radius < farthest(box)
```

Filmed on a 15 Pro Max with the Bottom bar, a circle out of the top right:

```
release trigger                       fade    ink against its own ground
middle of the first line              350ms   trails it: ~150ms pale on the new ground growing,
                                              ~400ms dark on the old ground shrinking, whole line
first touch of the first line         150ms   growing clean; shrinking ~200ms wrong on part of the
                                              line, because lower lines on screen turn first
first touch of the text on screen     150ms   within ~2 frames both ways; the ink now leads, by
                                              ≤90ms, part-faded
```
