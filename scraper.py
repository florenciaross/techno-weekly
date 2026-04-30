import requests
from bs4 import BeautifulSoup
import json, re, time

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

JUNO_URLS = [
    ('https://www.juno.co.uk/deep-house/this-week/',           'Deep house'),
    ('https://www.juno.co.uk/tech-house/this-week/',           'Tech house'),
    ('https://www.juno.co.uk/melodic-house-techno/this-week/', 'Melodic house'),
    ('https://www.juno.co.uk/minimal-deep-tech/this-week/',    'Minimal / deep tech'),
    ('https://www.juno.co.uk/indie-dance-nu-disco/this-week/', 'Indie dance'),
]

BLOCKED = ['hard techno', 'acid', 'trance', 'industrial', 'hardcore', 'gabber', 'hardstyle']

tracks = []
seen = set()

for url, genre_label in JUNO_URLS:
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        items = soup.select('.product-list-item, .juno-product')

        for item in items[:10]:
            try:
                artist  = item.select_one('.artist')
                title   = item.select_one('.productTitle') or item.select_one('.title') or item.select_one('h3')
                label   = item.select_one('.label')
                date_el = item.select_one('.release-date') or item.select_one('[class*=date]')

                artist  = artist.get_text(strip=True)  if artist  else None
                title   = title.get_text(strip=True)   if title   else None
                label   = label.get_text(strip=True)   if label   else '—'
                date    = date_el.get_text(strip=True)  if date_el else '2026'

                if not artist or not title:
                    continue

                tags = ' '.join(t.get_text(strip=True).lower() for t in item.select('.tag,.genre,.category'))
                if any(b in tags for b in BLOCKED):
                    continue

                bpm = '—'
                bpm_el = item.select_one('.bpm')
                if bpm_el:
                    m = re.search(r'\d+', bpm_el.get_text())
                    if m:
                        v = int(m.group())
                        if v > 136:
                            continue
                        bpm = f'{v} BPM'

                key = f'{artist}|{title}'
                if key in seen:
                    continue
                seen.add(key)

                tracks.append({
                    'artist': artist,
                    'title':  title,
                    'label':  label,
                    'genre':  genre_label,
                    'bpm':    bpm,
                    'date':   date
                })

                if len(tracks) >= 15:
                    break

            except Exception as e:
                print(f'item error: {e}')

        time.sleep(1)

    except Exception as e:
        print(f'url error {url}: {e}')

    if len(tracks) >= 15:
        break

tracks = tracks[:15]
print(f'Got {len(tracks)} tracks')

if len(tracks) < 5:
    print('Too few tracks, keeping existing list')
    exit(0)

# Read index.html
with open('index.html') as f:
    html = f.read()

# Build new tracks block
def esc(s):
    return str(s).replace('\\', '\\\\').replace('"', '\\"')

lines = ['// AUTO-GENERATED EACH SUNDAY — do not edit manually', 'const tracks = [']
for t in tracks:
    lines.append(
        f'  {{ artist: "{esc(t["artist"])}", title: "{esc(t["title"])}", '
        f'label: "{esc(t["label"])}", genre: "{esc(t["genre"])}", '
        f'bpm: "{esc(t["bpm"])}", date: "{esc(t["date"])}" }},'
    )
lines.append('];')
new_block = '\n'.join(lines)

# Replace block in html
html = re.sub(
    r'// AUTO-GENERATED EACH SUNDAY.*?(?=\n\s*function)',
    new_block + '\n',
    html,
    flags=re.DOTALL
)

with open('index.html', 'w') as f:
    f.write(html)

print(f'index.html updated with {len(tracks)} tracks')
