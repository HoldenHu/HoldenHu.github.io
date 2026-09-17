/* RAG Survey — shared interactions: question explorer, catalog search,
   figure lightbox, BibTeX copy. No dependencies. */
(function () {
  "use strict";

  var QCOLOR = {
    design: "var(--q-design)",
    runtime: "var(--q-runtime)",
    eval: "var(--q-eval)",
    open: "var(--q-open)"
  };

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function fetchJSON(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error(r.status + " " + url);
      return r.json();
    });
  }

  /* ── Figure lightbox ─────────────────────────────────────────────── */
  var lb = document.getElementById("lb");
  if (lb) {
    var lbImg = document.getElementById("lb-img");
    var lbCap = document.getElementById("lb-cap");
    var lbOpen = document.getElementById("lb-open");
    document.querySelectorAll("figure a.zoom").forEach(function (a) {
      a.addEventListener("click", function (e) {
        e.preventDefault();
        lbImg.src = a.getAttribute("href");
        lbCap.textContent = a.dataset.caption || "";
        lbOpen.href = a.getAttribute("href");
        lb.classList.add("on");
        document.body.classList.add("lb-lock");
      });
    });
    function close() {
      lb.classList.remove("on");
      document.body.classList.remove("lb-lock");
      lbImg.src = "";
    }
    document.getElementById("lb-close").addEventListener("click", close);
    lb.addEventListener("click", function (e) { if (e.target === lb) close(); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
  }

  /* ── BibTeX copy ─────────────────────────────────────────────────── */
  var copybtn = document.getElementById("copybtn");
  if (copybtn) {
    copybtn.addEventListener("click", function () {
      var txt = document.querySelector("#bibtex code").innerText;
      var done = function () {
        copybtn.textContent = "Copied";
        setTimeout(function () { copybtn.textContent = "Copy"; }, 1500);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(txt).then(done, done);
      } else {
        var ta = document.createElement("textarea");
        ta.value = txt; document.body.appendChild(ta); ta.select();
        try { document.execCommand("copy"); } catch (err) {}
        document.body.removeChild(ta); done();
      }
    });
  }

  /* ── Question explorer ───────────────────────────────────────────── */
  var grid = document.getElementById("q-grid");
  if (grid) {
    var tabsEl = document.getElementById("q-tabs");
    var searchEl = document.getElementById("q-search");
    var countEl = document.getElementById("q-count");
    var emptyEl = document.getElementById("q-empty");
    var typeBtns = {
      all: document.getElementById("q-type-all"),
      Focal: document.getElementById("q-type-focal"),
      Open: document.getElementById("q-type-open")
    };
    var state = { group: "all", type: "all", q: "" };
    var DATA = null;

    function render() {
      if (!DATA) return;
      var q = state.q.trim().toLowerCase();
      var shown = 0;
      var html = DATA.groups.map(function (g) {
        var qs = g.questions.filter(function (x) {
          if (state.group !== "all" && state.group !== g.key) return false;
          if (state.type !== "all" && x.type !== state.type) return false;
          if (q && (x.text + " " + x.label + " " + x.section).toLowerCase().indexOf(q) < 0) return false;
          return true;
        });
        shown += qs.length;
        if (!qs.length) return "";
        return qs.map(function (x) {
          var c = QCOLOR[g.key] || "var(--ink)";
          return '<div class="qcard" style="--qc:' + c + '">' +
            '<div class="qhead"><span class="qnum">Q-' + x.n + '</span>' +
            '<span class="qtype">' + esc(x.type) + '</span></div>' +
            '<div class="qtext">' + esc(x.text) + '</div>' +
            (x.section ? '<div class="qsec">Ch. ' + g.chapter + " &middot; " + esc(x.section) + "</div>" : "") +
            '<div class="qlabel">' + esc(x.label) + "</div>" +
            "</div>";
        }).join("");
      }).join("");
      grid.innerHTML = html;
      emptyEl.hidden = shown > 0;
      countEl.textContent = shown + " of " + DATA.total + " questions";
    }

    function setType(t) {
      state.type = t;
      Object.keys(typeBtns).forEach(function (k) {
        typeBtns[k].setAttribute("aria-pressed", String(k === t));
      });
      render();
    }
    Object.keys(typeBtns).forEach(function (k) {
      if (typeBtns[k]) typeBtns[k].addEventListener("click", function () { setType(k); });
    });
    if (searchEl) searchEl.addEventListener("input", function () { state.q = searchEl.value; render(); });

    fetchJSON("data/questions.json").then(function (d) {
      DATA = d;
      var counts = { all: d.total };
      d.groups.forEach(function (g) { counts[g.key] = g.count; });
      var items = [{ key: "all", label: "All chapters", color: "var(--ink)" }]
        .concat(d.groups.map(function (g) {
          return { key: g.key, label: g.label, color: QCOLOR[g.key] || "var(--ink)" };
        }));
      tabsEl.innerHTML = items.map(function (it) {
        var n = counts[it.key] != null ? counts[it.key] : "";
        return '<button class="tab' + (it.key === "all" ? " on" : "") + '" type="button" data-k="' + it.key +
          '" style="--tabc:' + it.color + '">' + esc(it.label) +
          ' <span class="n">' + n + "</span></button>";
      }).join("");
      tabsEl.querySelectorAll("button").forEach(function (b) {
        b.addEventListener("click", function () {
          state.group = b.dataset.k;
          tabsEl.querySelectorAll("button").forEach(function (x) { x.classList.toggle("on", x === b); });
          render();
        });
      });
      render();
    }).catch(function () {
      grid.innerHTML = '<p class="qempty">Could not load <code>data/questions.json</code>.</p>';
    });
  }

  /* ── Reading room: inline catalog search ─────────────────────────── */
  var roomInput = document.getElementById("room-q");
  if (roomInput) {
    var listEl = document.getElementById("room-list");
    var countLbl = document.getElementById("room-count");
    var CAT = null, loading = false;

    function load() {
      if (CAT || loading) return;
      loading = true;
      countLbl.textContent = "Loading the catalog…";
      fetchJSON("data/catalog.json").then(function (d) {
        CAT = d;
        roomInput.disabled = false;
        countLbl.textContent = "1,049 papers in the catalog — start typing.";
      }).catch(function () {
        countLbl.textContent = "Could not load the catalog.";
      });
    }

    function search() {
      if (!CAT) return;
      var q = roomInput.value.trim().toLowerCase();
      if (!q) { listEl.innerHTML = ""; countLbl.textContent = "1,049 papers in the catalog — start typing."; return; }
      var terms = q.split(/\s+/);
      var hits = CAT.filter(function (p) {
        var hay = (p.title + " " + p.authors + " " + p.venue + " " + p.cluster_name + " " + p.year).toLowerCase();
        return terms.every(function (t) { return hay.indexOf(t) >= 0; });
      });
      countLbl.textContent = hits.length + " match" + (hits.length === 1 ? "" : "es");
      listEl.innerHTML = hits.slice(0, 8).map(function (p) {
        var title = p.url
          ? '<a class="rt" href="' + esc(p.url) + '" target="_blank" rel="noopener">' + esc(p.title) + "</a>"
          : '<span class="rt">' + esc(p.title) + "</span>";
        return '<div class="rrow">' + title +
          '<span class="rm">' + esc(p.venue || "n/a") + " &middot; " + esc(p.year) +
          " &middot; " + esc(p.cluster_name) + "</span></div>";
      }).join("") + (hits.length > 8
        ? '<div class="rrow"><a class="rt" href="papers.html">See all ' + hits.length + " matches in the full catalog &rarr;</a></div>"
        : "");
    }

    roomInput.addEventListener("focus", load);
    roomInput.addEventListener("input", search);
    document.querySelectorAll('a[href="papers.html"]').forEach(function (a) {
      if (a.classList.contains("sbtn")) a.addEventListener("click", load);
    });
  }
})();
