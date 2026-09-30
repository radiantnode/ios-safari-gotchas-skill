# Testing pitfalls that produce false results

Harness mistakes that make a fix look like it works, or a bug look like it is gone.
Section numbers refer to SKILL.md.

- **Headless WebKit fires no `scroll` event for `scrollTo()` from `page.evaluate`.**
  Handlers never run; states never update. Drive scrolling with `mouse.wheel()`.
- **A harness that calls `scrollTo()` inside its own rAF** mutates the position mid-frame,
  after the page's callbacks ran. It measures your registration order, not the browser.
  Real input never does this.
- **A per-frame recorder registered before the page's own rAF loop** reads each frame one
  step stale. Start the page's loop first (one wheel nudge), then register the recorder.
- **Eyeballing screenshots.** Sample pixels. The strip, the status bar, and a seam are all
  one `getpixel` each, and "exactly `#0E1113`" is a fact where "dark" is a guess.
- **Headless WebKit does not advance animations on its own.** Its Web Animations and CSS
  transitions only move when something makes it paint, and `requestAnimationFrame` barely
  fires (once in 1.6s, in a mobile context). Polled from inside `page.evaluate`, a
  clip-path circle read the same radius for over a second. Between Playwright screenshots
  it sat at 0 for 2s, then jumped straight to its end, and a color transition started 1.2s
  before the last shot had not moved at all. Headless
  Chromium ran the same page on time. Check the *logic* of an animated effect (what turns
  when, in what order) in Chromium; check anything tied to the screen's edge in the
  simulator. Neither result comes from WebKit headless.
- **Emulating late scroll delivery** is a fair test of §5: wrap `addEventListener` so
  `scroll` handlers fire on a 120ms timeout, then drive with real wheel input. The
  event-driven version drops frames; the rAF version doesn't. Confirm the test can fail
  before trusting that it passes.
