/* RAG Survey — citation graph page: vis-network rendering of the manuscript's
   citation network, with chapter isolation, search and a selected-paper panel. */
(function () {
  "use strict";

  var CHAPTER_COLORS = {
    "Introduction":    "#8a97a8",
    "Components":      "#3f6fb5",
    "System Design":   "#5a8fc7",
    "Agentic RAG":     "#2f9e8f",
    "Learning":        "#7a5fa8",
    "Evaluation":      "#c98a2c",
    "Open Challenges": "#b5544a",
    "Other":           "#b6c0cd"
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

  var container = document.getElementById("graphContainer");
  if (!container || typeof vis === "undefined") return;

  var countEl = document.getElementById("g-count");
  var selEl = document.getElementById("g-sel");
  var topEl = document.getElementById("g-top");
  var legendEl = document.getElementById("g-legend");
  var searchEl = document.getElementById("g-search");
  var fitBtn = document.getElementById("g-fit");
  var freezeBtn = document.getElementById("g-freeze");

  var DATA = null, POS = null, network = null, nodeById = {};
  var hiddenChapters = {};
  var selected = null;

  Promise.all([
    fetchJSON("data/graph_data.json"),
    fetchJSON("data/graph_positions.json")
  ]).then(function (res) {
    DATA = res[0];
    POS = res[1].positions || {};

    var nodes = DATA.nodes.map(function (n) {
      var p = POS[n.bibkey] || { x: 0, y: 0 };
      var size = Math.min(34, 7 + Math.sqrt(n.n_cites) * 4.2);
      nodeById[n.bibkey] = n;
      return {
        id: n.bibkey,
        label: "",
        title: n.title,
        x: p.x, y: p.y,
        value: n.n_cites,
        shape: "dot",
        size: size,
        color: {
          background: CHAPTER_COLORS[n.primary_chapter] || CHAPTER_COLORS["Other"],
          border: "rgba(22, 36, 61, 0.35)",
          highlight: { background: "#16243d", border: "#16243d" }
        }
      };
    });

    var visible = {};
    DATA.nodes.forEach(function (n) { visible[n.bibkey] = true; });
    var edges = DATA.edges
      .filter(function (e) { return visible[e.a] && visible[e.b]; })
      .map(function (e) {
        return {
          from: e.a, to: e.b, value: e.weight,
          color: { color: "rgba(120, 138, 160, 0.35)", highlight: "#16243d" },
          width: Math.min(3, 0.4 + e.weight * 0.35)
        };
      });

    var nodeDS = new vis.DataSet(nodes);
    var edgeDS = new vis.DataSet(edges);

    network = new vis.Network(container, { nodes: nodeDS, edges: edgeDS }, {
      nodes: { borderWidth: 1, scaling: { min: 6, max: 34 } },
      edges: { smooth: false, selectionWidth: 2 },
      interaction: { hover: true, tooltipDelay: 120, navigationButtons: false, keyboard: false },
      physics: { enabled: false },
      layout: { improvedLayout: false }
    });

    countEl.textContent = DATA.meta.total_nodes + " cited works · " +
      DATA.meta.total_edges + " co-citation links · " + DATA.meta.total_citations + " citation instances";

    renderLegend(DATA.meta.per_chapter, nodes);
    renderTop(DATA.nodes);
    searchEl.disabled = false;

    network.on("selectNode", function (params) {
      if (params.nodes.length) showNode(params.nodes[0]);
    });
    network.on("deselectNode", function () { selected = null; });

    searchEl.addEventListener("input", function () {
      var q = searchEl.value.trim().toLowerCase();
      if (q.length < 2) return;
      var hit = DATA.nodes.filter(function (n) {
        return (n.title + " " + n.bibkey + " " + n.venue).toLowerCase().indexOf(q) >= 0;
      })[0];
      if (hit) {
        network.selectNodes([hit.bibkey]);
        showNode(hit.bibkey);
        network.focus(hit.bibkey, { scale: 1.4, animation: { duration: 420, easingFunction: "easeInOutQuad" } });
      }
    });

    fitBtn.addEventListener("click", function () {
      network.fit({ animation: { duration: 420, easingFunction: "easeInOutQuad" } });
    });

    freezeBtn.addEventListener("click", function () {
      var live = freezeBtn.getAttribute("aria-pressed") === "true";
      network.setOptions({ physics: { enabled: !live } });
      freezeBtn.setAttribute("aria-pressed", String(!live));
      freezeBtn.textContent = live ? "Freeze layout" : "Stop layout";
    });
  }).catch(function (err) {
    countEl.textContent = "Could not load the graph data (" + err.message + ")";
  });

  function showNode(id) {
    var n = nodeById[id];
    if (!n) return;
    selected = id;
    var links = "";
    if (n.url) links += '<a class="sbtn" href="' + esc(n.url) + '" target="_blank" rel="noopener">Open paper</a>';
    links += '<button class="sbtn" type="button" id="g-trace">Trace links</button>';
    selEl.innerHTML =
      '<div class="sel-title">' + esc(n.title) + "</div>" +
      '<div class="sel-meta">' + esc(n.venue || "n/a") + " · " + esc(n.year || "n/a") +
      " · cited " + n.n_cites + "× in the manuscript<br>" +
      "Primary chapter: <b>" + esc(n.primary_chapter) + "</b></div>" +
      '<div class="sel-links">' + links + "</div>";
    var trace = document.getElementById("g-trace");
    if (trace) {
      trace.addEventListener("click", function () {
        network.selectNodes([id]);
        var neighbours = network.getConnectedNodes(id);
        network.selectNodes(neighbours.concat([id]));
      });
    }
  }

  function renderTop(nodes) {
    var top = nodes.slice(0, 10);
    topEl.innerHTML = top.map(function (n) {
      return '<div class="topcited"><span class="k" data-k="' + esc(n.bibkey) + '">' +
        esc(n.title.length > 58 ? n.title.slice(0, 57) + "…" : n.title) + "</span>" +
        '<span class="c">' + n.n_cites + "</span></div>";
    }).join("");
    topEl.querySelectorAll(".k").forEach(function (el) {
      el.addEventListener("click", function () {
        var id = el.dataset.k;
        network.selectNodes([id]);
        showNode(id);
        network.focus(id, { scale: 1.4, animation: { duration: 420, easingFunction: "easeInOutQuad" } });
      });
    });
  }

  function renderLegend(perChapter, nodes) {
    var counts = {};
    nodes.forEach(function (n) { counts[n.primary_chapter] = (counts[n.primary_chapter] || 0) + 1; });
    legendEl.innerHTML = perChapter.map(function (pair) {
      var ch = pair[0], c = pair[1];
      return '<div class="legend-item" data-ch="' + esc(ch) + '">' +
        '<span class="legend-color" style="background:' +
        (CHAPTER_COLORS[ch] || CHAPTER_COLORS["Other"]) + '"></span>' +
        esc(ch) + '<span class="n">' + c + "</span></div>";
    }).join("");
    legendEl.querySelectorAll(".legend-item").forEach(function (el) {
      el.addEventListener("click", function () {
        var ch = el.dataset.ch;
        hiddenChapters[ch] = !hiddenChapters[ch];
        el.classList.toggle("off", !!hiddenChapters[ch]);
        applyFilter();
      });
    });
  }

  function applyFilter() {
    var anyHidden = Object.keys(hiddenChapters).some(function (k) { return hiddenChapters[k]; });
    var ds = network.body.data.nodes;
    ds.update(DATA.nodes.map(function (n) {
      var hide = anyHidden && hiddenChapters[n.primary_chapter];
      return { id: n.bibkey, hidden: !!hide };
    }));
  }
})();
