const houseInput = document.getElementById("house_name");
const refreshBtn = document.getElementById("refreshBtn");
const loadBtn = document.getElementById("loadBtn");
const salesList = document.getElementById("salesList");
const saleDetail = document.getElementById("saleDetail");
const lotsList = document.getElementById("lotsList");
const statusBox = document.getElementById("statusBox");
const csvLink = document.getElementById("csvLink");
const xlsxLink = document.getElementById("xlsxLink");

let currentSales = [];
let selectedSaleId = null;

function badgeStatus(status) {
  if (status === "En cours") return "status-running";
  if (status === "À venir") return "status-upcoming";
  return "status-ended";
}

function badgeType(type) {
  if ((type || "").toLowerCase() === "live") return "type-live";
  if ((type || "").toLowerCase() === "chrono") return "type-chrono";
  return "type-catalogue";
}

function setExportLinks() {
  const house = houseInput.value.trim();
  const suffix = house ? `?house_name=${encodeURIComponent(house)}` : "";
  csvLink.href = `/api/export/csv${suffix}`;
  xlsxLink.href = `/api/export/xlsx${suffix}`;
}

async function loadSales() {
  const house = houseInput.value.trim();
  setExportLinks();

  const url = house
    ? `/api/sales?house_name=${encodeURIComponent(house)}`
    : "/api/sales";

  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error("Impossible de charger les ventes.");
  }

  currentSales = await resp.json();
  renderSales();

  if (currentSales.length) {
    selectedSaleId = selectedSaleId || currentSales[0].id;
    await loadSaleDetail(selectedSaleId);
  } else {
    selectedSaleId = null;
    saleDetail.innerHTML = "Aucune vente sélectionnée.";
    lotsList.innerHTML = "";
  }
}

function renderSales() {
  salesList.innerHTML = "";

  currentSales.forEach((sale) => {
    const div = document.createElement("div");
    div.className = `sale-card ${sale.id === selectedSaleId ? "active" : ""}`;

    div.innerHTML = `
      <div class="badges">
        <span class="badge ${badgeStatus(sale.status)}">${sale.status || "Statut inconnu"}</span>
        <span class="badge ${badgeType(sale.type)}">${sale.type || "Type inconnu"}</span>
        ${sale.results_available ? '<span class="badge">Résultats</span>' : ""}
      </div>
      <strong>${sale.title}</strong>
      <div class="meta" style="margin-top:10px;">
        <div><small class="muted">Maison</small><br>${sale.house_name || "-"}</div>
        <div><small class="muted">Date</small><br>${sale.start_at ? new Date(sale.start_at).toLocaleString("fr-FR") : "-"}</div>
        <div><small class="muted">Lieu</small><br>${[sale.postal_code, sale.city, sale.country].filter(Boolean).join(" ")}</div>
        <div><small class="muted">Source</small><br><a href="${sale.external_url}" target="_blank">ouvrir</a></div>
      </div>
    `;

    div.addEventListener("click", async () => {
      selectedSaleId = sale.id;
      renderSales();
      await loadSaleDetail(sale.id);
    });

    salesList.appendChild(div);
  });
}

async function loadSaleDetail(saleId) {
  const [saleResp, lotResp] = await Promise.all([
    fetch(`/api/sales/${saleId}`),
    fetch(`/api/sales/${saleId}/lots`)
  ]);

  if (!saleResp.ok || !lotResp.ok) {
    throw new Error("Impossible de charger le détail de la vente.");
  }

  const sale = await saleResp.json();
  const lots = await lotResp.json();

  saleDetail.innerHTML = `
    <h3 style="margin-top:0">${sale.title}</h3>
    <div class="meta">
      <div><small class="muted">Maison de vente</small><br>${sale.house_name || "-"}</div>
      <div><small class="muted">Date / heure</small><br>${sale.start_at ? new Date(sale.start_at).toLocaleString("fr-FR") : "-"}</div>
      <div><small class="muted">Type</small><br>${sale.type || "-"}</div>
      <div><small class="muted">Statut</small><br>${sale.status || "-"}</div>
      <div><small class="muted">Localisation</small><br>${[sale.postal_code, sale.city, sale.country].filter(Boolean).join(" ") || "-"}</div>
      <div><small class="muted">Résultats</small><br>${sale.result_summary || "-"}</div>
      <div style="grid-column:1 / -1">
        <small class="muted">URL source</small><br>
        <a href="${sale.external_url}" target="_blank">${sale.external_url}</a>
      </div>
    </div>
  `;

  lotsList.innerHTML = "";

  if (!lots.length) {
    lotsList.innerHTML = '<div class="detail empty">Aucun lot enregistré pour cette vente.</div>';
    return;
  }

  lots.forEach((lot) => {
    const card = document.createElement("div");
    card.className = "lot-card";

    card.innerHTML = `
      <div>
        ${lot.image_url ? `<img src="${lot.image_url}" alt="Photo du lot">` : '<img alt="Photo non disponible">'}
      </div>
      <div>
        <p class="lot-title">
          <strong>${lot.lot_number ? "Lot " + lot.lot_number + " — " : ""}</strong>${lot.title}
        </p>
        <div class="lot-meta">
          ${lot.result_status ? `<span class="badge result-badge">${lot.result_status}</span>` : '<span class="badge result-badge">Sans résultat</span>'}
          ${lot.result_amount ? `<span class="badge result-badge">${lot.result_amount}</span>` : ""}
          ${lot.public_url ? `<a class="badge result-badge" href="${lot.public_url}" target="_blank">Fiche lot</a>` : ""}
        </div>
      </div>
    `;

    lotsList.appendChild(card);
  });
}

async function refreshHouse() {
  const house = houseInput.value.trim();

  if (!house) {
    statusBox.textContent = "Merci de saisir un nom de maison de vente ou une URL Interencheres.";
    return;
  }

  statusBox.textContent = `Actualisation en cours pour « ${house} »...`;
  setExportLinks();

  try {
    const resp = await fetch(`/api/refresh?house_name=${encodeURIComponent(house)}`, {
      method: "POST"
    });

    if (!resp.ok) {
      let message = "Échec de l’actualisation.";
      try {
        const data = await resp.json();
        if (data.detail) {
          message = data.detail;
        }
      } catch (_) {}
      throw new Error(message);
    }

    const data = await resp.json();

    statusBox.textContent =
      `Terminé — Maison détectée: ${data.matched_house}. ` +
      `Ventes créées: ${data.created_sales}, ` +
      `ventes mises à jour: ${data.updated_sales}, ` +
      `lots créés: ${data.created_lots}, ` +
      `lots mis à jour: ${data.updated_lots}.`;

    await loadSales();
  } catch (e) {
    statusBox.textContent = `Erreur: ${e.message}`;
  }
}

refreshBtn.addEventListener("click", refreshHouse);

loadBtn.addEventListener("click", async () => {
  statusBox.textContent = "Chargement de la base locale...";
  try {
    await loadSales();
    statusBox.textContent = `${currentSales.length} vente(s) chargée(s).`;
  } catch (e) {
    statusBox.textContent = `Erreur: ${e.message}`;
  }
});

setExportLinks();
