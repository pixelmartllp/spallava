const puppeteer = require('puppeteer-core');
// Chrome is wherever this machine put it - do not hardcode a path.
const fs = require('fs');
function findChrome(){
  const envPath = process.env.CHROME_PATH;
  const guesses = [envPath,
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
  ].filter(Boolean);
  for (const g of guesses) { if (fs.existsSync(g)) return g; }
  console.error('No Chrome found. Set CHROME_PATH to the browser executable.');
  process.exit(1);
}
const CHROME = findChrome();

const URL = process.argv[2] || 'https://shashipallava.com/';
const OUT = process.argv[3] || 'phone.png';
const W = parseInt(process.argv[4] || '390', 10);

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--hide-scrollbars'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: W, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  await page.setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1');
  await page.goto(URL + (URL.includes('?') ? '&' : '?') + 'cb=' + Date.now(), { waitUntil: 'networkidle2', timeout: 60000 });
  await new Promise(r => setTimeout(r, 1200));
  // scroll through so every reveal fires, then come back to the top
  await page.evaluate(async () => {
    const step = window.innerHeight * 0.8;
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      window.scrollTo(0, y);
      await new Promise(r => setTimeout(r, 90));
    }
    window.scrollTo(0, 0);
  });
  await new Promise(r => setTimeout(r, 900));

  const m = await page.evaluate(() => {
    const q = s => { const e = document.querySelector(s); if (!e) return s + '=MISSING';
      const r = e.getBoundingClientRect(); return `${s}: w=${Math.round(r.width)} left=${Math.round(r.left)}`; };
    let worst = null, wm = 0;
    document.querySelectorAll('.sp *').forEach(e => {
      const r = e.getBoundingClientRect();
      const st = getComputedStyle(e);
      if (st.position === 'fixed') return;
      if (r.right > wm) { wm = r.right; worst = e; }
    });
    return {
      viewport: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      widest: worst ? (worst.className || worst.tagName) + ' right=' + Math.round(wm) : 'none',
      rows: [q('.sp .hero .wrap'), q('.sp .hero-ph'), q('.sp .stats'), q('.sp .burger'),
             q('.sp footer .mark'), q('.sp .door')],
    };
  });
  console.log('viewport   :', m.viewport, ' scrollWidth:', m.scrollWidth,
              m.viewport === m.scrollWidth ? '(no overflow)' : '*** OVERFLOW ***');
  console.log('widest     :', m.widest);
  m.rows.forEach(r => console.log('  ' + r));

  await page.screenshot({ path: OUT, fullPage: true });
  console.log('saved', OUT);
  await browser.close();
})();
