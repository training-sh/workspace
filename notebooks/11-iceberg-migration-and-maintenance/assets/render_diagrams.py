"""Create editable SVG diagrams and render each SVG to PNG with Chromium.

Run: python assets/render_diagrams.py
Requires Playwright and its Chromium browser (python -m playwright install chromium).
"""
import json
from html import escape
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1440, 600


def svg(diagram):
    title = escape(diagram['title'])
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
<title>{title}</title><desc>Four stages of the {title.lower()} exercise, read from left to right.</desc>
<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10" fill="#346b83"/></marker></defs>
<rect width="1440" height="600" fill="#f4f7fa"/>
<rect x="0" y="0" width="1440" height="12" fill="#136f63"/>
<g font-family="Arial, sans-serif">
<text x="64" y="76" font-size="19" letter-spacing="2" fill="#136f63">ICEBERG MIGRATION / LESSON {diagram['n']:02d}</text>
<text x="64" y="132" font-size="36" font-weight="bold" fill="#17324d">{title}</text>''']
    for i, label in enumerate(diagram['labels']):
        x = 64 + i * 342
        parts += [f'<rect x="{x}" y="218" width="280" height="190" rx="14" fill="white" stroke="#b7cbd6" stroke-width="2"/>',
                  f'<circle cx="{x+38}" cy="256" r="20" fill="#136f63"/><text x="{x+38}" y="263" text-anchor="middle" font-size="20" fill="white">{i+1}</text>']
        # Wrap text at word boundaries; preserve the diagram as editable text.
        words, lines, line = label.split(), [], ''
        for word in words:
            if len(line + ' ' + word) > 19:
                lines.append(line); line = word
            else:
                line = (line + ' ' + word).strip()
        lines.append(line)
        for j, line in enumerate(lines):
            parts.append(f'<text x="{x+22}" y="{316+j*31}" font-size="23" fill="#17324d">{escape(line)}</text>')
        if i < 3:
            parts.append(f'<path d="M{x+288},313 H{x+326}" fill="none" stroke="#346b83" stroke-width="3" marker-end="url(#arrow)"/>')
    parts += ['<path d="M64,467 H1370" stroke="#c8d6df"/>',
              '<text x="64" y="513" font-size="21" fill="#405e73">Stage data → inspect files and metadata → perform the operation → reconcile the result</text>',
              '<text x="64" y="550" font-size="18" fill="#405e73">Keep file ownership, writer boundaries and recovery requirements explicit at every stage.</text>', '</g></svg>']
    return '\n'.join(parts)


if __name__ == '__main__':
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': WIDTH, 'height': HEIGHT}, device_scale_factor=1)
        for diagram in json.loads((HERE / 'diagrams.json').read_text()):
            target = HERE / f"{diagram['n']:02d}_flow.svg"
            target.write_text(svg(diagram), encoding='utf-8')
            page.goto(target.as_uri())
            page.locator('svg').screenshot(path=str(target.with_suffix('.png')))
            print(target.with_suffix('.png').name)
        browser.close()
