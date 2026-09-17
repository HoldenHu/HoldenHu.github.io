/* RAG Survey — full catalog: search, filter, sort, incremental rendering. */
(function () {
  "use strict";

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  var CAT = null;
  var state = { q: "", cluster: "", year: "", sort: "year" };
  var shown = 0;
  var PAGE = 60;

  var listEl = document.getElementById("plist");
  var countEl = document.getElementById("cat-count");
  var moreBtn = document.getElementById("cat-more");
  var qEl = document.getElementById("cat-q");
  var clusterEl = document.getElementById("cat-cluster");
  var yearEl = document.getElementById("cat-year");
  var sortEl = document.getElementById("cat-sort");

  function match(p) {
    if (state.cluster && p.cluster !== state.cluster) return false;
    if (state.year && p.year !== state.year) return false;
    if (state.q) {
      var hay = (p.title + " " + p.authors + " " + p.venue + " " + p.cluster_name + " " + p.year).toLowerCase();
      var terms = state.q.toLowerCase().split(/\s+/);
      for (var i = 0; i < terms.length; i++) if (hay.indexOf(terms[i]) < 0) return false;
    }
    return true;
  }

  function sortFn(a, b) {
    if (state.sort === "year") return (b.year || "").localeCompare(a.year || "") || a.title.localeCompare(b.title);
    if (state.sort === "year-asc") return (a.year || "").localeCompare(b.year || "") || a.title.localeCompare(b.title);
    if (state.sort === "title") return a.title.localeCompare(b.title);
    if (state.sort === "cluster") return (a.cluster_name + a.title).localeCompare(b.cluster_name + b.title);
    return 0;
  }

  function rowHTML(p) {
    var title = p.url
      ? '<a class="pt" href="' + esc(p.url) + '" target="_blank" rel="noopener">' + esc(p.title) + "</a>"
      : '<span class="pt">' + esc(p.title) + "</span>";
    var meta = '<span class="v">' + esc(p.venue || "n/a") + "</span> &middot; " + esc(p.year) +
      ' &middot; <span class="v">' + esc(p.cluster_name || "unclustered") + "</span>";
    var body = '<div class="pm">' + meta + "</div>";
    if (p.authors) body += '<div class="pa">' + esc(p.authors) + "</div>";
    if (p.abstract) {
      body += "<details><summary>Abstract</summary><div class=\"ab\">" + esc(p.abstract) + "</div></details>";
    }
    return '<div class="prow">' + title + body + "</div>";
  }

  function render(reset) {
    var hits = CAT.filter(match).sort(sortFn);
    if (reset) { shown = 0; listEl.innerHTML = ""; }
    var next = hits.slice(shown, shown + PAGE);
    listEl.insertAdjacentHTML("beforeend", next.map(rowHTML).join(""));
    shown += next.length;
    countEl.textContent = hits.length + " paper" + (hits.length === 1 ? "" : "s") +
      (hits.length ? " · showing " + Math.min(shown, hits.length) : "");
    moreBtn.hidden = shown >= hits.length;
  }

  function wire() {
    qEl.addEventListener("input", function () { state.q = qEl.value.trim(); render(true); });
    clusterEl.addEventListener("change", function () { state.cluster = clusterEl.value; render(true); });
    yearEl.addEventListener("change", function () { state.year = yearEl.value; render(true); });
    sortEl.addEventListener("change", function () { state.sort = sortEl.value; render(true); });
    moreBtn.addEventListener("click", function () { render(false); });
  }

  fetch("data/catalog.json").then(function (r) { return r.json(); }).then(function (d) {
    CAT = d;

    var clusters = {};
    var years = {};
    d.forEach(function (p) {
      clusters[p.cluster] = clusters[p.cluster] || { name: p.cluster_name, n: 0 };
      clusters[p.cluster].n++;
      if (p.year) years[p.year] = (years[p.year] || 0) + 1;
    });
    clusterEl.innerHTML = '<option value="">All clusters (15)</option>' +
      Object.keys(clusters).sort().map(function (k) {
        return '<option value="' + esc(k) + '">' + esc(clusters[k].name) + " (" + clusters[k].n + ")</option>";
      }).join("");
    yearEl.innerHTML = '<option value="">All years</option>' +
      Object.keys(years).sort().reverse().map(function (y) {
        return '<option value="' + esc(y) + '">' + esc(y) + " (" + years[y] + ")</option>";
      }).join("");

    qEl.disabled = false;
    wire();
    render(true);
  }).catch(function () {
    countEl.textContent = "Could not load data/catalog.json.";
  });
})();
