# Writes the resample/, rule/ and black/ probe sets under docs/probes/. Run from the repo root:
#   python3 tools/make_probes.py
#   resample/   does anything re-tint the bars after load?
#   rule/       which top element does Safari's sampler count? (joe-bell/apple-web-app's rule)
#   black/      fresh copies of the blurred-header page, for dark mode and for tinting off
# Same conventions as the earlier sets: body #ff00ff, white/gray stripes, readout box.
import os

D = 'docs/probes'
BLUE, GREEN, RED = '#0000ff', '#00ff00', '#ff0000'

TPL = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>probe: {folder}/{slug}</title>
<style>
html,body{{margin:0}}
body{{background:#ff00ff;font:15px/1.35 -apple-system,system-ui,sans-serif}}
.s{{height:4000px;background:repeating-linear-gradient(#fff 0 20px,#bbb 20px 40px)}}
#r{{position:fixed;left:8px;top:120px;z-index:5;background:#fff;color:#000;border:2px solid #000;padding:6px 8px;max-width:70%;white-space:pre-wrap}}
#r a{{color:#00e}}
#r b{{font-size:18px}}
{css}
</style></head>
<body>
{html}<div class="s"></div>
<div id="r"><span id="rv"></span>
<a href="../../#{anchor}-{slug}">What this tests</a></div>
<script>
// probe {folder}/{slug}: {what}
const t0 = Date.now();
const CHANGE_AT = {change_at};   // seconds after load; 0 means nothing changes
let phase = CHANGE_AT ? 'BEFORE' : 'static';
{js}
if (CHANGE_AT) addEventListener('load', () => setTimeout(() => {{ change(); phase = 'AFTER'; }}, CHANGE_AT * 1000));
setInterval(() => {{
  const s = Math.round((Date.now() - t0) / 1000);
  rv.innerHTML = '<b>' + phase + (CHANGE_AT && phase === 'BEFORE' ? ' (changes at ' + CHANGE_AT + 's)' : '') + '</b>\\n' +
    '{folder}/{slug}\\n{what_short}\\n' + 'iH ' + innerHeight + '  y ' + Math.round(scrollY) + '  t ' + s + 's';
}}, 250);
</script>
</body></html>
'''

HEADER = '.hdr{{position:sticky;top:{top};height:64px;{w}background:{bg};{extra}z-index:1}}'
FULL = 'margin:0;'
def hdr(bg, top='0', width=None, extra=''):
    w = f'width:{width};margin:0 auto;' if width else FULL
    return HEADER.format(top=top, w=w, bg=bg, extra=extra)

PAGES = {
  # ---- resample: change happens at 5s; shoot before (t < 5) and after (t >= 8)
  'resample': ('resample', [
    ('dim', 'a fixed full-screen dim, rgba(0,0,0,.5), added at 5s', 'fixed dim added at 5s',
     '', '', 5,
     "function change(){const d=document.createElement('div');d.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:3';document.body.appendChild(d);}"),
    ('dialog', 'a native <dialog> opened with showModal() at 5s', '<dialog> at 5s',
     'dialog{border:2px solid #000;padding:12px}dialog::backdrop{background:rgba(0,0,0,.5)}', '<dialog id="dlg">Modal dialog</dialog>\n', 5,
     "function change(){dlg.showModal();}"),
    ('header-recolor', f'a solid sticky header, {BLUE} at load, turned {GREEN} at 5s', 'header blue → green at 5s',
     hdr(BLUE), '<div class="hdr" id="h"></div>\n', 5,
     f"function change(){{h.style.background='{GREEN}';}}"),
    ('header-added', f'no header at load; a solid sticky {BLUE} header inserted at the top at 5s', 'blue header added at 5s',
     hdr(BLUE), '', 5,
     "function change(){const h=document.createElement('div');h.className='hdr';document.body.prepend(h);}"),
    ('body-then-nudge', f'body turned {GREEN} at 5s, then scrolled 1px at 7s', 'body → green at 5s, 1px scroll at 7s',
     '', '', 5,
     f"function change(){{document.body.style.background='{GREEN}';setTimeout(()=>scrollBy(0,1),2000);}}"),
  ]),
  # ---- rule: static pages; shoot within 20s of load
  'rule': ('rule', [
    ('solid', f'control: a solid full-width sticky {BLUE} header at the top', 'solid blue header',
     hdr(BLUE), '<div class="hdr"></div>\n', 0, ''),
    ('alpha50', 'the header at rgba(0,0,255,.5), no blur', 'header alpha .5, no blur',
     hdr('rgba(0,0,255,.5)'), '<div class="hdr"></div>\n', 0, ''),
    ('alpha80', 'the header at rgba(0,0,255,.8), no blur', 'header alpha .8, no blur',
     hdr('rgba(0,0,255,.8)'), '<div class="hdr"></div>\n', 0, ''),
    ('width85', 'the solid header at 85% of the width, centered', 'header 85% wide',
     hdr(BLUE, width='85%'), '<div class="hdr"></div>\n', 0, ''),
    ('width95', 'the solid header at 95% of the width, centered', 'header 95% wide',
     hdr(BLUE, width='95%'), '<div class="hdr"></div>\n', 0, ''),
    ('top8', 'the solid header stuck at top: 8px, leaving 8px of the magenta body above it', 'header at top: 8px',
     hdr(BLUE, top='8px') + '.gap{height:8px}', '<div class="gap"></div><div class="hdr"></div>\n', 0, ''),
    ('center-pill', f'the solid full-width header plus a narrow fixed {RED} pill (120×32px) at the top center', 'header + red pill at top center',
     hdr(BLUE) + f'.pill{{position:fixed;top:0;left:50%;width:120px;height:32px;margin-left:-60px;background:{RED};z-index:2}}',
     '<div class="hdr"></div><div class="pill"></div>\n', 0, ''),
  ]),
  # ---- black: the header-blur page again, no theme-color, fresh paths
  'black': ('black', [
    (slug, 'a translucent red sticky header with backdrop-filter blur, no theme-color (copy of header-blur-nometa)',
     'blurred header, no theme-color',
     hdr('rgba(255,0,0,.5)', extra='-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);'),
     '<div class="hdr"></div>\n', 0, '')
    for slug in ('dark-a', 'dark-b', 'dark-c', 'notint-a', 'notint-b', 'notint-c')
  ]),
}

n = 0
for folder, (anchor, pages) in PAGES.items():
    for slug, what, short, css, body, change_at, js in pages:
        d = f'{D}/{folder}/{slug}'
        os.makedirs(d, exist_ok=True)
        open(f'{d}/index.html', 'w').write(TPL.format(folder=folder, slug=slug, anchor=anchor, what=what,
            what_short=short.replace("'", "\\'"), css=css, html=body, change_at=change_at, js=js or 'function change(){}'))
        n += 1
    open(f'{D}/{folder}/index.html', 'w').write(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0; url=../#{anchor}">
<title>Safari Color Probes</title>
<style>body{{margin:0;padding:16px;font:16px/1.5 system-ui,sans-serif;background:#fff;color:#000}}</style>
</head><body><p><a href="../#{anchor}">Safari color probes</a></p></body></html>
''')
print('pages written:', n)
