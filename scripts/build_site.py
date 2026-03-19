#!/usr/bin/env python3
"""Build static GitHub Pages site from domain YAMLs."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

DOMAINS_DIR = Path(__file__).parent.parent / "domains"
OUTPUT_DIR = Path(__file__).parent.parent / "docs"

RELATION_COLORS = {
    "extends": "#22c55e",
    "combines": "#06b6d4",
    "replaces": "#ef4444",
    "inspires": "#eab308",
}

RELATION_DASHES = {
    "extends": False,
    "combines": False,
    "replaces": False,
    "inspires": True,
}

CATEGORY_MAP = {
    "Autonomous Driving (L4+)": [
        "Waymo",
        "Cruise",
        "Aurora & Argo AI",
        "Zoox & Nuro",
        "Pony.ai & WeRide",
        "Wayve",
    ],
    "ADAS / L2+": [
        "Tesla Autopilot / FSD",
        "Mobileye",
        "Comma.ai & Momenta",
        "Horizon Robotics",
    ],
    "AD Software & Infra": [
        "Tier IV / Autoware",
        "NVIDIA DRIVE & Infra",
        "Applied Intuition & Simulation",
    ],
    "Robotics Companies": [
        "Boston Dynamics & Hyundai",
        "Unitree & Agility Robotics",
        "Figure AI & Humanoid Startups",
        "Physical Intelligence & Covariant",
    ],
    "AI Labs": [
        "OpenAI",
        "Anthropic",
        "Google DeepMind",
        "Meta FAIR",
        "xAI & Mistral & DeepSeek",
    ],
    "Sensors & Industrial": [
        "LiDAR Companies",
        "SLAM Companies",
        "Industrial Robots",
        "Surgical Robots",
    ],
}


def load_domain(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def load_all_domains() -> list[dict]:
    return [load_domain(p) for p in sorted(DOMAINS_DIR.glob("*.yaml"))]


def domain_to_graph_data(domains: list[dict]) -> dict:
    nodes = []
    edges = []
    all_methods = {}

    for d in domains:
        for m in d.get("methods", []):
            all_methods[m["name"]] = m

    years = sorted({m["year"] for m in all_methods.values()})
    year_to_level = {y: i for i, y in enumerate(years)}

    for name, m in all_methods.items():
        size = 25
        stars = m.get("stars")
        if stars:
            if stars > 10000:
                size = 55
            elif stars > 5000:
                size = 42
            elif stars > 1000:
                size = 32

        has_parents = bool(m.get("parents"))
        base_color = "#3b82f6" if has_parents else "#f97316"
        tags = m.get("tags", [])
        desc = m.get("description", "")

        title_parts = [f"{name} [{m['year']}]"]
        if desc:
            title_parts.append(desc)
        if tags:
            title_parts.append(f"Tags: {', '.join(tags)}")

        nodes.append({
            "id": name,
            "label": f"{name}\n[{m['year']}]",
            "title": "\n".join(title_parts),
            "size": size,
            "color": {"background": base_color, "border": "#555", "highlight": {"background": base_color, "border": "#fff"}},
            "borderWidth": 2,
            "font": {"size": 24, "color": "white"},
            "level": year_to_level[m["year"]],
            "year": m["year"],
            "description": desc,
            "tags": tags,
        })

    for name, m in all_methods.items():
        for parent in m.get("parents", []):
            pname = parent["name"]
            rel = parent.get("relation", "extends")
            if pname in all_methods:
                edges.append({
                    "from": pname,
                    "to": name,
                    "color": RELATION_COLORS.get(rel, "#555"),
                    "title": rel,
                    "dashes": RELATION_DASHES.get(rel, False),
                    "arrows": "to",
                    "width": 3,
                })

    return {"nodes": nodes, "edges": edges}


def build_site_data(domains: list[dict]) -> dict:
    domain_by_name = {d["name"]: d for d in domains}
    site_data = {"categories": {}, "domains": {}, "method_index": {}}

    for cat_name, domain_names in CATEGORY_MAP.items():
        cat_domains = [domain_by_name[n] for n in domain_names if n in domain_by_name]
        site_data["categories"][cat_name] = {
            "domain_names": [d["name"] for d in cat_domains],
            "graph": domain_to_graph_data(cat_domains),
        }

    for d in domains:
        site_data["domains"][d["name"]] = {
            "description": d.get("description", ""),
            "methods_count": len(d.get("methods", [])),
            "graph": domain_to_graph_data([d]),
        }

    for d in domains:
        for m in d.get("methods", []):
            if m["name"] not in site_data["method_index"]:
                site_data["method_index"][m["name"]] = d["name"]

    return site_data


def build_stats(domains: list[dict]) -> dict:
    all_methods = []
    for d in domains:
        all_methods.extend(d.get("methods", []))

    methods_per_domain = sorted(
        [(d["name"], len(d.get("methods", []))) for d in domains],
        key=lambda x: -x[1],
    )

    year_counts = {}
    for m in all_methods:
        y = m["year"]
        year_counts[y] = year_counts.get(y, 0) + 1

    return {
        "total_methods": len(all_methods),
        "total_domains": len(domains),
        "methods_per_domain": methods_per_domain,
        "methods_per_year": sorted(year_counts.items()),
    }


INDEX_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta property="og:title" content="Company Technology Genealogy">
<meta property="og:description" content="Interactive genealogy of robotics & AI companies and their technology evolution">
<meta property="og:url" content="https://rsasaki0109.github.io/company-technology-genealogy/">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<title>Company Technology Genealogy</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #0e1117; color: #ccc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
  .header { padding: 16px 24px; border-bottom: 1px solid #333; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
  .header h1 { color: #fff; font-size: 20px; white-space: nowrap; }
  .header a { color: #888; text-decoration: none; font-size: 13px; }
  .header a:hover { color: #fff; }
  .controls { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  select { background: #1a1d23; color: #fff; border: 1px solid #444; border-radius: 6px; padding: 8px 12px; font-size: 14px; cursor: pointer; }
  select:hover { border-color: #666; }
  #search { background: #1a1d23; color: #fff; border: 1px solid #444; border-radius: 6px; padding: 8px 12px; font-size: 14px; width: 200px; }
  #search:focus { border-color: #3b82f6; outline: none; }
  .filter-btn { background: #1a1d23; color: #888; border: 1px solid #444; border-radius: 6px; padding: 6px 10px; font-size: 12px; cursor: pointer; }
  .filter-btn.active { color: #fff; border-color: #22c55e; background: #1a2e1a; }
  .filter-btn:hover { border-color: #666; }
  .stats { color: #888; font-size: 13px; white-space: nowrap; }
  #graph { width: 100%; height: calc(100vh - 70px); }
  .legend {
    position: fixed; top: 80px; right: 16px; z-index: 9999;
    background: rgba(14,17,23,0.9); border: 1px solid #333; border-radius: 8px;
    padding: 10px 14px; font-size: 13px; line-height: 1.7; pointer-events: none;
  }
  .legend b { color: #fff; }
  #info-panel {
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 9998;
    background: #161b22; border-top: 1px solid #333; padding: 16px 24px;
    display: none; max-height: 200px; overflow-y: auto;
  }
  #info-panel.visible { display: flex; gap: 24px; align-items: flex-start; }
  #info-panel .close { position: absolute; top: 8px; right: 16px; color: #888; cursor: pointer; font-size: 18px; }
  #info-panel .close:hover { color: #fff; }
  #info-panel h3 { color: #fff; margin-bottom: 4px; }
  #info-panel .desc { color: #aaa; margin-bottom: 8px; }
  #info-panel .tags span { background: #1a1d23; border: 1px solid #444; border-radius: 4px; padding: 2px 6px; font-size: 11px; margin-right: 4px; }
  @media (max-width: 768px) {
    .header { flex-direction: column; align-items: flex-start; padding: 12px 16px; }
    .header h1 { font-size: 16px; }
    .controls { flex-wrap: wrap; gap: 8px; }
    select, #search { font-size: 12px; padding: 6px 8px; width: 100%; }
    .filter-btn { font-size: 11px; padding: 4px 8px; }
    #graph { height: calc(100vh - 120px); }
    .legend { font-size: 11px; padding: 6px 10px; top: auto; bottom: 12px; right: 12px; }
  }
</style>
</head>
<body>

<div class="header">
  <h1>Company Technology Genealogy</h1>
  <div class="controls">
    <select id="category"></select>
    <select id="domain"></select>
    <input type="text" id="search" placeholder="Search..." autocomplete="off" list="search-list">
    <datalist id="search-list"></datalist>
    <span class="stats" id="stats"></span>
  </div>
  <a href="https://github.com/rsasaki0109/company-technology-genealogy" target="_blank">GitHub</a>
</div>

<div id="graph"></div>

<div class="legend">
  <b>Edges</b><br>
  <span style="color:#22c55e">━━▶</span> extends<br>
  <span style="color:#06b6d4">━━▶</span> combines<br>
  <span style="color:#ef4444">━━▶</span> replaces<br>
  <span style="color:#eab308">╌╌▶</span> inspires<br>
  <b style="margin-top:4px;display:inline-block">Nodes</b><br>
  <span style="color:#f97316">●</span> Origin &nbsp;
  <span style="color:#3b82f6">●</span> Evolution
</div>

<div id="info-panel">
  <span class="close" onclick="document.getElementById('info-panel').classList.remove('visible')">&times;</span>
  <div>
    <h3 id="info-name"></h3>
    <div class="desc" id="info-desc"></div>
    <div class="tags" id="info-tags"></div>
  </div>
</div>

<script>
let DATA;
let network;
let currentGraphData = null;

const OPTIONS = {
  layout: {
    hierarchical: {
      enabled: true,
      direction: "LR",
      sortMethod: "directed",
      levelSeparation: 300,
      nodeSpacing: 150
    }
  },
  physics: { enabled: false },
  edges: { smooth: { type: "cubicBezier" } },
  interaction: { hover: true, tooltipDelay: 100 }
};

function renderGraph(graphData, save) {
  if (save !== false) currentGraphData = graphData;
  const container = document.getElementById("graph");
  const data = {
    nodes: new vis.DataSet(graphData.nodes),
    edges: new vis.DataSet(graphData.edges)
  };
  if (network) network.destroy();
  network = new vis.Network(container, data, OPTIONS);
  document.getElementById("stats").textContent =
    graphData.nodes.length + " entries / " + graphData.edges.length + " edges";

  network.on("click", function(params) {
    if (params.nodes.length === 1) {
      const nodeId = params.nodes[0];
      const node = graphData.nodes.find(n => n.id === nodeId);
      if (node) {
        document.getElementById("info-name").textContent = node.id + " [" + node.year + "]";
        document.getElementById("info-desc").textContent = node.description || "";
        const tagsEl = document.getElementById("info-tags");
        tagsEl.innerHTML = (node.tags || []).map(t => "<span>" + t + "</span>").join("");
        document.getElementById("info-panel").classList.add("visible");
      }
    } else {
      document.getElementById("info-panel").classList.remove("visible");
    }
  });
}

function buildSearchIndex() {
  const list = document.getElementById("search-list");
  for (const name of Object.keys(DATA.method_index)) {
    const opt = document.createElement("option");
    opt.value = name;
    list.appendChild(opt);
  }
}

function searchMethod(query) {
  if (!query || !DATA.method_index[query]) return;
  const domainName = DATA.method_index[query];
  for (const [catName, catData] of Object.entries(DATA.categories)) {
    if (catData.domain_names.includes(domainName)) {
      document.getElementById("category").value = catName;
      populateDomains(catName);
      document.getElementById("domain").value = domainName;
      renderGraph(DATA.domains[domainName].graph);
      setTimeout(() => {
        if (network) {
          network.selectNodes([query]);
          network.focus(query, { scale: 1.2, animation: { duration: 500 } });
        }
      }, 300);
      break;
    }
  }
}

function populateDomains(catName) {
  const domainSelect = document.getElementById("domain");
  domainSelect.innerHTML = "";
  const allOpt = document.createElement("option");
  allOpt.value = "__category__";
  allOpt.textContent = "All (" + DATA.categories[catName].domain_names.length + " companies)";
  domainSelect.appendChild(allOpt);
  for (const dName of DATA.categories[catName].domain_names) {
    const opt = document.createElement("option");
    opt.value = dName;
    const info = DATA.domains[dName];
    opt.textContent = dName + " (" + info.methods_count + ")";
    domainSelect.appendChild(opt);
  }
}

function onCategoryChange() {
  const catName = document.getElementById("category").value;
  populateDomains(catName);
  renderGraph(DATA.categories[catName].graph);
}

function onDomainChange() {
  const catName = document.getElementById("category").value;
  const domainName = document.getElementById("domain").value;
  if (domainName === "__category__") {
    renderGraph(DATA.categories[catName].graph);
  } else {
    renderGraph(DATA.domains[domainName].graph);
  }
}

fetch("data.json")
  .then(r => r.json())
  .then(d => {
    DATA = d;
    const catSelect = document.getElementById("category");
    for (const catName of Object.keys(DATA.categories)) {
      const opt = document.createElement("option");
      opt.value = catName;
      opt.textContent = catName;
      catSelect.appendChild(opt);
    }
    catSelect.addEventListener("change", onCategoryChange);
    document.getElementById("domain").addEventListener("change", onDomainChange);
    const searchInput = document.getElementById("search");
    searchInput.addEventListener("change", (e) => { searchMethod(e.target.value); e.target.value = ""; });
    searchInput.addEventListener("keydown", (e) => { if (e.key === "Enter") { searchMethod(e.target.value); e.target.value = ""; } });
    buildSearchIndex();
    onCategoryChange();
  });
</script>
</body>
</html>
"""


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("Loading domains...")
    domains = load_all_domains()
    total = sum(len(d.get("methods", [])) for d in domains)
    print(f"  {len(domains)} companies, {total} entries")

    print("Building site data...")
    site_data = build_site_data(domains)

    data_path = OUTPUT_DIR / "data.json"
    with data_path.open("w") as f:
        json.dump(site_data, f, separators=(",", ":"))
    print(f"  data.json: {data_path.stat().st_size / 1024:.0f} KB")

    print("Building stats...")
    stats = build_stats(domains)
    stats_path = OUTPUT_DIR / "stats.json"
    with stats_path.open("w") as f:
        json.dump(stats, f, indent=2)

    index_path = OUTPUT_DIR / "index.html"
    index_path.write_text(INDEX_HTML)
    print(f"  index.html written")

    print(f"\nDone! Open {OUTPUT_DIR}/index.html")


if __name__ == "__main__":
    main()
