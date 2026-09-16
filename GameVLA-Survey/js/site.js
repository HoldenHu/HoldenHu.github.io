/* site.js — progressive enhancements for the GameVLA Survey pages.
   Every block is guarded: it only runs when its markup is present.
   Without JavaScript each feature degrades to plain links. */
(function () {
  'use strict';

  /* ── Figure lightbox ─────────────────────────────────────────────────── */
  (function () {
    var links = Array.prototype.slice.call(document.querySelectorAll('a.zoom'));
    if (!links.length) return;

    var lb = document.createElement('div');
    lb.className = 'lb';
    lb.setAttribute('role', 'dialog');
    lb.setAttribute('aria-label', 'Figure viewer');
    lb.innerHTML =
      '<div class="lbbar"><span class="lbtitle"></span><span class="sp"></span>' +
      '<a class="lborig" target="_blank" rel="noopener">Open original &#8599;</a>' +
      '<button type="button" class="lbclose">Close (Esc)</button></div>' +
      '<img alt="">';
    document.body.appendChild(lb);

    var img = lb.querySelector('img');
    var title = lb.querySelector('.lbtitle');
    var orig = lb.querySelector('.lborig');

    function open(a) {
      img.src = a.getAttribute('href');
      var src = a.querySelector('img');
      img.alt = src ? src.alt : '';
      title.textContent = a.getAttribute('data-caption') || '';
      orig.href = a.getAttribute('href');
      lb.classList.add('on');
      document.body.classList.add('lb-lock');
      lb.querySelector('.lbclose').focus();
    }
    function close() {
      lb.classList.remove('on');
      document.body.classList.remove('lb-lock');
      img.removeAttribute('src');
    }

    links.forEach(function (a) {
      a.addEventListener('click', function (e) { e.preventDefault(); open(a); });
    });
    lb.addEventListener('click', function (e) {
      if (e.target === lb || e.target.classList.contains('lbclose')) close();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') close();
    });
  })();

  /* ── Reading room: search the catalog from the landing page ──────────── */
  (function () {
    var input = document.getElementById('room-q');
    if (!input) return;
    var list = document.getElementById('room-list');
    var count = document.getElementById('room-count');
    var P = [];

    function esc(s) {
      var d = document.createElement('div');
      d.textContent = s == null ? '' : String(s);
      return d.innerHTML;
    }

    function row(p) {
      var href = p.a ? 'https://arxiv.org/abs/' + p.a
                     : 'https://scholar.google.com/scholar?q=' + encodeURIComponent(p.t || '');
      var meta = [p.y ? String(p.y).slice(0, 4) : '', p.v || '', p.ph || '']
        .filter(Boolean).join(' · ');
      return '<div class="rrow"><a class="rt" href="' + href + '" target="_blank" rel="noopener">' +
             esc(p.t) + '</a><span class="rm">' + esc(meta) + '</span></div>';
    }

    function render() {
      var q = input.value.trim().toLowerCase();
      var hits;
      if (!q) {
        hits = P.filter(function (p) { return p.k; })
                .sort(function (a, b) { return (+String(b.y).slice(0, 4)) - (+String(a.y).slice(0, 4)); })
                .slice(0, 4);
        count.textContent = 'Showing 4 of the 315 core works the survey builds on — ' +
                            'search ' + P.length.toLocaleString() + ' screened papers above.';
      } else {
        hits = P.filter(function (p) {
          return ((p.t || '') + ' ' + (p.v || '') + ' ' + (p.m || []).join(' ')).toLowerCase().indexOf(q) >= 0;
        });
        count.innerHTML = hits.length.toLocaleString() + ' match' + (hits.length === 1 ? '' : 'es') +
          ' &middot; <a href="papers.html?q=' + encodeURIComponent(input.value.trim()) + '">open the full catalog &rarr;</a>';
      }
      if (!hits.length) {
        list.innerHTML = '<p class="rempty">No matching paper. Try a venue (NeurIPS), a method (world model), or a game (Minecraft).</p>';
        return;
      }
      list.innerHTML = hits.slice(0, 6).map(row).join('');
    }

    fetch('data/papers_web.json').then(function (r) { return r.json(); }).then(function (d) {
      P = (d || []).map(function (p) {
        if (!Array.isArray(p.m)) p.m = p.m ? [p.m] : [];   // legacy rows: bare-string method
        return p;
      });
      input.disabled = false;
      render();
    }).catch(function () {
      count.textContent = '';
      list.innerHTML = '<p class="rempty">The catalog lives in <code>data/papers_web.json</code> — ' +
                       '<a href="papers.html">open the catalog page</a>.</p>';
    });

    input.addEventListener('input', render);
  })();

  /* ── 90-second tour player ───────────────────────────────────────────── */
  (function () {
    var tour = document.getElementById('tour');
    if (!tour) return;
    var scenes = Array.prototype.slice.call(tour.querySelectorAll('.scene'));
    if (!scenes.length) return;
    var durs = scenes.map(function (s) { return parseInt(s.getAttribute('data-ms'), 10) || 12000; });
    var total = durs.reduce(function (a, b) { return a + b; }, 0);
    var btn = document.getElementById('tour-play');
    var prog = document.getElementById('tour-prog');
    var steps = document.getElementById('tour-steps');
    var strip = tour.querySelectorAll('.strip i');

    var i = 0, playing = false, startAt = 0, elapsed = 0, raf = null;

    function fmt(ms) {
      var s = Math.max(0, Math.round(ms / 1000));
      return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
    }
    function show(n) {
      scenes.forEach(function (s, k) { s.classList.toggle('on', k === n); });
      Array.prototype.forEach.call(strip, function (s, k) { s.classList.toggle('on', k <= n); });
      steps.textContent = 'scene ' + (n + 1) + ' / ' + scenes.length + ' · ' + fmt(elapsed) + ' / ' + fmt(total);
    }
    function tick(ts) {
      if (!playing) return;
      if (!startAt) startAt = ts - elapsed;
      elapsed = ts - startAt;
      prog.style.width = Math.min(100, elapsed / total * 100) + '%';
      var end = durs.slice(0, i + 1).reduce(function (a, b) { return a + b; }, 0);
      if (elapsed >= end) {
        if (i + 1 < scenes.length) { i++; show(i); }
        else { stop(true); return; }
      }
      steps.textContent = 'scene ' + (i + 1) + ' / ' + scenes.length + ' · ' + fmt(elapsed) + ' / ' + fmt(total);
      raf = requestAnimationFrame(tick);
    }
    function play() {
      if (elapsed >= total) { elapsed = 0; i = 0; }
      playing = true; startAt = 0;
      btn.textContent = 'Pause';
      show(i);
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(tick);
    }
    function stop(done) {
      playing = false;
      cancelAnimationFrame(raf);
      btn.textContent = done ? 'Replay' : 'Resume';
      if (done) {
        prog.style.width = '100%';
        steps.textContent = 'end of tour · ' + fmt(total);
      }
    }
    btn.addEventListener('click', function () { if (playing) stop(false); else play(); });
    show(0);
  })();
})();
