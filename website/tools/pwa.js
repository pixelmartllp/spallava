// Check the site really is installable as an app, rather than assuming it is
// because a manifest exists. Chrome's bar is: served over HTTPS, a linked
// manifest with name, a 192 and a 512 icon, a display mode that is not
// "browser", and a service worker that actually takes control of the page.
const puppeteer = require('puppeteer-core');
const fs = require('fs');

function findChrome(){
  const guesses = [process.env.CHROME_PATH,
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
  ].filter(Boolean);
  for (const g of guesses) { if (fs.existsSync(g)) return g; }
  console.error('No Chrome found. Set CHROME_PATH.');
  process.exit(1);
}

const SITE = process.env.SITE_URL || 'https://shashipallava.com/';
const UA = 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36';

(async () => {
  const browser = await puppeteer.launch({ executablePath: findChrome(), headless: 'new',
    args: ['--no-sandbox', '--hide-scrollbars'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  await page.setUserAgent(UA);
  await page.goto(SITE, { waitUntil: 'networkidle2', timeout: 60000 });

  // a service worker only controls the page from the *next* load, so reload once
  await new Promise(r => setTimeout(r, 2500));
  await page.reload({ waitUntil: 'networkidle2', timeout: 60000 });
  await new Promise(r => setTimeout(r, 2500));

  const res = await page.evaluate(async () => {
    const link = document.querySelector('link[rel="manifest"]');
    const out = {
      https: location.protocol === 'https:',
      manifestLink: link ? link.href : null,
      swSupported: 'serviceWorker' in navigator,
      swControlled: !!(navigator.serviceWorker && navigator.serviceWorker.controller),
      themeColor: (document.querySelector('meta[name="theme-color"]') || {}).content || null,
      appleIcon: !!document.querySelector('link[rel="apple-touch-icon"]'),
      appleCapable: !!document.querySelector('meta[name="apple-mobile-web-app-capable"]'),
    };
    if (navigator.serviceWorker) {
      const regs = await navigator.serviceWorker.getRegistrations();
      out.swRegistrations = regs.length;
      out.swScope = regs.length ? regs[0].scope : null;
    }
    if (link) {
      try {
        const m = await (await fetch(link.href)).json();
        out.manifest = {
          name: m.name, short_name: m.short_name, display: m.display,
          start_url: m.start_url, theme_color: m.theme_color,
          background_color: m.background_color,
          icons: (m.icons || []).map(i => `${i.sizes} ${i.purpose || 'any'}`),
          iconSrcs: (m.icons || []).map(i => i.src),
        };
      } catch (e) { out.manifestError = String(e); }
    }
    return out;
  });

  const m = res.manifest || {};
  const has = (s, p) => (m.icons || []).some(x => x.startsWith(s) && x.includes(p));
  const checks = [
    ['served over HTTPS',            res.https],
    ['manifest linked in head',      !!res.manifestLink],
    ['manifest has a name',          !!m.name],
    ['display is app-like',          m.display && m.display !== 'browser'],
    ['192px icon',                   has('192', 'any')],
    ['512px icon',                   has('512', 'any')],
    ['maskable icon (nice to have)', (m.icons || []).some(x => x.includes('maskable'))],
    ['service worker registered',    res.swRegistrations > 0],
    ['service worker controls page', res.swControlled],
  ];
  console.log('--- installability ---');
  let hard = 0;
  checks.forEach(([label, ok], i) => {
    const optional = label.includes('nice to have');
    if (!ok && !optional) hard++;
    console.log(`  ${ok ? 'PASS' : (optional ? 'warn' : 'FAIL')}  ${label}`);
  });
  console.log('--- manifest ---');
  console.log('  name        :', m.name);
  console.log('  short_name  :', m.short_name);
  console.log('  display     :', m.display, '| start_url:', m.start_url);
  console.log('  theme_color :', m.theme_color, '| background:', m.background_color);
  console.log('  icons       :', (m.icons || []).join(', '));
  (m.iconSrcs || []).forEach(s => console.log('     ', s));
  console.log('  sw scope    :', res.swScope);
  console.log('  apple icon  :', res.appleIcon, '| apple capable meta:', res.appleCapable);
  console.log(hard === 0 ? '\n  => INSTALLABLE' : `\n  => NOT INSTALLABLE (${hard} hard checks failed)`);

  await browser.close();
  process.exit(hard === 0 ? 0 : 1);
})();
