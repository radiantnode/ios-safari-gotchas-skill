# Builds docs/probes/index.html (the results page) and the two forwarding sub-indexes, and adds a
# "What this tests" link to any probe page missing one. Run from the repo root:
#   python3 tools/build_probes_page.py
# The results tables below are hand-kept: update a row when a probe is rerun.
# Probe paths, colors and timing on existing pages are left exactly as they are.
import html, os, re

D = 'docs/probes'
MAG = '<span class="sw" style="background:#ff00ff"></span>'
RED = '<span class="sw" style="background:#ff0000"></span>'
BLK = '<span class="sw" style="background:#000"></span>'
STR = '<span class="sw sw-stripe"></span>'

HB = 'translucent red sticky header with backdrop-filter blur'
EXPANDED = [  # slug, theme-color, on the page, simulator, iPhone 15 Pro Max
    ('control', 'none', 'nothing sticky', f'{MAG} status bar; {STR} stripes to the last row', f'{MAG} status bar; identical to meta'),
    ('meta', '#00ff00', 'nothing sticky', 'identical to control', 'identical to control, apart from the clock'),
    ('header-blur', '#00ff00', HB, f'{MAG} status bar', f'{BLK} status bar'),
    ('header-blur-nometa', 'none', HB, f'{MAG} status bar', f'{MAG} status bar'),
    ('header-blur-white', '#ffffff', HB, 'not run', f'{BLK} status bar'),
    ('header-blur-blue', '#0000ff', HB, 'not run', f'{MAG} status bar'),
    ('header-blur-body', '#ff00ff', HB, 'not run', f'{MAG} status bar'),
    ('header-blur-dark', '#203040', HB, 'not run', f'{BLK} status bar'),
    ('repeat-green', '#00ff00', 'copy of header-blur on a fresh path', 'not run', f'{BLK} status bar'),
    ('repeat-blue', '#0000ff', 'copy of header-blur-blue', 'not run', f'{BLK} status bar (was {MAG})'),
    ('repeat-white', '#ffffff', 'copy of header-blur-white', 'not run', f'{BLK} status bar'),
    ('repeat-none', 'none', 'copy of header-blur-nometa', 'not run', f'{BLK} status bar (was {MAG})'),
    ('flat-red', '#00ff00', 'opaque red sticky 100dvh stage (§1)', f'{RED} flat fill, {RED} status bar, red-tinted toolbar', 'not run'),
    ('flat-clear', '#00ff00', 'transparent sticky 100dvh stage', f'{STR} no flat fill; {MAG} status bar', 'not run'),
    ('flat-clear-nometa', 'none', 'transparent sticky 100dvh stage', 'identical to flat-clear', 'not run'),
]
COLLAPSED = [
    ('control', 'none', 'nothing sticky', f'{STR} stripes under the pill to the last row', f'{STR} stripes to the last row; frosted status bar with a magenta cast'),
    ('meta', '#00ff00', 'nothing sticky', 'identical to control', 'not run'),
    ('header-blur', '#00ff00', HB, f'{STR} stripes to the last row; {MAG} status bar', f'{STR} stripes to the last row; {BLK} status bar'),
    ('header-blur-nometa', 'none', HB, 'identical to header-blur', 'not run'),
    ('flat-red', '#00ff00', 'opaque red sticky 100dvh stage (§1)', f'{RED} flat fill on both devices; red-tinted pill', 'not run'),
    ('flat-clear', '#00ff00', 'transparent sticky 100dvh stage', f'{STR} stripes to the last row', f'{STR} stripes to the last row'),
    ('flat-clear-nometa', 'none', 'transparent sticky 100dvh stage', 'identical to flat-clear', 'not run'),
]
SETS = [('theme-color', 'expanded', EXPANDED), ('theme-color-collapsed', 'collapsed', COLLAPSED)]

P = '<span class="muted">not run</span>'
BLU = '<span class="sw" style="background:#0000ff"></span>'
GRN = '<span class="sw" style="background:#00ff00"></span>'
PUR = '<span class="sw" style="background:#7f00ff"></span>'
DIM = '<span class="sw" style="background:#7f007f"></span>'
AR = ' → '
RESAMPLE = [
    ('dim', 'fixed full-screen dim, rgba(0,0,0,.5), added at 5s',
     f'{MAG}{AR}{DIM} status bar; strip switches to {DIM} flat fill', f'{MAG}{AR}{DIM} status bar; strip and toolbar go flat {DIM}'),
    ('dialog', 'native &lt;dialog&gt; opened with showModal() at 5s', 'same as dim', 'same as dim'),
    ('header-recolor', 'solid sticky header, blue at load, green at 5s', f'{BLU}{AR}{GRN}', f'{BLU}{AR}{GRN} (second load)'),
    ('header-added', 'no header at load; solid blue sticky header inserted at 5s', f'{MAG}{AR}{BLU}', f'{MAG}{AR}{BLU}'),
    ('body-then-nudge', 'body turned green at 5s, then a 1px scroll at 7s', f'{MAG}{AR}{GRN}, before the scroll', f'{MAG}{AR}{GRN}'),
]
RULE = [
    ('solid', 'control: solid full-width blue sticky header', f'{BLU}', f'{BLU}'),
    ('alpha50', 'header at rgba(0,0,255,.5), no blur', f'{PUR} blended over body', f'{PUR} blended over body'),
    ('alpha80', 'header at rgba(0,0,255,.8), no blur', f'{BLU} taken as opaque', f'{BLU} taken as opaque'),
    ('width85', 'solid header, 85% of the width', f'{MAG} not counted', f'{MAG} not counted'),
    ('width95', 'solid header, 95% of the width', f'{BLU}', f'{BLU}'),
    ('top8', 'solid header stuck at top: 8px, with body showing above it', f'{MAG}', f'{MAG}'),
    ('center-pill', 'solid header plus a narrow fixed red pill at the top center', f'{MAG} (not red, not blue)', f'{MAG} (not red, not blue)'),
]
RESAMPLE_NT = [
    ('body-then-nudge', 'copy of resample/body-then-nudge, for "Allow Website Tinting" off', P, f'{MAG}{AR}{GRN}; toolbar untinted'),
    ('header-recolor', 'copy of resample/header-recolor, for "Allow Website Tinting" off', P, f'{BLU}{AR}{GRN}; toolbar untinted'),
]
FOLLOWUP = [
    ('combo', "§10's fix on one page: solid cyan masthead; body turns #111 at 5s, then the page scrolls to its end", P,
     '<span class="sw" style="background:#00aeef"></span> status bar before and after; strip below the page turned dark: pass'),
    ('cache', 'body color set from ?c= before first paint; load ?c=blue, then the same path with ?c=green', P,
     f'{BLU} then {GRN}: no per-URL cache'),
]
BLACK = [(s, 'blurred translucent header, no theme-color', P, r) for s, r in
         (('dark-a', f'{BLK} (Dark Mode)'), ('dark-b', f'{MAG} (Dark Mode)'), ('dark-c', f'{BLK} (Dark Mode)'),
          ('notint-a', f'{MAG} (tinting off)'), ('notint-b', f'{MAG} (tinting off)'), ('notint-c', f'{MAG} (tinting off)'))]

def rows4(folder, anchor, items):
    return '\n'.join(f'''<tr id="{anchor}-{slug}">
  <th scope="row"><a href="{folder}/{slug}/">{slug}</a></th>
  <td>{page}</td><td>{sim}</td><td>{phone}</td>
</tr>''' for slug, page, sim, phone in items)


def table4(folder, anchor, items):
    return f'''<div class="scroll"><table class="t4">
    <thead><tr><th scope="col">Probe</th><th scope="col">On the page</th><th scope="col">Simulator</th><th scope="col">iPhone 15 Pro Max</th></tr></thead>
    <tbody>
{rows4(folder, anchor, items)}
    </tbody>
  </table></div>'''


def rows(folder, anchor, items):
    out = []
    for slug, tc, page, sim, phone in items:
        tcs = '<span class="muted">none</span>' if tc == 'none' else f'<code>{tc}</code>'
        out.append(f'''<tr id="{anchor}-{slug}">
  <th scope="row"><a href="{folder}/{slug}/">{slug}</a></th>
  <td>{tcs}</td><td>{html.escape(page)}</td><td>{sim}</td><td>{phone}</td>
</tr>''')
    return '\n'.join(out)


PAGE = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Safari Color Probes</title>
<meta name="description" content="Single-variable test pages behind the ios-safari-gotchas skill's claims about theme-color, the status bar and the strip under Safari's toolbar on iOS 27.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..900&display=swap" rel="stylesheet">
<style>
  :root {{ --cyan: #00aeef; --yellow: #ffe600; --magenta: #ff00ff; --black: #000; --paper: #fff; --muted: #555; color-scheme: light; }}
  html, body {{ margin: 0; }}
  body {{ background: var(--paper); color: var(--black); font: 400 16px/1.5 Archivo, system-ui, sans-serif; -webkit-text-size-adjust: 100%; }}
  .band {{ height: 16px; background: repeating-linear-gradient(90deg, var(--cyan) 0 40px, var(--yellow) 40px 80px); }}
  main {{ max-width: 72rem; margin: 0 auto; padding: 24px 16px 64px; }}
  h1 {{ margin: 8px 0 12px; font-size: clamp(28px, 7vw, 44px); line-height: 1.04; font-weight: 850; font-variation-settings: "wdth" 125; }}
  h2 {{ margin: 40px 0 8px; font-size: 22px; line-height: 1.2; font-weight: 800; font-variation-settings: "wdth" 112; }}
  p, ul {{ max-width: 64ch; margin: 0 0 12px; }}
  li {{ margin-bottom: 6px; }}
  a {{ color: inherit; text-decoration-thickness: 2px; text-underline-offset: 3px; }}
  a:focus-visible {{ outline: 3px solid var(--magenta); outline-offset: 2px; }}
  code {{ font-size: 0.92em; }}
  .muted {{ color: var(--muted); }}
  .back {{ display: inline-block; margin-bottom: 8px; font-weight: 700; }}
  .findings {{ border-block: 2px solid var(--black); padding: 12px 0; margin: 20px 0; }}
  .findings li {{ max-width: 70ch; }}
  .scroll {{ overflow-x: auto; -webkit-overflow-scrolling: touch; border-block: 2px solid var(--black); }}
  table {{ border-collapse: collapse; min-width: 56rem; width: 100%; font-size: 15px; line-height: 1.4; }}
  th, td {{ text-align: left; vertical-align: top; padding: 8px 10px; border-bottom: 1px solid #bbb; }}
  .t4 {{ min-width: 44rem; }}
  thead th {{ font-weight: 800; font-variation-settings: "wdth" 100; border-bottom: 2px solid var(--black); white-space: nowrap; }}
  tbody th {{ font-weight: 700; white-space: nowrap; }}
  tr:target {{ background: #fff7b3; }}
  .sw {{ display: inline-block; width: 0.8em; height: 0.8em; margin-right: 0.3em; vertical-align: -0.05em; border: 1px solid var(--black); }}
  .sw-stripe {{ background: repeating-linear-gradient(#fff 0 3px, #bbb 3px 6px); }}
</style>
</head>
<body>
<div class="band" aria-hidden="true"></div>
<main>
  <a class="back" href="../">Back to the edge probe</a>
  <h1>Safari color probes</h1>
  <p>Single-variable test pages behind the <a href="https://github.com/radiantnode/ios-safari-gotchas-skill">iOS Safari Gotchas</a>
    skill's claims about <code>theme-color</code>, the status bar and the strip under Safari's toolbar. Every page has a magenta
    <code>body</code> (<code>#ff00ff</code>), white and gray stripes, and a readout box. Where a page sets <code>theme-color</code>,
    it is a color that appears nowhere else on it, so any trace of it would show.</p>

  <div class="findings">
    <p><strong>What they showed on iOS 27</strong> (simulator, and a real iPhone 15 Pro Max with website tinting on unless noted):</p>
    <ul>
      <li><code>theme-color</code>'s color never appeared: not in the status bar, the toolbar or the strip, on any page, device or tab layout.</li>
      <li>The status bar keeps sampling after load. A recolored or inserted header, a new <code>body</code> color, a fixed
        dim or a <code>&lt;dialog&gt;</code> re-tinted it within about 2 seconds, with website tinting on and off.</li>
      <li>Safari samples the element 4px inside the top edge if it spans at least 90% of the width, takes alpha 0.75 and
        up as opaque and blends below that. Otherwise it falls back to <code>body</code>'s color. This is the rule in
        joe-bell/apple-web-app, and every page here agreed with it.</li>
      <li>With a blurred sticky header, the phone sometimes fell back to black instead: 10 of 14 loads with website
        tinting on, whatever the tag said, and 0 of 3 with it off. Identical copies disagreed, so it's a race. The
        simulator gave <code>body</code>'s color every time.</li>
      <li>So a solid, full-width header can hold the status bar while <code>body</code> drives the strip under the toolbar
        (<code>combo</code>), and there is no per-URL color cache (<code>cache</code>).</li>
      <li>Only an opaque sticky element sized to the viewport flattened the strip under the toolbar, and it filled with that element's
        own color. No page showed a flat <code>body</code> strip under the collapsed pill.</li>
    </ul>
    <p>The rules that follow from these are in the skill's SKILL.md, sections 1, 2 and 10.</p>
  </div>

  <h2>How to run them</h2>
  <ul>
    <li><strong>Reloading is fine for the status bar.</strong> Safari keeps no status-bar color per URL on iOS 27 (see
      <code>cache</code> below). Flat fill across loads is untested, so for those pages a fresh copy on a new path is safer.</li>
    <li><strong>Expanded set:</strong> screenshot within 20 seconds of opening. Each page scrolls itself to y=1500 at 30 seconds,
      so a second shot gives you mid-page.</li>
    <li><strong>Collapsed set:</strong> these don't scroll themselves. Swipe up once so the bars collapse (a programmatic scroll
      never does), check that the readout's <code>iH</code> jumps to <code>100lvh</code>, then screenshot.</li>
    <li>Note your Safari tab layout and whether "Allow Website Tinting" is on (Settings › Apps › Safari).</li>
    <li>New results, on any device or iOS version, are welcome as a
      <a href="https://github.com/radiantnode/ios-safari-gotchas-skill/issues/new">GitHub issue</a>.</li>
  </ul>

  <h2 id="expanded">Toolbar expanded</h2>
  <p>Simulator: iPhone 18 Pro, iOS 27.0, Compact tab bar. iPhone: 15 Pro Max, iOS 27, Bottom tab bar.</p>
  <div class="scroll"><table>
    <thead><tr><th scope="col">Probe</th><th scope="col">theme-color</th><th scope="col">On the page</th><th scope="col">Simulator</th><th scope="col">iPhone 15 Pro Max</th></tr></thead>
    <tbody>
{rows('theme-color', 'expanded', EXPANDED)}
    </tbody>
  </table></div>

  <h2 id="collapsed">Toolbar collapsed</h2>
  <p>Simulator: iPhone 18 Pro (Compact, all seven) and 15 Pro Max (Bottom: control, meta, flat-red). iPhone: 15 Pro Max, Bottom tab bar.</p>
  <div class="scroll"><table>
    <thead><tr><th scope="col">Probe</th><th scope="col">theme-color</th><th scope="col">On the page</th><th scope="col">Simulator</th><th scope="col">iPhone 15 Pro Max</th></tr></thead>
    <tbody>
{rows('theme-color-collapsed', 'collapsed', COLLAPSED)}
    </tbody>
  </table></div>
  <p class="muted">On flat-clear the transparent stage takes up the first screen of the page, so <code>body</code> shows above the
    stripes until you scroll past it. That's expected, and the bottom edge is what the page tests.</p>

  <h2 id="resample">Does anything re-tint the bars after load?</h2>
  <p>Each page changes one thing 5 seconds after it loads; the readout says BEFORE or AFTER. Take one screenshot
    before 5 seconds and one after 8. Every change re-tinted the status bar, on the phone and in the simulator.</p>
  {table4('resample', 'resample', RESAMPLE)}

  <p>The same two tests on fresh paths with "Allow Website Tinting" off. The status bar still followed; only the toolbar's tint went away.</p>
  {table4('resample-notint', 'resample-notint', RESAMPLE_NT)}

  <h2 id="rule">Which element does the sampler count?</h2>
  <p>Static pages that test the rule in joe-bell/apple-web-app: Safari samples 4px in from the edge, counts an element
    only if it spans at least 90% of the width, and blends a color below 0.75 alpha. Screenshot within 20 seconds.</p>
  {table4('rule', 'rule', RULE)}

  <h2 id="followup">Follow-ups</h2>
  <p><code>combo</code> passes if the status bar stays cyan while the strip under the toolbar turns dark; it did.
    <code>cache</code> tests SKILL.md §3's old claim that Safari keeps colors per URL; the second load came up green, so it doesn't.</p>
  {table4('followup', 'followup', FOLLOWUP)}

  <h2 id="black">Why did the status bar go black?</h2>
  <p>Fresh copies of the blurred-header page with no <code>theme-color</code>. Open the <code>dark-</code> pages with the
    phone in Dark Mode, and the <code>notint-</code> pages in Light Mode with "Allow Website Tinting" off. Dark Mode
    made no difference; with tinting off, the black never appeared.</p>
  {table4('black', 'black', BLACK)}
</main>
</body>
</html>
'''
open(f'{D}/index.html', 'w').write(PAGE)

# Sub-indexes: forward to the matching section of the landing page.
for folder, anchor, _ in SETS:
    open(f'{D}/{folder}/index.html', 'w').write(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0; url=../#{anchor}">
<title>Safari Color Probes</title>
<style>body{{margin:0;padding:16px;font:16px/1.5 system-ui,sans-serif;background:#fff;color:#000}}</style>
</head><body><p><a href="../#{anchor}">Safari color probes</a></p></body></html>
''')

# Probe pages: a "What this tests" link inside the readout box. Nothing else changes.
n = 0
for folder, anchor, items in SETS:
    for slug, *_ in items:
        p = f'{D}/{folder}/{slug}/index.html'
        t = open(p).read()
        if 'id="rv"' not in t:
            t = t.replace('<div id="r"></div>',
                          f'<div id="r"><span id="rv"></span>\n<a href="../../#{anchor}-{slug}">What this tests</a></div>', 1)
            t, k = re.subn(r'setInterval\(\(\) => \{ r\.textContent = ', 'setInterval(() => { rv.textContent = ', t)
            assert k == 1, p
            t = t.replace('#r{position:fixed;', '#r a{color:#00e}\n#r{position:fixed;', 1)
            open(p, 'w').write(t)
            n += 1
print('probe pages updated:', n)
