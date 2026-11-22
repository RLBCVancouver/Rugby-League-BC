/* Rugby League BC site behaviour. No dependencies. */
(function () {
  'use strict';
  var d = document, root = d.documentElement;
  root.classList.add('js');
  var $ = function (s, c) { return (c || d).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || d).querySelectorAll(s)); };
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---- menu ---- */
  var mb = $('.menu-b'), menu = $('#menu');
  if (mb && menu) {
    var setMenu = function (open) {
      mb.setAttribute('aria-expanded', open ? 'true' : 'false');
      menu.hidden = !open;
    };
    mb.addEventListener('click', function () { setMenu(mb.getAttribute('aria-expanded') !== 'true'); });
    d.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !menu.hidden) { setMenu(false); mb.focus(); } });
    menu.addEventListener('click', function (e) { if (e.target.closest('a')) setMenu(false); });
  }

  /* ---- reveal on scroll ---- */
  var rv = $$('.rv');
  if (reduce || !('IntersectionObserver' in window)) {
    rv.forEach(function (el) { el.classList.add('in'); });
  } else {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
    rv.forEach(function (el) { io.observe(el); });
  }

  /* ---- scrollspy for the jump bar on long pages ---- */
  $$('.jump').forEach(function (jump) {
    if (!('IntersectionObserver' in window)) return;
    var links = $$('a[href^="#"]', jump), secs = [], ul = $('ul', jump);
    links.forEach(function (a) { var s = d.getElementById(a.getAttribute('href').slice(1)); if (s) secs.push(s); });
    var spy = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        links.forEach(function (a) {
          var on = a.getAttribute('href') === '#' + e.target.id;
          a.classList.toggle('on', on);
          if (on) {
            a.setAttribute('aria-current', 'true');
            if (ul && ul.scrollWidth > ul.clientWidth) ul.scrollLeft = Math.max(0, a.parentNode.offsetLeft - ul.offsetLeft - 16);
          } else a.removeAttribute('aria-current');
        });
      });
    }, { rootMargin: '-25% 0px -65% 0px' });
    secs.forEach(function (s) { spy.observe(s); });
  });

  /* ---- events: hide the ones that have passed, keep the next few on the home page ---- */
  $$('.evs').forEach(function (list) {
    var now = new Date(); now.setHours(0, 0, 0, 0);
    var limit = parseInt(list.getAttribute('data-limit') || '0', 10), shown = 0;
    $$('.ev', list).forEach(function (li) {
      var p = (li.getAttribute('data-end') || '').split('-');
      var end = new Date(+p[0], +p[1] - 1, +p[2]);
      if (end < now || (limit && shown >= limit)) li.hidden = true; else shown++;
    });
    var empty = list.nextElementSibling;
    if (!shown && empty && empty.classList.contains('evs-empty')) { empty.hidden = false; list.hidden = true; }
  });

  /* ---- video: load the player only when asked ---- */
  d.addEventListener('click', function (e) {
    var b = e.target.closest('.yt[data-yt]');
    if (!b) return;
    var f = d.createElement('iframe');
    f.className = 'yt-frame';
    f.src = 'https://www.youtube-nocookie.com/embed/' + encodeURIComponent(b.getAttribute('data-yt')) + '?autoplay=1&rel=0';
    f.title = (b.getAttribute('aria-label') || 'Video').replace(/^Play video: /, '');
    f.allow = 'accelerometer; autoplay; encrypted-media; picture-in-picture; fullscreen';
    f.allowFullscreen = true;
    b.parentNode.replaceChild(f, b);
    f.focus();
  });

  /* ---- image viewer for season result sheets ---- */
  var dlg = $('.zoom-d');
  if (dlg && dlg.showModal) {
    d.addEventListener('click', function (e) {
      var a = e.target.closest('a.zoom');
      if (!a) return;
      e.preventDefault();
      var im = $('img', dlg);
      im.src = a.getAttribute('href');
      im.alt = a.getAttribute('data-zoom') || '';
      dlg.showModal();
    });
    dlg.addEventListener('click', function (e) { if (e.target === dlg) dlg.close(); });
  }

  /* ---- fixtures: filter by club ---- */
  var data = {};
  try { data = JSON.parse($('#rlbc-data').textContent); } catch (err) { data = {}; }
  var team = '';
  function applyFilter() {
    $$('.rds[data-live] .mx, .rds-all .mx').forEach(function (li) {
      li.hidden = !!team && (' ' + li.getAttribute('data-teams') + ' ').indexOf(' ' + team + ' ') < 0;
    });
    $$('.rds-all .rd').forEach(function (rd) { rd.hidden = !$$('.mx', rd).some(function (li) { return !li.hidden; }); });
  }
  d.addEventListener('click', function (e) {
    var c = e.target.closest('.chip[data-team]');
    if (!c) return;
    team = c.getAttribute('data-team');
    $$('.chip[data-team]').forEach(function (x) { var on = x === c; x.classList.toggle('on', on); x.setAttribute('aria-pressed', on ? 'true' : 'false'); });
    applyFilter();
  });

  /* ---- fixtures: optional live Google Sheet ----
     If a published-sheet CSV link is set in Site settings, the fixtures page reads the
     sheet when it loads, so score updates show without touching the website.
     Columns: date, round, home, away, home_score, away_score, venue, time, note.
     If the sheet can't be read, the page keeps the results it was built with. */
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  function parseCSV(t) {
    var rows = [], row = [], cur = '', q = false;
    for (var i = 0; i < t.length; i++) {
      var ch = t[i];
      if (q) { if (ch === '"') { if (t[i + 1] === '"') { cur += '"'; i++; } else q = false; } else cur += ch; }
      else if (ch === '"') q = true;
      else if (ch === ',') { row.push(cur); cur = ''; }
      else if (ch === '\n' || ch === '\r') { if (ch === '\r' && t[i + 1] === '\n') i++; row.push(cur); cur = ''; rows.push(row); row = []; }
      else cur += ch;
    }
    if (cur !== '' || row.length) { row.push(cur); rows.push(row); }
    return rows;
  }
  function teamOf(key) {
    var k = String(key || '').trim(), id = (data.lookup || {})[k.toLowerCase()];
    if (id && data.clubs[id]) { var c = data.clubs[id]; return { id: id, name: c.name, short: c.short, logo: c.logo, url: c.url }; }
    return { id: k.toLowerCase().replace(/[^a-z0-9]+/g, '-'), name: k, short: k, logo: '', url: '' };
  }
  var isNum = function (v) { return /^\d+$/.test(String(v == null ? '' : v).trim()); };
  var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], DAY = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  function fmt(iso) { var p = iso.split('-'), dt = new Date(+p[0], +p[1] - 1, +p[2]); return DAY[dt.getDay()] + ' ' + MON[dt.getMonth()] + ' ' + dt.getDate() + ', ' + dt.getFullYear(); }
  function sideHTML(t, cls) {
    var crest = t.logo ? '<span class="tile tile-s"><img src="' + esc(t.logo) + '" alt="" loading="lazy"></span>' : '<span class="tile tile-s tile-blank" aria-hidden="true"></span>';
    var nm = t.url ? '<a href="' + esc(t.url) + '">' + esc(t.name) + '</a>' : esc(t.name);
    return '<div class="mx-team ' + cls + '">' + crest + '<span>' + nm + '</span></div>';
  }
  function renderResults(ms) {
    var out = '', key = null;
    ms.forEach(function (m) {
      var k = m.date + '|' + m.round;
      if (k !== key) {
        if (key !== null) out += '</ol></section>';
        key = k;
        out += '<section class="rd' + (/final/i.test(m.round) ? ' rd-final' : '') + '"><h3 class="rd-h"><span>' + (esc(m.round) || 'Match') + '</span><time datetime="' + esc(m.date) + '">' + fmt(m.date) + '</time></h3><ol class="mxs">';
      }
      var h = teamOf(m.home), a = teamOf(m.away), mid;
      if (isNum(m.home_score) && isNum(m.away_score)) {
        var hs = +m.home_score, as = +m.away_score;
        mid = '<div class="mx-score"><b class="' + (hs > as ? 'w' : '') + '">' + hs + '</b><i aria-hidden="true">–</i><b class="' + (as > hs ? 'w' : '') + '">' + as + '</b></div>';
      } else mid = '<div class="mx-score mx-up">' + esc(m.time || 'vs') + '</div>';
      var meta = [m.venue, m.note].filter(Boolean).map(esc).join(' · ');
      out += '<li class="mx" data-teams="' + esc(h.id) + ' ' + esc(a.id) + '">' + sideHTML(h, 'mx-home') + mid + sideHTML(a, 'mx-away') + (meta ? '<p class="mx-meta">' + meta + '</p>' : '') + '</li>';
    });
    return out ? out + '</ol></section>' : '<p class="empty">No matches listed yet. Check back once the draw is confirmed.</p>';
  }
  function renderLadder(ms) {
    var t = {};
    ms.forEach(function (m) {
      if (!/^round/i.test(m.round) || !isNum(m.home_score) || !isNum(m.away_score)) return;
      var hs = +m.home_score, as = +m.away_score;
      [[teamOf(m.home), hs, as], [teamOf(m.away), as, hs]].forEach(function (x) {
        var r = t[x[0].id] || (t[x[0].id] = { t: x[0], p: 0, w: 0, l: 0, d: 0, pf: 0, pa: 0 });
        r.p++; r.pf += x[1]; r.pa += x[2];
        if (x[1] > x[2]) r.w++; else if (x[1] < x[2]) r.l++; else r.d++;
      });
    });
    var rows = Object.keys(t).map(function (k) { return t[k]; }).sort(function (a, b) {
      return (b.w - a.w) || (b.d - a.d) || ((b.pf - b.pa) - (a.pf - a.pa)) || (b.pf - a.pf) || a.t.name.localeCompare(b.t.name);
    });
    if (!rows.length) return '';
    var body = rows.map(function (r, i) {
      var diff = r.pf - r.pa, tm = r.t;
      return '<tr><td class="pos">' + (i + 1) + '</td><th scope="row">' + (tm.logo ? '<span class="tile tile-xs"><img src="' + esc(tm.logo) + '" alt="" loading="lazy"></span>' : '') +
        '<span>' + (tm.url ? '<a href="' + esc(tm.url) + '">' + esc(tm.name) + '</a>' : esc(tm.name)) + '</span></th><td>' + r.p + '</td><td>' + r.w + '</td><td>' + r.l + '</td><td>' + r.d + '</td><td>' + r.pf + '</td><td>' + r.pa +
        '</td><td class="diff">' + (diff > 0 ? '+' : '') + diff + '</td></tr>';
    }).join('');
    return body;
  }
  var live = $('.rds[data-live]');
  if (live && data.sheet) {
    fetch(data.sheet, { cache: 'no-store' }).then(function (r) { if (!r.ok) throw new Error('sheet ' + r.status); return r.text(); }).then(function (txt) {
      var rows = parseCSV(txt).filter(function (r) { return r.some(function (c) { return c.trim() !== ''; }); });
      if (rows.length < 2) throw new Error('empty sheet');
      var head = rows[0].map(function (h) { return h.trim().toLowerCase().replace(/[^a-z]+/g, '_'); });
      var need = ['date', 'home', 'away'];
      if (need.some(function (n) { return head.indexOf(n) < 0; })) throw new Error('sheet is missing a date, home or away column');
      var ms = rows.slice(1).map(function (r) { var o = {}; head.forEach(function (h, i) { o[h] = (r[i] || '').trim(); }); o.round = o.round || ''; return o; })
        .filter(function (m) { return /^\d{4}-\d{2}-\d{2}$/.test(m.date) && m.home && m.away; })
        .sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : 0; });
      if (!ms.length) throw new Error('no usable rows');
      live.innerHTML = renderResults(ms);
      var lb = $('.ladder tbody', $('#ladder') || d), rowsHTML = renderLadder(ms);
      if (lb && rowsHTML && lb.closest('table').querySelectorAll('thead th').length === 9) lb.innerHTML = rowsHTML;
      applyFilter();
    }).catch(function (err) { if (window.console) console.warn('Fixtures sheet not loaded, showing built-in results:', err.message); });
  }

  /* ---- contact form (Netlify Forms, sent without leaving the page) ---- */
  $$('form[data-netlify]').forEach(function (form) {
    var topic = new URLSearchParams(location.search).get('topic'), sel = $('select[name=topic]', form);
    if (topic && sel) $$('option', sel).forEach(function (o) { if (o.value.toLowerCase() === topic.toLowerCase()) sel.value = o.value; });
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var msg = $('.form-msg', form), btn = $('button[type=submit]', form);
      btn.disabled = true; btn.textContent = 'Sending…';
      fetch('/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(new FormData(form)).toString() })
        .then(function (r) { if (!r.ok) throw new Error(r.status); form.reset(); msg.className = 'form-msg ok'; msg.textContent = 'Message sent. The RLBC board will reply by email.'; })
        .catch(function () { msg.className = 'form-msg err'; msg.textContent = 'The message did not send. Check your connection and try again, or email board@rugbyleaguebc.ca.'; })
        .then(function () { msg.hidden = false; btn.disabled = false; btn.textContent = 'Send message'; msg.focus(); });
    });
  });
  /* ---- photo gallery lightbox (links open the full photo if scripts are off) ---- */
  var gl = $$('a[data-gallery]');
  if (gl.length && window.HTMLDialogElement) {
    var dlg = document.createElement('dialog'), cur = 0;
    dlg.className = 'lb'; dlg.setAttribute('aria-label', 'Photo viewer');
    dlg.innerHTML = '<div class="lb-in"><img alt=""></div><button class="lb-x" type="button" aria-label="Close">\u00d7</button><button class="lb-p" type="button" aria-label="Previous photo">\u2039</button><button class="lb-n" type="button" aria-label="Next photo">\u203a</button>';
    document.body.appendChild(dlg);
    var big = $('img', dlg);
    var show = function (i) { cur = (i + gl.length) % gl.length; big.src = gl[cur].getAttribute('href'); big.alt = $('img', gl[cur]).alt; };
    gl.forEach(function (a, i) { a.addEventListener('click', function (e) { e.preventDefault(); show(i); dlg.showModal(); }); });
    $('.lb-x', dlg).addEventListener('click', function () { dlg.close(); });
    $('.lb-p', dlg).addEventListener('click', function () { show(cur - 1); });
    $('.lb-n', dlg).addEventListener('click', function () { show(cur + 1); });
    dlg.addEventListener('click', function (e) { if (e.target === dlg || e.target.className === 'lb-in') dlg.close(); });
    dlg.addEventListener('keydown', function (e) { if (e.key === 'ArrowLeft') show(cur - 1); else if (e.key === 'ArrowRight') show(cur + 1); });
  }
})();
