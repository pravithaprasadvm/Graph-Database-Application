/**
 * Vanguard Supply Chain Graph Intelligence Engine - Frontend Logic
 * Integrated with Cytoscape.js & CognoDB / FastAPI Backend
 */

document.addEventListener("DOMContentLoaded", () => {
  // Global State
  let cy = null;
  let currentGraphData = { nodes: [], relationships: [] };

  // DOM Element Handles
  const statusPill = document.getElementById("db-status-pill");
  const statusText = document.getElementById("db-status-text");
  const statNodes = document.getElementById("stat-nodes");
  const statEdges = document.getElementById("stat-edges");
  const statSpof = document.getElementById("stat-spof");

  const graphLoader = document.getElementById("graph-loader");
  const inspectorBody = document.getElementById("inspector-body");
  const inspectorTitle = document.getElementById("inspector-title");
  const cypherResultsContainer = document.getElementById("cypher-results-container");

  // Tab Navigation Elements
  const navItems = document.querySelectorAll(".nav-item");
  const tabPanels = document.querySelectorAll(".tab-panel");

  // Colors mapping per Node label
  const LABEL_COLORS = {
    "Product": "#8b5cf6",         // Purple
    "Assembly": "#3b82f6",        // Blue
    "Component": "#06b6d4",       // Cyan
    "Supplier": "#10b981",        // Emerald
    "Facility": "#f59e0b",        // Amber
    "Region": "#ec4899",          // Pink
    "DisruptionEvent": "#ef4444"  // Crimson
  };

  // 1. Initialize Cytoscape.js Instance
  function initCytoscape() {
    cy = cytoscape({
      container: document.getElementById("cy"),
      boxSelectionEnabled: false,
      autounselectify: false,
      style: [
        {
          selector: "node",
          style: {
            "label": "data(name)",
            "color": "#f3f4f6",
            "font-size": "11px",
            "font-family": "Inter, sans-serif",
            "text-valign": "bottom",
            "text-margin-y": 6,
            "background-color": function(ele) {
              const label = ele.data("label") || "Node";
              return LABEL_COLORS[label] || "#6b7280";
            },
            "width": 36,
            "height": 36,
            "border-width": 2,
            "border-color": "#ffffff",
            "border-opacity": 0.2,
            "transition-property": "background-color, line-color, target-arrow-color, width, height",
            "transition-duration": "0.3s"
          }
        },
        {
          selector: "node[label = 'DisruptionEvent']",
          style: {
            "shape": "diamond",
            "width": 46,
            "height": 46
          }
        },
        {
          selector: "node[label = 'Product']",
          style: {
            "shape": "pentagon",
            "width": 42,
            "height": 42
          }
        },
        {
          selector: "edge",
          style: {
            "width": 2,
            "line-color": "rgba(255, 255, 255, 0.15)",
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "target-arrow-color": "rgba(255, 255, 255, 0.2)",
            "arrow-scale": 0.8,
            "label": "data(type)",
            "font-size": "9px",
            "font-family": "JetBrains Mono, monospace",
            "color": "#9ca3af",
            "text-rotation": "autorotate",
            "text-background-opacity": 0.8,
            "text-background-color": "#0a0d14",
            "text-background-padding": "2px"
          }
        },
        {
          selector: ".highlighted",
          style: {
            "background-color": "#ef4444",
            "line-color": "#ef4444",
            "target-arrow-color": "#ef4444",
            "width": 44,
            "height": 44,
            "border-color": "#fef08a",
            "border-width": 3
          }
        },
        {
          selector: "edge.highlighted-edge",
          style: {
            "width": 4,
            "line-color": "#ef4444",
            "target-arrow-color": "#ef4444"
          }
        },
        {
          selector: ":selected",
          style: {
            "border-color": "#3b82f6",
            "border-width": 4,
            "border-opacity": 1.0
          }
        }
      ],
      layout: {
        name: "cose",
        animate: true,
        padding: 40,
        componentSpacing: 80,
        nodeOverlap: 20,
        idealEdgeLength: 90,
        edgeElasticity: 100
      }
    });

    // Node click handler -> Inspect details
    cy.on("tap", "node", (evt) => {
      const node = evt.target;
      inspectEntity(node.data(), "Node");
    });

    cy.on("tap", "edge", (evt) => {
      const edge = evt.target;
      inspectEntity(edge.data(), "Relationship");
    });
  }

  // 2. Load Database Connection Status
  async function checkDbStatus() {
    try {
      const res = await fetch("/api/status");
      const data = await res.json();

      if (data.is_live) {
        statusPill.className = "db-status-pill live";
        statusText.innerText = `Connected Live: CognoDB Cloud`;
        showToast("Connected to live CognoDB Cloud database!", "success");
      } else {
        statusPill.className = "db-status-pill demo";
        statusText.innerText = `Demo Engine (Local Mode)`;
      }
    } catch (err) {
      statusPill.className = "db-status-pill demo";
      statusText.innerText = `Demo Engine (Offline)`;
    }
  }

  // 3. Load Main Graph Overview
  async function loadGraphOverview() {
    showLoader(true);
    try {
      const res = await fetch("/api/graph/overview?limit=100");
      const data = await res.json();

      if (data.status === "success" && data.graph) {
        currentGraphData = data.graph;
        renderGraph(data.graph.nodes, data.graph.relationships);
      } else {
        showToast("Failed to fetch graph data", "error");
      }
    } catch (err) {
      console.error(err);
      showToast("Error loading graph overview", "error");
    } finally {
      showLoader(false);
    }
  }

  // 4. Render Nodes & Edges on Canvas
  function renderGraph(nodes, relationships) {
    if (!cy) return;

    cy.elements().remove();

    const cyNodes = nodes.map(n => ({
      data: {
        id: String(n.id),
        name: n.name || n.id,
        label: n.label || "Node",
        ...n
      }
    }));

    const cyEdges = relationships.map((r, idx) => ({
      data: {
        id: `rel-${idx}-${r.source}-${r.target}`,
        source: String(r.source),
        target: String(r.target),
        type: r.type || "CONNECTED_TO",
        ...(r.properties || {})
      }
    }));

    cy.add([...cyNodes, ...cyEdges]);
    cy.layout({ name: "cose", animate: true, padding: 50 }).run();

    // Update Top Counters
    statNodes.innerText = nodes.length;
    statEdges.innerText = relationships.length;

    // Fetch SPOF count for header counter
    fetchSpofCount();
  }

  // 5. Inspect Node/Relationship Properties
  function inspectEntity(data, type) {
    inspectorTitle.innerHTML = `<i class="fa-solid fa-circle-nodes"></i> ${type}: ${data.name || data.id || data.type}`;
    
    const label = data.label || "Entity";
    const badgeColor = LABEL_COLORS[label] || "#3b82f6";

    let html = `
      <div class="prop-badge" style="background:${badgeColor}22; color:${badgeColor}; border:1px solid ${badgeColor}66">
        ${label} • ${data.id || ''}
      </div>
      <table class="prop-table">
    `;

    for (const [key, val] of Object.entries(data)) {
      if (key === "id" || key === "label" || key === "name") continue;
      const displayVal = typeof val === "object" ? JSON.stringify(val) : val;
      html += `
        <tr>
          <th>${key}</th>
          <td>${displayVal}</td>
        </tr>
      `;
    }

    html += `</table>`;

    if (type === "Node") {
      html += `
        <button id="btn-inspect-lineage" class="btn btn-secondary btn-block" style="margin-top:16px;">
          <i class="fa-solid fa-diagram-nested"></i> Trace Lineage Tree
        </button>
      `;
    }

    inspectorBody.innerHTML = html;

    const btnLineage = document.getElementById("btn-inspect-lineage");
    if (btnLineage) {
      btnLineage.addEventListener("click", () => traceLineage(data.id));
    }
  }

  // Close Inspector Panel
  const btnCloseInspector = document.getElementById("btn-close-inspector");
  if (btnCloseInspector) {
    btnCloseInspector.addEventListener("click", () => {
      inspectorBody.innerHTML = `
        <div class="empty-state">
          <i class="fa-solid fa-hand-pointer"></i>
          <p>Select a node or relationship on the canvas to inspect details and query lineage.</p>
        </div>
      `;
      inspectorTitle.innerHTML = `<i class="fa-solid fa-circle-nodes"></i> Entity Inspector`;
    });
  }
  }

  // Trace Lineage Tree
  async function traceLineage(entityId) {
    showLoader(true);
    try {
      const res = await fetch("/api/cypher/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cypher: "MATCH path = (n)-[*1..4]->(m) WHERE n.id = $id RETURN path",
          parameters: { id: entityId }
        })
      });
      const data = await res.json();
      if (data.status === "success" && data.graph && data.graph.nodes.length > 0) {
        renderGraph(data.graph.nodes, data.graph.relationships);
        showToast(`Lineage tree rendered for ${entityId}`, "success");
      }
    } catch (err) {
      console.error(err);
    } finally {
      showLoader(false);
    }
  }

  // 6. Multi-hop Disruption Simulator
  const btnRunSimulation = document.getElementById("btn-run-simulation");
  if (btnRunSimulation) {
    btnRunSimulation.addEventListener("click", async () => {
      const disruptionId = document.getElementById("disruption-select").value;
      showLoader(true);

      try {
        const res = await fetch("/api/disruptions/simulate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ disruption_id: disruptionId })
        });
        const data = await res.json();

        if (data.status === "success") {
          const graph = data.graph;
          renderGraph(graph.nodes, graph.relationships);

          // Highlight Disruption Paths on Canvas
          cy.batch(() => {
            cy.nodes().addClass("highlighted");
            cy.edges().addClass("highlighted-edge");
          });

          // Show Summary Metrics
          const summaryCard = document.getElementById("simulation-summary");
          summaryCard.classList.remove("hidden");
          
          if (data.records && data.records.length > 0) {
            const rec = data.records[0];
            document.getElementById("sim-hops").innerText = rec.hops || 4;
            document.getElementById("sim-products").innerText = (rec.affected_products || []).join(", ") || "QuantumDrive Server X, Nexus Router";
            document.getElementById("sim-revenue").innerText = `$${rec.revenue_impact_m || '73.5'}M`;
          }

          showToast("Multi-hop blast radius simulation complete!", "success");
        }
      } catch (err) {
        showToast("Error running disruption simulation", "error");
      } finally {
        showLoader(false);
      }
    });
  }

  // 7. Single Point of Failure (SPOF) Risks
  async function fetchSpofCount() {
    try {
      const res = await fetch("/api/analytics/spof");
      const data = await res.json();
      if (data.records) {
        statSpof.innerText = data.records.length;
      }
    } catch (e) {}
  }

  const btnLoadSpof = document.getElementById("btn-load-spof");
  if (btnLoadSpof) {
    btnLoadSpof.addEventListener("click", async () => {
      showLoader(true);
      try {
        const res = await fetch("/api/analytics/spof");
        const data = await res.json();

        const container = document.getElementById("spof-list");
        container.innerHTML = "";

        if (data.records && data.records.length > 0) {
          data.records.forEach(rec => {
            const card = document.createElement("div");
            card.className = "summary-card";
            card.style.marginBottom = "10px";
            card.innerHTML = `
              <h4><i class="fa-solid fa-triangle-exclamation text-danger"></i> ${rec.component_name}</h4>
              <div class="stat-row"><span>Sole Supplier:</span><strong>${rec.sole_supplier}</strong></div>
              <div class="stat-row"><span>Impacted Products:</span><strong>${(rec.affected_products || []).join(", ")}</strong></div>
              <div class="stat-row"><span>Revenue Exposure:</span><strong class="text-warning">$${rec.revenue_at_risk_m || 0}M</strong></div>
            `;
            container.appendChild(card);
          });
          if (data.graph) {
            renderGraph(data.graph.nodes, data.graph.relationships);
          }
        }
      } catch (err) {
        showToast("Failed to run SPOF query", "error");
      } finally {
        showLoader(false);
      }
    });
  }

  // 8. Find Alternate Supply Routes
  const btnFindRoutes = document.getElementById("btn-find-routes");
  if (btnFindRoutes) {
    btnFindRoutes.addEventListener("click", async () => {
      const supplierId = document.getElementById("supplier-select").value;
      showLoader(true);

      try {
        const res = await fetch("/api/analytics/alternate-routes", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ supplier_id: supplierId })
        });
        const data = await res.json();

        const container = document.getElementById("routes-results");
        container.innerHTML = "";

        if (data.records && data.records.length > 0) {
          data.records.forEach(rec => {
            const card = document.createElement("div");
            card.className = "summary-card";
            card.style.marginBottom = "10px";
            card.innerHTML = `
              <h4><i class="fa-solid fa-square-check text-success"></i> Backup: ${rec.alt_supplier}</h4>
              <div class="stat-row"><span>Component:</span><strong>${rec.component}</strong></div>
              <div class="stat-row"><span>Switching Days:</span><strong>${rec.switching_days} Days</strong></div>
              <div class="stat-row"><span>Extra Cost:</span><strong>+${rec.extra_cost_pct}%</strong></div>
              <div class="stat-row"><span>Supplier Rating:</span><strong class="text-warning">★ ${rec.alt_rating}</strong></div>
            `;
            container.appendChild(card);
          });
          if (data.graph) {
            renderGraph(data.graph.nodes, data.graph.relationships);
          }
        }
      } catch (err) {
        showToast("Failed to find alternate routes", "error");
      } finally {
        showLoader(false);
      }
    });
  }

  // 9. openCypher Console Execution
  const btnRunCypher = document.getElementById("btn-run-cypher");
  if (btnRunCypher) {
    btnRunCypher.addEventListener("click", async () => {
      const cypherText = document.getElementById("cypher-input").value;
      if (!cypherText.trim()) return;

      showLoader(true);
      try {
        const res = await fetch("/api/cypher/execute", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ cypher: cypherText })
        });
        const data = await res.json();

        if (data.status === "success") {
          renderCypherTable(data.records);
          if (data.graph && data.graph.nodes.length > 0) {
            renderGraph(data.graph.nodes, data.graph.relationships);
          }
          showToast("Cypher statement executed successfully", "success");
        } else {
          showToast(`Cypher Error: ${data.error}`, "error");
        }
      } catch (err) {
        showToast("Error executing Cypher", "error");
      } finally {
        showLoader(false);
      }
    });
  }

  // Format Tabular Cypher Query Output
  function renderCypherTable(records) {
    cypherResultsContainer.classList.remove("hidden");
    const wrapper = document.getElementById("cypher-table-wrapper");

    if (!records || records.length === 0) {
      wrapper.innerHTML = `<p style="font-size:0.8rem; color:var(--text-muted);">Query returned 0 records.</p>`;
      return;
    }

    const headers = Object.keys(records[0]);
    let html = `<table class="cypher-table"><thead><tr>`;
    headers.forEach(h => html += `<th>${h}</th>`);
    html += `</tr></thead><tbody>`;

    records.forEach(row => {
      html += `<tr>`;
      headers.forEach(h => {
        const val = typeof row[h] === "object" ? JSON.stringify(row[h]) : row[h];
        html += `<td>${val}</td>`;
      });
      html += `</tr>`;
    });

    html += `</tbody></table>`;
    wrapper.innerHTML = html;
  }

  // 10. Seed Button Trigger
  const btnSeed = document.getElementById("btn-seed");
  if (btnSeed) {
    btnSeed.addEventListener("click", async () => {
      if (!confirm("Re-seed CognoDB Cloud with baseline graph dataset?")) return;
      showLoader(true);
      try {
        const res = await fetch("/api/seed", { method: "POST" });
        const data = await res.json();
        if (data.status === "success") {
          showToast(data.message, "success");
          loadGraphOverview();
        } else {
          showToast(data.message, "error");
        }
      } catch (err) {
        showToast("Error seeding database", "error");
      } finally {
        showLoader(false);
      }
    });
  }

  // Search filter box
  const searchInput = document.getElementById("search-input");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      const term = e.target.value.toLowerCase().trim();
      if (!cy) return;

      if (!term) {
        cy.nodes().removeClass("highlighted");
        return;
      }

      cy.nodes().forEach(node => {
        const name = (node.data("name") || "").toLowerCase();
        if (name.includes(term)) {
          node.addClass("highlighted");
        } else {
          node.removeClass("highlighted");
        }
      });
    });
  }

  // Reset zoom view button
  const btnResetZoom = document.getElementById("btn-reset-zoom");
  if (btnResetZoom) {
    btnResetZoom.addEventListener("click", () => {
      if (cy) {
        cy.nodes().removeClass("highlighted");
        cy.edges().removeClass("highlighted-edge");
        cy.fit();
      }
    });
  }

  // Reload graph button
  const btnReloadGraph = document.getElementById("btn-reload-graph");
  if (btnReloadGraph) {
    btnReloadGraph.addEventListener("click", loadGraphOverview);
  }

  // Tab Switching Logic
  navItems.forEach(item => {
    item.addEventListener("click", () => {
      navItems.forEach(n => n.classList.remove("active"));
      tabPanels.forEach(p => p.classList.remove("active"));

      item.classList.add("active");
      const targetTab = item.getAttribute("data-tab");
      document.getElementById(targetTab).classList.add("active");
    });
  });

  // Helper functions
  function showLoader(show) {
    if (show) graphLoader.classList.remove("hidden");
    else graphLoader.classList.add("hidden");
  }

  function showToast(msg, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `<i class="fa-solid fa-circle-info"></i> <span>${msg}</span>`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  }

  // Initialize
  initCytoscape();
  checkDbStatus();
  loadGraphOverview();
});
