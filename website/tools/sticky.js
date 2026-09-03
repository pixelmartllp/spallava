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
const URL = (process.env.SITE_URL || 'https://shashipallava.com/') + '?cb=' + Date.now();

async function check(browser, label, width, height, isMobile, out) {
  const page = await browser.newPage();
  await page.setViewport({ width, height, deviceScaleFactor: 1, isMobile, hasTouch: isMobile });
  await page.setUserAgent(isMobile
    ? 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
    : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36');
  await page.goto(URL, { waitUntil: 'networkidle2', timeout: 60000 });
  await new Promise(r => setTimeout(r, 900));

  const before = await page.evaluate(() => {
    const b = document.querySelector('.sp .appbar').getBoundingClientRect();
    return Math.round(b.top);
  });
  await page.evaluate(() => window.scrollTo(0, 1600));
  await new Promise(r => setTimeout(r, 700));
  const after = await page.evaluate(() => {
    const e = document.querySelector('.sp .appbar');
    const b = e.getBoundingClientRect();
    return { top: Math.round(b.top), tight: e.classList.contains('tight'),
             scrolled: Math.round(window.pageYOffset) };
  });
  console.log(`${label.padEnd(10)} width=${width}  appbar top before=${before}  after scrolling ${after.scrolled}px: top=${after.top}  tight=${after.tight}  -> ${after.top === 0 ? 'STICKY OK' : '*** NOT STICKY ***'}`);
  if (out) { await page.screenshot({ path: out }); }
  await page.close();
}

(async () => {
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox', '--hide-scrollbars'] });
  await check(browser, 'phone', 390, 844, true, process.argv[2]);
  await check(browser, 'desktop', 1440, 900, false, process.argv[3]);
  await browser.close();
})();
