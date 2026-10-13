/* Play & Grow - Brain Game, Missions, Wallet, Account.
   Shipped by sp-game.php in every page's footer (not post content), so this
   file may use any characters - but it must never contain a closing script tag.
   The server decides every point; this file only asks and shows. */
(function () {
  'use strict';
  if (window.SPGame) return;
  var API = window.SPG_API || '/wp-json/sp/v1/';
  var WA = '919876732099';
  var LOGO = 'https://shashipallava.com/wp-content/uploads/2026/09/sp-logo-mark.png';
  var state = { me: null, nonce: '', tab: null, round: null, track: 'iq' };

  /* ---------------- dom helpers ---------------- */
  function h(tag, attrs, kids) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === 'text') n.textContent = attrs[k];
      else if (k === 'html') n.innerHTML = attrs[k];
      else if (k.indexOf('on') === 0) n.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] !== null && attrs[k] !== undefined && attrs[k] !== false) n.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (c) { if (c) n.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); });
    return n;
  }
  function wa(text) { return 'https://wa.me/' + WA + '?text=' + encodeURIComponent(text); }
  function when(t) { return new Date(t * 1000).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }); }

  /* ---------------- api ---------------- */
  function getNonce() {
    if (!document.body.classList.contains('logged-in') && !state.loggedIn) return Promise.resolve('');
    return fetch('/wp-admin/admin-ajax.php?action=rest-nonce', { credentials: 'same-origin' })
      .then(function (r) { return r.text(); })
      .then(function (t) { t = t.trim(); state.nonce = (t !== '0' && t.length === 10) ? t : ''; return state.nonce; })
      .catch(function () { return ''; });
  }
  function api(path, body) {
    var opt = { credentials: 'same-origin', headers: {} };
    if (state.nonce) opt.headers['X-WP-Nonce'] = state.nonce;
    if (body) { opt.method = 'POST'; opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(body); }
    return fetch(API + path, opt).then(function (r) {
      return r.json().then(function (j) {
        if (!r.ok) throw new Error((j && j.message) || 'Something went wrong. Please try again.');
        return j;
      });
    });
  }
  function loadMe() {
    return api('me').then(function (me) { state.me = me; state.loggedIn = me.logged_in; paintPoints(); return me; });
  }

  /* ---------------- shell ---------------- */
  var root, main, pts, tabsBox;
  function build() {
    pts = h('div', { class: 'spg-pts', title: '1 point = ₹1' }, ['★ ', h('span', { text: '0' })]);
    tabsBox = h('nav', { class: 'spg-tabs' });
    main = h('div', { class: 'spg-main' });
    root = h('div', { class: 'spg', id: 'spg', role: 'dialog', 'aria-label': 'Play and Grow' }, [
      h('div', { class: 'spg-top' }, [
        h('img', { src: LOGO, alt: '' }),
        h('div', null, [h('p', { class: 'ttl', text: 'Play & Grow' }), h('p', { class: 'sub', text: 'Brain Game · Missions · Wallet' })]),
        pts,
        h('button', { class: 'spg-x', type: 'button', 'aria-label': 'Close', text: '✕', onclick: close })
      ]),
      tabsBox, main
    ]);
    document.body.appendChild(root);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && root.classList.contains('on')) close(); });
  }
  function paintTabs() {
    tabsBox.textContent = '';
    var inn = state.me && state.me.logged_in;
    var list = inn
      ? [['home', '🏠', 'Dashboard'], ['game', '🧠', 'Game'], ['missions', '🎯', 'Missions'], ['wallet', '★', 'Wallet'], ['account', '👤', 'Account']]
      : [['game', '🧠', 'Game'], ['missions', '🎯', 'Missions'], ['wallet', '★', 'Wallet'], ['account', '👤', 'Login']];
    if (state.me && state.me.is_admin) list.push(['admin', '⚙', 'Admin']);
    list.forEach(function (t) {
      tabsBox.appendChild(h('button', { type: 'button', class: state.tab === t[0] ? 'on' : null, onclick: function () { show(t[0]); } },
        [h('span', { class: 'ic', text: t[1] }), h('span', { text: t[2] })]));
    });
  }
  function paintPoints(bump) {
    var p = state.me && state.me.logged_in ? state.me.points : 0;
    pts.style.display = state.me && state.me.logged_in ? '' : 'none';
    pts.lastChild.textContent = p;
    mountPill();
    if (bump) { pts.classList.add('bump'); setTimeout(function () { pts.classList.remove('bump'); }, 250); }
  }
  function pop(text) {
    var n = h('div', { class: 'spg-pop', text: text });
    document.body.appendChild(n);
    setTimeout(function () { n.remove(); }, 1150);
  }
  function wrap(kids) { main.textContent = ''; main.scrollTop = 0; var w = h('div', { class: 'spg-wrap' }, kids); main.appendChild(w); return w; }
  function loading() { wrap([h('p', { class: 'lede', text: 'Loading…' })]); }
  function failed(e) { wrap([h('p', { class: 'err', text: e.message || String(e) }), h('button', { class: 'spg-btn ghost', type: 'button', text: 'Try again', onclick: function () { show(state.tab); } })]); }

  function show(tab) {
    state.tab = tab;
    state.round = null;
    paintTabs();
    if (tab === 'home' || tab === 'game' || tab === 'wallet' || tab === 'account') {
      loading();
      return loadMe().then(function () {
        if (tab === 'home' && !state.me.logged_in) tab = state.tab = 'account';
        paintTabs();
        if (tab === 'home') viewHome(); else if (tab === 'game') viewLevels(); else if (tab === 'wallet') viewWallet(); else viewAccount();
      }).catch(failed);
    }
    if (tab === 'missions') return viewMissions();
    if (tab === 'wallet') return viewWallet();
    if (tab === 'account') return viewAccount();
    if (tab === 'admin') return viewAdmin();
  }
  function isLight() {
    return !!(document.querySelector('.sp.light') || document.documentElement.classList.contains('spl'));
  }
  function open(tab) {
    if (!root) build();
    root.classList.toggle('light', isLight());
    root.classList.add('on');
    document.documentElement.style.overflow = 'hidden';
    loading();
    getNonce().then(loadMe).then(function () {
      show(tab || state.tab || (state.me.logged_in ? 'home' : 'game'));
    }).catch(failed);
  }
  function close() {
    if (!root) return;
    root.classList.remove('on');
    document.documentElement.style.overflow = '';
    if (HASH[location.hash]) history.replaceState(null, '', location.pathname + location.search);
  }
  function needAccount(msg) {
    return h('div', { class: 'spg-note' }, [
      h('p', { html: '<b>' + msg + '</b>' }),
      h('div', { class: 'spg-row' }, [h('button', { class: 'spg-btn', type: 'button', text: 'Create free account', onclick: function () { show('account'); } })])
    ]);
  }

  /* ---------------- Brain Game ---------------- */
  function trackProg(track) { return track === 'mind' ? state.me.progress_mind : state.me.progress; }
  function pointsFor(track, l) { return track === 'mind' ? state.me.conf.mind_points : state.me.conf.per_level[l]; }
  function viewLevels() {
    var me = state.me, conf = me.conf, track = state.track, prog = trackProg(track);
    var grid = h('div', { class: 'spg-levels' + (track === 'mind' ? ' five' : '') });
    for (var l = 1; l <= prog.levels; l++) (function (l) {
      var locked = l > prog.open;
      var c = prog.correct[l] || 0, size = prog.size[l] || 0;
      var pct = size ? Math.round(c * 100 / size) : 0;
      var hint = locked
        ? (me.logged_in ? prog.unlock + ' right in Level ' + (l - 1) + ' to open' : 'Free account to play')
        : (me.logged_in ? c + '/' + size + ' solved · +' + pointsFor(track, l) + ' each' : 'Practice · no points');
      grid.appendChild(h('button', { type: 'button', class: 'spg-lv' + (locked ? ' lock' : ''), onclick: function () {
        if (locked) { if (!me.logged_in) show('account'); return; }
        startRound(l, track);
      } }, [
        h('span', { class: 'n', text: String(l) }), h('span', { class: 'g', text: track === 'mind' ? 'Mindset ' + l : 'Grade ' + l }),
        h('span', { class: 'bar' }, [h('i', { style: 'width:' + pct + '%' })]), h('span', { class: 'p', text: hint })
      ]));
    })(l);
    var sw = h('div', { class: 'spg-switch' }, [
      h('button', { type: 'button', class: track === 'iq' ? 'on' : null, text: '🧠 IQ Levels', onclick: function () { state.track = 'iq'; viewLevels(); } }),
      h('button', { type: 'button', class: track === 'mind' ? 'on' : null, text: '🌱 Mindset Challenge', onclick: function () { state.track = 'mind'; viewLevels(); } })]);
    var top = [h('p', { class: 'eyebrow', text: track === 'mind' ? 'Mindset Challenge' : 'Brain Game' }),
      h('h2', { text: track === 'mind' ? 'Think it through, the healthy way' : 'Train your mind, one level at a time' }),
      h('p', { class: 'lede', text: track === 'mind'
        ? 'Real-life situations - anger, boundaries, self-worth, relationships. Pick the response that helps you grow. ' + prog.levels + ' levels of ' + (prog.size[1] || 12) + '; get ' + prog.unlock + ' right to open the next.'
        : 'Puzzles, patterns, numbers and words - Grade 1 to Grade 10. Every level is ' + (prog.size[1] || 60) + ' questions; get ' + prog.unlock + ' right to open the next.' }),
      sw];
    if (me.logged_in) {
      top.push(h('div', { class: 'spg-note', html: 'Each <b>first</b> right answer earns points. Today you can still win <b>' + me.day_left + ' of ' + conf.daily_cap + '</b> points. <b>1 point = ₹1</b> towards a 1:1 session or a membership.' }));
    } else {
      top.push(needAccount((track === 'mind' ? 'Level 1 is' : 'Levels 1 and 2 are') + ' free to practise. Create a free account to unlock every level and win points - 1 point = ₹1.'));
    }
    top.push(grid);
    wrap(top);
  }

  function startRound(level, track) {
    track = track || 'iq';
    state.track = track;
    loading();
    api('quiz?level=' + level + '&track=' + track).then(function (r) {
      state.round = { level: level, track: track, qs: r.questions, i: 0, right: 0, won: 0, each: r.points_each };
      askQ();
    }).catch(failed);
  }
  function askQ() {
    var R = state.round, q = R.qs[R.i];
    var isPic = q.o[0].indexOf('<svg') === 0;
    var isLong = !isPic && q.o.some(function (o) { return o.length > 22; });
    var opts = h('div', { class: 'spg-opts' + (isPic ? ' pics' : '') + (isLong ? ' long' : '') });
    var fb = h('div', { class: 'spg-fb' });
    var next = h('button', { class: 'spg-btn', type: 'button', text: R.i + 1 === R.qs.length ? 'See result' : 'Next question →', onclick: function () {
      R.i++;
      if (R.i === R.qs.length) endRound(); else askQ();
    } });
    var answered = false;
    q.o.forEach(function (o, k) {
      var b = h('button', { type: 'button' });
      if (isPic) b.innerHTML = o; else b.textContent = o;
      b.addEventListener('click', function () {
        if (answered) return;
        answered = true;
        Array.prototype.forEach.call(opts.children, function (x) { x.disabled = true; });
        api('answer', { id: q.id, choice: k }).then(function (res) {
          opts.children[res.answer].classList.add('ok');
          if (!res.correct) b.classList.add('bad');
          if (res.correct) R.right++;
          var line = res.correct ? 'Sahi jawab! 🎉' : 'Not quite.';
          if (res.awarded) { R.won += res.awarded; state.me.points = res.points; state.me.day_left = res.day_left; paintPoints(true); pop('+' + res.awarded + ' ★'); }
          if (res.progress) state.me.progress = res.progress;
          if (res.progress_mind) state.me.progress_mind = res.progress_mind;
          var extra = '';
          if (state.me.logged_in && res.correct && !res.awarded) extra = res.first === false ? ' (Already solved before - no new points.)' : ' (Daily points limit reached - keep practising!)';
          fb.textContent = '';
          fb.appendChild(h('p', { class: 'r ' + (res.correct ? 'ok' : 'bad'), text: line + extra }));
          fb.appendChild(h('p', { text: res.explain }));
          fb.appendChild(h('div', { class: 'spg-row' }, [next]));
          fb.classList.add('on');
          fb.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }).catch(function (e) { answered = false; Array.prototype.forEach.call(opts.children, function (x) { x.disabled = false; }); pop(e.message); });
      });
      opts.appendChild(b);
    });
    wrap([
      h('div', { class: 'spg-qh' }, [h('span', { text: (R.track === 'mind' ? 'Mindset ' : 'Level ') + R.level + ' · Question ' + (R.i + 1) + ' of ' + R.qs.length }),
        h('span', { text: state.me.logged_in ? (q.fresh ? '+' + R.each + ' ★ if right' : 'practice') : 'practice' })]),
      h('div', { class: 'spg-qbar' }, [h('i', { style: 'width:' + Math.round(R.i * 100 / R.qs.length) + '%' })]),
      h('p', { class: 'spg-q', text: q.q }),
      q.svg ? h('div', { class: 'spg-fig', html: q.svg }) : null,
      opts, fb
    ]);
  }
  function endRound() {
    var R = state.round, n = R.qs.length;
    var stars = R.right >= n * 0.9 ? 3 : R.right >= n * 0.6 ? 2 : R.right >= n * 0.3 ? 1 : 0;
    var prog = trackProg(R.track);
    var nextOpen = prog.open > R.level;
    var last = R.level === prog.levels;
    wrap([h('div', { class: 'spg-end' }, [
      h('p', { class: 'eyebrow', text: 'Level ' + R.level + ' · round complete' }),
      h('p', { class: 'big', text: R.right + '/' + n }),
      h('p', { class: 'spg-stars', text: '★★★'.slice(0, stars) + '☆☆☆'.slice(0, 3 - stars) }),
      h('p', { class: 'lede', text: state.me.logged_in ? (R.won ? 'You won ' + R.won + ' points this round.' : 'No new points this round.') : 'Create a free account to keep score and win points.' }),
      state.me.logged_in && !last ? h('p', { class: 'lede', text: nextOpen ? 'Level ' + (R.level + 1) + ' is open!' : (prog.correct[R.level] || 0) + ' of ' + prog.unlock + ' right answers needed to open Level ' + (R.level + 1) + '.' }) : null,
      h('div', { class: 'spg-row', style: 'justify-content:center' }, [
        h('button', { class: 'spg-btn', type: 'button', text: 'Play again', onclick: function () { startRound(R.level, R.track); } }),
        nextOpen && !last ? h('button', { class: 'spg-btn ghost', type: 'button', text: 'Level ' + (R.level + 1) + ' →', onclick: function () { startRound(R.level + 1, R.track); } }) : null,
        h('button', { class: 'spg-btn ghost', type: 'button', text: 'All levels', onclick: function () { show('game'); } })
      ])
    ])]);
  }

  /* ---------------- Dashboard ---------------- */
  function viewHome() {
    var me = state.me;
    var iq = me.progress, mind = me.progress_mind;
    var solved = function (pr) { var n = 0; for (var k in pr.correct) n += pr.correct[k]; return n; };
    var since = me.joined ? new Date(me.joined * 1000).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' }) : '';
    var missionBox = h('div', { class: 'spg-card' }, [h('p', { class: 'lede', text: 'Loading this month’s missions…' })]);
    var pending = (me.requests || []).filter(function (r) { return r.status === 'pending'; });
    var trackCard = function (title, pr, track, emoji) {
      return h('div', { class: 'spg-card spg-dc' }, [
        h('p', { class: 'eyebrow', text: emoji + ' ' + title }),
        h('p', { class: 'num', text: 'Level ' + pr.open + ' of ' + pr.levels }),
        h('p', { class: 'lede', text: solved(pr) + ' questions solved' }),
        h('div', { class: 'spg-row' }, [h('button', { class: 'spg-btn', type: 'button', text: 'Continue', onclick: function () { startRound(pr.open, track); } })])
      ]);
    };
    wrap([
      h('p', { class: 'eyebrow', text: 'My Dashboard' }),
      h('h2', { text: 'Namaste, ' + me.name.split(' ')[0] + ' 🌸' }),
      h('p', { class: 'lede', text: since ? 'Member since ' + since : '' }),
      h('div', { class: 'spg-bal spg-sec' }, [
        h('p', { class: 'eyebrow', text: 'Wallet balance' }), h('p', { class: 'big', text: '★ ' + me.points }), h('p', { class: 'rs', text: '= ₹' + me.points }),
        h('p', { class: 'lede', style: 'margin-top:8px', text: me.points >= me.conf.min_redeem ? 'You can redeem now.' : (me.conf.min_redeem - me.points) + ' more points to your first redeem (from ' + me.conf.min_redeem + ').' }),
        h('div', { class: 'spg-row', style: 'justify-content:center' }, [
          h('button', { class: 'spg-btn', type: 'button', text: 'Open wallet', onclick: function () { show('wallet'); } }),
          h('a', { class: 'spg-btn ghost', href: '/membership/', text: 'Memberships' })])
      ]),
      h('div', { class: 'spg-dash spg-sec' }, [trackCard('Brain Game', iq, 'iq', '🧠'), trackCard('Mindset Challenge', mind, 'mind', '🌱')]),
      h('div', { class: 'spg-note', html: 'Today you can still win <b>' + me.day_left + ' of ' + me.conf.daily_cap + '</b> points from the games.' }),
      h('div', { class: 'spg-sec' }, [h('h3', { text: '🎯 This month' }), missionBox]),
      pending.length ? h('div', { class: 'spg-sec' }, [h('h3', { text: 'Waiting for Shashi' }), h('div', { class: 'spg-list' }, pending.map(function (r) {
        return h('div', { class: 'spg-li' }, [h('div', null, [h('p', { text: r.item + ' · ' + r.id }), h('p', { class: 'w', text: when(r.at) })]), h('b', { text: String(r.points) })]);
      }))]) : null,
      h('div', { class: 'spg-sec' }, [h('h3', { text: 'Recent activity' }), h('div', { class: 'spg-list' }, (me.ledger || []).slice(0, 5).map(function (l) {
        return h('div', { class: 'spg-li' }, [h('div', null, [h('p', { text: l.n }), h('p', { class: 'w', text: when(l.t) })]),
          h('span', { class: 'v ' + (l.d < 0 ? 'minus' : 'plus'), text: (l.d < 0 ? '' : '+') + l.d })]);
      }))])
    ]);
    api('missions').then(function (m) {
      missionBox.textContent = '';
      var done = m.weeks.filter(function (w) { return w.done; }).length;
      var next = m.weeks.filter(function (w) { return w.open && !w.done; })[0];
      missionBox.appendChild(h('p', null, [h('b', { text: (m.theme || 'Missions') + (m.month ? ' · ' + m.month : '') })]));
      missionBox.appendChild(h('p', { class: 'lede', text: done + ' of ' + m.weeks.length + ' missions done' }));
      missionBox.appendChild(h('div', { class: 'spg-row' }, [h('button', { class: next ? 'spg-btn' : 'spg-btn ghost', type: 'button',
        text: next ? 'Next: ' + next.title + ' · +' + next.points + ' ★' : 'See missions', onclick: function () { show('missions'); } })]));
    }).catch(function () { missionBox.textContent = ''; });
  }

  /* ---------------- app-bar pill: the wallet, on every page ---------------- */
  function mountPill() {
    var inn = state.me && state.me.logged_in;
    var pill = document.querySelector('.spg-pill');
    if (!inn) { if (pill) pill.remove(); return; }
    if (!pill) {
      pill = h('a', { class: 'spg-pill', href: '#dashboard', title: 'My Dashboard · 1 point = ₹1' });
      var bar = document.querySelector('.sp .appbar');
      var nav = document.querySelector('.spb-bar nav');
      if (bar) bar.insertBefore(pill, bar.querySelector('.themer'));
      else if (nav) nav.insertBefore(pill, nav.firstChild);
      else return;
    }
    pill.textContent = '★ ' + state.me.points;
  }

  /* ---------------- Missions ---------------- */
  function viewMissions() {
    loading();
    api('missions').then(function (m) {
      var list = h('div', { class: 'spg-ms' });
      if (!m.weeks.length) list.appendChild(h('p', { class: 'lede', text: 'This month’s missions are coming soon.' }));
      m.weeks.forEach(function (w) {
        var card = h('div', { class: 'spg-card spg-m' + (w.open ? '' : ' lock') }, [
          h('div', { class: 'top' }, [h('span', { class: 'wk', text: 'Week ' + w.week }), h('span', { class: 'pt', text: '+' + w.points + ' ★' })]),
          h('h3', { text: w.title }), h('p', { class: 'd', text: w.desc })
        ]);
        if (w.done) card.appendChild(h('p', { class: 'st done', text: '✓ Completed' }));
        else if (!w.open) card.appendChild(h('p', { class: 'st', text: 'Opens on ' + w.opens + ' ' + (m.month || '').split(' ')[0] }));
        else if (!state.me.logged_in) card.appendChild(h('div', { class: 'spg-row' }, [h('button', { class: 'spg-btn ghost', type: 'button', text: 'Log in to take part', onclick: function () { show('account'); } })]));
        else {
          var ta = h('textarea', { placeholder: 'Kaisa raha? 2-3 line mein likhiye - aapne kya kiya aur kya mehsoos kiya.' });
          var err = h('p', { class: 'err' });
          var btn = h('button', { class: 'spg-btn', type: 'button', text: 'Mark done · +' + w.points + ' ★', onclick: function () {
            btn.disabled = true; err.textContent = '';
            api('mission', { id: w.id, reflection: ta.value }).then(function (r) {
              state.me.points = r.points; paintPoints(true); pop('+' + r.awarded + ' ★'); viewMissions();
            }).catch(function (e) { btn.disabled = false; err.textContent = e.message; });
          } });
          card.appendChild(ta); card.appendChild(err); card.appendChild(h('div', { class: 'spg-row' }, [btn]));
        }
        list.appendChild(card);
      });
      wrap([h('p', { class: 'eyebrow', text: 'Mission of the Month' + (m.month ? ' · ' + m.month : '') }),
        h('h2', { text: m.theme || 'Self-challenges' }),
        h('p', { class: 'lede', text: 'One small mission every week. Do it, write a few honest lines about how it went, and earn points.' }),
        list]);
    }).catch(failed);
  }

  /* ---------------- Wallet ---------------- */
  function viewWallet() {
    var me = state.me;
    if (!me.logged_in) return wrap([h('p', { class: 'eyebrow', text: 'Wallet' }), h('h2', { text: 'Your points, your growth' }),
      needAccount('Create a free account to collect points. 1 point = ₹1 towards a 1:1 session or a Silver, Gold or Platinum membership.')]);
    var item = h('select', null, me.conf.items.map(function (i) { return h('option', { value: i, text: i }); }));
    var amt = h('input', { type: 'number', min: me.conf.min_redeem, max: me.points, step: '1', value: Math.max(me.conf.min_redeem, Math.min(me.points, me.points)) });
    var err = h('p', { class: 'err' });
    var out = h('div');
    var btn = h('button', { class: 'spg-btn', type: 'button', text: 'Redeem points', onclick: function () {
      err.textContent = ''; btn.disabled = true;
      api('redeem', { item: item.value, points: parseInt(amt.value, 10) || 0 }).then(function (r) {
        state.me.points = r.points; paintPoints(true);
        out.textContent = '';
        out.appendChild(h('div', { class: 'spg-note' }, [
          h('p', { html: 'Request <b>' + r.code + '</b> is with Shashi. Your points are on hold until she confirms.' }),
          h('div', { class: 'spg-row' }, [h('a', { class: 'spg-btn', target: '_blank', rel: 'noopener',
            href: wa('Hi Shashi, I want to use ' + amt.value + ' points for ' + item.value + '. My request code is ' + r.code + '.'), text: 'Send code on WhatsApp' })])
        ]));
        loadMe().then(function () { btn.disabled = false; });
      }).catch(function (e) { btn.disabled = false; err.textContent = e.message; });
    } });
    var hist = h('div', { class: 'spg-list' });
    (me.ledger || []).forEach(function (l) {
      hist.appendChild(h('div', { class: 'spg-li' }, [h('div', null, [h('p', { text: l.n }), h('p', { class: 'w', text: when(l.t) })]),
        h('span', { class: 'v ' + (l.d < 0 ? 'minus' : 'plus'), text: (l.d < 0 ? '' : '+') + l.d })]));
    });
    if (!(me.ledger || []).length) hist.appendChild(h('p', { class: 'lede', style: 'padding:10px 0', text: 'No points yet - play a level or finish a mission.' }));
    var reqs = h('div', { class: 'spg-list' });
    (me.requests || []).forEach(function (r) {
      reqs.appendChild(h('div', { class: 'spg-li' }, [h('div', null, [h('p', { text: r.item + ' · ' + r.id }), h('p', { class: 'w', text: when(r.at) })]),
        h('span', null, [h('span', { class: 'spg-chip ' + r.status, text: r.status }), ' ', h('b', { text: String(r.points) })])]));
    });
    wrap([
      h('div', { class: 'spg-bal' }, [h('p', { class: 'eyebrow', text: 'Wallet balance' }), h('p', { class: 'big', text: '★ ' + me.points }), h('p', { class: 'rs', text: '= ₹' + me.points })]),
      h('div', { class: 'spg-sec spg-card' }, [h('h3', { text: 'Use your points' }),
        h('p', { class: 'lede', text: '1 point = ₹1. Use them for a 1:1 session with Shashi or a Silver, Gold or Platinum membership. From ' + me.conf.min_redeem + ' points.' }),
        h('label', { text: 'Use for' }), item, h('label', { text: 'Points' }), amt, err, h('div', { class: 'spg-row' }, [btn]), out]),
      (me.requests || []).length ? h('div', { class: 'spg-sec' }, [h('h3', { text: 'Your requests' }), reqs]) : null,
      h('div', { class: 'spg-sec' }, [h('h3', { text: 'History' }), hist])
    ]);
  }

  /* ---------------- Account ---------------- */
  function viewAccount(mode) {
    var me = state.me;
    if (me.logged_in) {
      return wrap([h('p', { class: 'eyebrow', text: 'Account' }), h('h2', { text: 'Namaste, ' + me.name }), h('p', { class: 'lede', text: me.email }),
        h('div', { class: 'spg-row' }, [
          h('button', { class: 'spg-btn', type: 'button', text: 'Play Brain Game', onclick: function () { show('game'); } }),
          h('button', { class: 'spg-btn ghost', type: 'button', text: 'Log out', onclick: function () {
            api('logout', {}).then(function () { state.nonce = ''; state.loggedIn = false; document.body.classList.remove('logged-in'); return loadMe(); }).then(function () { show('account'); }).catch(failed);
          } })])]);
    }
    mode = mode || 'signup';
    var sw = h('div', { class: 'spg-switch' }, [
      h('button', { type: 'button', class: mode === 'signup' ? 'on' : null, text: 'Create account', onclick: function () { viewAccount('signup'); } }),
      h('button', { type: 'button', class: mode === 'login' ? 'on' : null, text: 'Log in', onclick: function () { viewAccount('login'); } })]);
    var f = {}, err = h('p', { class: 'err' });
    var fields = mode === 'signup'
      ? [['name', 'Your name', 'text', 'name'], ['email', 'Email', 'email', 'email'], ['phone', 'WhatsApp number', 'tel', 'tel'], ['password', 'Password (8+ characters)', 'password', 'new-password']]
      : [['email', 'Email', 'email', 'username'], ['password', 'Password', 'password', 'current-password']];
    var kids = [];
    fields.forEach(function (x) {
      f[x[0]] = h('input', { type: x[2], autocomplete: x[3], inputmode: x[0] === 'phone' ? 'numeric' : null });
      kids.push(h('label', { text: x[1] }), f[x[0]]);
    });
    var hp = h('input', { class: 'hp', tabindex: '-1', autocomplete: 'off', 'aria-hidden': 'true' });
    var btn = h('button', { class: 'spg-btn', type: 'submit', text: mode === 'signup' ? 'Create account · +' + me.conf.signup_bonus + ' ★ welcome' : 'Log in' });
    var form = h('form', { onsubmit: function (e) {
      e.preventDefault(); err.textContent = ''; btn.disabled = true;
      var body = { website: hp.value };
      Object.keys(f).forEach(function (k) { body[k] = f[k].value.trim(); });
      if (mode === 'login') body.password = f.password.value;
      if (mode === 'signup') body.password = f.password.value;
      api(mode === 'signup' ? 'register' : 'login', body).then(function () {
        state.loggedIn = true; document.body.classList.add('logged-in');
        return getNonce();
      }).then(loadMe).then(function () { paintTabs(); show(mode === 'signup' ? 'game' : 'wallet'); if (mode === 'signup') pop('Welcome! +' + state.me.conf.signup_bonus + ' ★'); })
        .catch(function (e2) { btn.disabled = false; err.textContent = e2.message; });
    } }, kids.concat([hp, err, h('div', { class: 'spg-row' }, [btn])]));
    wrap([h('p', { class: 'eyebrow', text: 'Account' }), h('h2', { text: mode === 'signup' ? 'Join free - play, grow, earn' : 'Welcome back' }),
      h('p', { class: 'lede', text: 'Your points and progress are saved to your account, so they are safe on any phone.' }),
      sw, form,
      mode === 'login' ? h('p', { class: 'lede', style: 'margin-top:12px' }, [h('a', { href: '/wp-login.php?action=lostpassword', text: 'Forgot password?', style: 'color:inherit' })]) : null,
      h('p', { class: 'lede', style: 'margin-top:14px;font-size:.78rem', text: 'We use your number only to reach you about your points and the community.' })]);
  }

  /* ---------------- Admin ---------------- */
  function viewAdmin() {
    loading();
    api('admin/overview').then(function (o) {
      var reqs = h('div', { class: 'spg-list' });
      o.requests.forEach(function (r) {
        var acts = r.status === 'pending' ? h('span', null, [
          h('button', { class: 'spg-btn', type: 'button', style: 'min-height:36px;padding:0 12px', text: 'Done', onclick: function () { act(r.id, 'done'); } }), ' ',
          h('button', { class: 'spg-btn ghost', type: 'button', style: 'min-height:36px;padding:0 12px', text: 'Reject', onclick: function () { if (confirm('Reject and refund ' + r.points + ' points?')) act(r.id, 'reject'); } })
        ]) : h('span', { class: 'spg-chip ' + r.status, text: r.status });
        reqs.appendChild(h('div', { class: 'spg-li' }, [h('div', null, [
          h('p', null, [h('b', { text: r.name }), ' · ' + r.item + ' · ', h('b', { text: r.points + ' pts' })]),
          h('p', { class: 'w', text: r.id + ' · ' + r.phone + ' · ' + r.email + ' · ' + when(r.at) })]), acts]));
      });
      if (!o.requests.length) reqs.appendChild(h('p', { class: 'lede', style: 'padding:10px 0', text: 'No redeem requests yet.' }));
      var refl = h('div', { class: 'spg-list' });
      o.reflections.forEach(function (r) {
        refl.appendChild(h('div', { class: 'spg-li' }, [h('div', null, [h('p', null, [h('b', { text: r.name }), ' · ' + r.mission]), h('p', { text: r.note }), h('p', { class: 'w', text: when(r.at) })])]));
      });
      if (!o.reflections.length) refl.appendChild(h('p', { class: 'lede', style: 'padding:10px 0', text: 'No mission reflections yet.' }));
      wrap([h('p', { class: 'eyebrow', text: 'Admin' }), h('h2', { text: o.members + ' members · ' + o.bank + ' questions' }),
        h('p', { class: 'lede', html: 'Missions are edited in wp-admin → Pages → <b>Missions</b>.' }),
        h('div', { class: 'spg-sec' }, [h('h3', { text: 'Redeem requests' }), reqs]),
        h('div', { class: 'spg-sec' }, [h('h3', { text: 'Mission reflections' }), refl])]);
    }).catch(failed);
    function act(id, action) { api('admin/request', { id: id, action: action }).then(viewAdmin).catch(function (e) { alert(e.message); }); }
  }

  /* ---------------- entry points ---------------- */
  var HASH = { '#play': 'game', '#missions': 'missions', '#wallet': 'wallet', '#dashboard': 'home' };
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href]');
    if (!a) return;
    var href = a.getAttribute('href'), hash = href.slice(href.indexOf('#'));
    if (href.indexOf('#') === -1 || !HASH[hash]) return;
    var path = href.slice(0, href.indexOf('#'));
    if (path && path !== '/' && path !== location.pathname) return;
    e.preventDefault();
    var menuOpen = document.querySelector('.sp.menu-open .burger');
    if (menuOpen) menuOpen.click();
    open(HASH[hash]);
  });
  function fromHash() { if (HASH[location.hash]) open(HASH[location.hash]); }
  window.addEventListener('hashchange', fromHash);
  window.SPGame = { open: open, close: close };
  function boot() {
    fromHash();
    if (document.body.classList.contains('logged-in')) {
      if (!root) build();
      getNonce().then(loadMe).catch(function () {});
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
