<?php
/**
 * SP Lang - an English / Hindi switch on every page, like the theme switch.
 *
 * Runs as the Code Snippets snippet "SP Lang" (published by
 * website/tools/push_seo.py; edit here, not in wp-admin).
 *
 * The site is written in English. Choosing Hindi asks Google's website
 * translator to translate the page in place - the homepage, blog, pages, the
 * assistant and the Play & Grow app, including what they add later. It is
 * machine translation: names and anything marked class="notranslate" are left
 * alone. Nothing is loaded for a visitor who stays in English.
 *
 * The choice lives in Google's own "googtrans" cookie, so it follows the
 * visitor from page to page. Back to English clears it and reloads.
 */

if ( ! defined( 'ABSPATH' ) ) {
	return;
}

add_action( 'wp_footer', function () {
	if ( is_admin() ) {
		return;
	}
	?>
<style id="sp-lang-css">
.sp-lang{flex:none;display:grid;place-items:center;width:44px;height:44px;margin-right:8px;padding:0;border-radius:12px;cursor:pointer;
  border:1px solid var(--fg,#FAFAFA);background:transparent;color:var(--fg,#FAFAFA);font:800 .82rem/1 "Archivo",-apple-system,"Segoe UI",Arial,sans-serif}
.sp .appbar .sp-lang{margin-left:auto}
.sp .appbar .sp-lang + .themer{margin-left:0}
.sp .appbar .spg-pill + .sp-lang{margin-left:8px}
.sp .menu .sp-lang{width:100%;height:48px;margin:0 0 10px;font-size:.72rem;letter-spacing:.09em;text-transform:uppercase}
.spb-bar .sp-lang{width:40px;height:40px;margin:0}
@media (min-width:900px){.sp .appbar .sp-lang{margin-left:0}}
/* Google's own bar, tooltip and highlight stay out of sight */
.goog-te-banner-frame,iframe.skiptranslate,.skiptranslate>iframe,#goog-gt-tt,.goog-te-balloon-frame,.goog-tooltip,
.VIpgJd-ZVi9od-ORHb-OEVmcd,.VIpgJd-ZVi9od-aZ2wEe-wOHMyf,.VIpgJd-yAWNEb-L7lbkb,#sp-gt{display:none!important}
html.translated-ltr body,body{top:0!important}
.goog-text-highlight{background:none!important;box-shadow:none!important}
</style>
<div id="sp-gt" class="notranslate" aria-hidden="true"></div>
<script id="sp-lang-js">
(function () {
	if (window.SPLang) { return; }
	var host = location.hostname;
	function cur() { return /googtrans=\/en\/hi/.test(document.cookie) ? 'hi' : 'en'; }
	function setCookie(v, days) {
		var exp = days ? '; expires=' + new Date(Date.now() + days * 864e5).toUTCString() : '; expires=Thu, 01 Jan 1970 00:00:00 GMT';
		['', '; domain=' + host, '; domain=.' + host.replace(/^www\./, '')].forEach(function (d) {
			document.cookie = 'googtrans=' + v + exp + '; path=/' + d;
		});
	}
	var loaded = false;
	function load() {
		if (loaded) { return; }
		loaded = true;
		window.spGtInit = function () {
			new google.translate.TranslateElement({ pageLanguage: 'en', includedLanguages: 'hi', autoDisplay: false }, 'sp-gt');
		};
		var s = document.createElement('script');
		s.src = 'https://translate.google.com/translate_a/element.js?cb=spGtInit';
		s.async = true;
		document.body.appendChild(s);
	}
	function label() { return cur() === 'hi' ? 'EN' : 'हिं'; }
	function toggle() {
		if (cur() === 'hi') { setCookie('', 0); location.reload(); return; }
		setCookie('/en/hi', 365);
		load();
		paint();
	}
	function paint() {
		document.querySelectorAll('.sp-lang, .spg-lang').forEach(function (b) {
			var wide = b.classList.contains('wide');
			b.textContent = wide ? (cur() === 'hi' ? 'Read in English' : 'हिंदी में पढ़ें') : label();
			b.setAttribute('aria-label', cur() === 'hi' ? 'Switch to English' : 'हिंदी में पढ़ें - switch to Hindi');
			b.setAttribute('translate', 'no');
			b.classList.add('notranslate');
		});
	}
	function button(wide) {
		var b = document.createElement('button');
		b.type = 'button';
		b.className = 'sp-lang notranslate' + (wide ? ' wide' : '');
		b.addEventListener('click', toggle);
		return b;
	}
	function mount() {
		var bar = document.querySelector('.sp .appbar .themer');
		if (bar) { bar.parentNode.insertBefore(button(false), bar); }
		var menu = document.querySelector('.sp .menu .themer');
		if (menu) { menu.parentNode.insertBefore(button(true), menu); }
		var blog = document.querySelector('.spb-bar .spb-tg');
		if (blog) { blog.parentNode.insertBefore(button(false), blog); }
		/* names and the program stay as they are */
		document.querySelectorAll('.sp .name, .spa-head .t, .spg-top .ttl').forEach(function (n) { n.classList.add('notranslate'); });
		paint();
		if (cur() === 'hi') { load(); }
	}
	window.SPLang = { toggle: toggle, label: label, lang: cur };
	if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', mount); } else { mount(); }
})();
</script>
	<?php
}, 40 );
