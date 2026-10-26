"""Playwright screenshots of every Dhoa screen at 360/768/1280. Needs Chromium (set executable_path) and Leaflet/jQuery/Bootstrap in /tmp/chrom/node_modules (npm install leaflet@1.9.3 jquery@3.7.1 bootstrap@5.2.2 leaflet.markercluster@1.5.3 leaflet.awesome-markers@2.0.5 @fortawesome/fontawesome-free@6.2.0); CDN requests are answered locally via route interception."""
import re, subprocess, sys, time, os
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path('/home/claude/w2/proj'); NM=Path('/tmp/chrom/node_modules'); OUT=Path(sys.argv[1] if len(sys.argv)>1 else '/home/claude/w2/shots')
OUT.mkdir(exist_ok=True); PORT=8601
def local(url):
    m=re.match(r'https://cdn\.jsdelivr\.net/npm/((?:@[^/]+/)?[^@/]+)@[^/]+/(.*)',url)
    if m: return NM/m.group(1)/m.group(2)
    if 'code.jquery.com' in url: return NM/'jquery/dist/jquery.min.js'
    m=re.match(r'https://cdnjs\.cloudflare\.com/ajax/libs/Leaflet\.awesome-markers/[^/]+/(.*)',url)
    if m: return NM/'leaflet.awesome-markers/dist'/m.group(1)
    m=re.match(r'https://cdnjs\.cloudflare\.com/ajax/libs/leaflet\.markercluster/[^/]+/(.*)',url)
    if m: return NM/'leaflet.markercluster/dist'/m.group(1)
    return None
def route(r):
    u=r.request.url
    if u.startswith('http://localhost') or u.startswith('data:') or u.startswith('blob:'): return r.continue_()
    p=local(u)
    if p and p.exists(): return r.fulfill(path=str(p))
    return r.abort()
srv=subprocess.Popen([sys.executable,'-m','streamlit','run','app/streamlit_app.py','--server.port',str(PORT),'--server.headless','true','--browser.gatherUsageStats','false'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=open('/tmp/st.log','w'))
time.sleep(9)
ARGS=['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--font-render-hinting=none']
errors=[]
try:
  with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/tmp/chromium',args=ARGS,headless=True)
    for w,h in ((1280,900),(768,1000),(360,740)):
        ctx=b.new_context(viewport={'width':w,'height':h}); ctx.route('**/*',route)
        pg=ctx.new_page(); pg.on('pageerror',lambda e:errors.append(str(e)[:200]))
        pg.goto(f'http://localhost:{PORT}/?lang=bn'); pg.wait_for_selector('text=ধোঁয়া',timeout=60000); time.sleep(30)
        pg.screenshot(path=str(OUT/f'inspector_{w}.png'),full_page=True)
        try:
            pg.locator('[data-testid="stButtonGroup"] button').nth(1).click(); time.sleep(30)
            pg.screenshot(path=str(OUT/f'community_{w}.png'),full_page=True)
        except Exception as e: errors.append('community nav: '+str(e)[:120])
        if w==1280:
            try:
                pg.locator('[data-testid="stButtonGroup"] button').nth(0).click(); time.sleep(6)
                sel='[data-testid="stSidebar"] [data-testid="stSelectbox"]'
                pg.locator(sel).nth(0).click(); pg.keyboard.type('Dhaka'); pg.keyboard.press('Enter'); time.sleep(8)
                pg.locator(sel).nth(1).click(); pg.keyboard.type('Adabor'); pg.keyboard.press('Enter'); time.sleep(2)
                pg.get_by_role('button',name='প্রয়োগ').first.click(); time.sleep(15)
                pg.screenshot(path=str(OUT/'inspector_empty_1280.png'),full_page=True)
            except Exception as e: errors.append('empty: '+str(e)[:160])
        ctx.close()
    b.close()
finally:
    srv.terminate()
print('errors:',errors); print(sorted(x.name for x in OUT.glob('*.png')))
