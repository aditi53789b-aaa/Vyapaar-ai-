document.addEventListener("DOMContentLoaded", function () {
  let currentLang = getCurrentLang();
  applyLanguage(currentLang);

  // Language switcher
  const langBtn = document.getElementById("langBtn");
  if (langBtn) {
    langBtn.addEventListener("click", function () {
      currentLang = currentLang === "en" ? "hi" : "en";
      localStorage.setItem("bolokhata_lang", currentLang);
      applyLanguage(currentLang);
    });
  }

  // Dashboard Voice Recorder simulation
  const micBtn = document.getElementById("micBtn");
  const statusEl = document.getElementById("status");
  let isRecording = false;

  if (micBtn && statusEl) {
    micBtn.addEventListener("click", function () {
      const dict = translations[getCurrentLang()] || translations.en;
      isRecording = !isRecording;

      if (isRecording) {
        micBtn.classList.add("active");
        micBtn.textContent = dict.btnStopSpeak;
        statusEl.textContent = dict.statusListening;
      } else {
        micBtn.classList.remove("active");
        micBtn.textContent = dict.btnTapSpeak;
        statusEl.textContent = dict.statusReady;
      }
    });
  }

  // Dashboard Quick Manual Entry
  const quickForm = document.getElementById("quickForm");
  const ledgerList = document.getElementById("ledgerList");

  if (quickForm && ledgerList) {
    quickForm.addEventListener("submit", function (event) {
      event.preventDefault();
      const cust = document.getElementById("qCust").value.trim();
      const amt = Number(document.getElementById("qAmt").value);
      const type = document.getElementById("qType").value;

      if (!cust || amt <= 0) return;

      const row = document.createElement("div");
      row.className = "ledgerrow";

      const info = document.createElement("div");
      const nameEl = document.createElement("strong");
      nameEl.textContent = cust;
      const subEl = document.createElement("span");
      subEl.className = "sub";
      subEl.textContent = type === "udhar" ? "Pending Udhar" : "Cash Sale";
      info.appendChild(nameEl);
      info.appendChild(subEl);

      const badge = document.createElement("span");
      badge.className = type === "udhar" ? "badgeudhar" : "badgepaid";
      badge.textContent = amt + " INR";

      row.appendChild(info);
      row.appendChild(badge);
      ledgerList.prepend(row);

      quickForm.reset();
    });
  }

  // Persist invoices through the authenticated API; never add demo rows.
  const invForm = document.getElementById("invForm");
  const invBody = document.getElementById("invBody");
  const API = (window.BOLOKHATA_API_URL || ((["localhost","127.0.0.1"].includes(location.hostname) && location.port && location.port !== "8000") ? "http://127.0.0.1:8000" : location.origin)).replace(/\/$/, "");
  const token = sessionStorage.getItem("bolokhaata_token") || localStorage.getItem("bolokhaata_token");

  async function refreshInvoices() {
    if (!invBody) return;
    const response = await fetch(API + "/api/v1/invoices", { headers: { Authorization: "Bearer " + token } });
    if (response.status === 401) { location.href = "auth.html?mode=login"; return; }
    if (!response.ok) throw new Error("Could not load invoices.");
    const payload = await response.json();
    invBody.replaceChildren();
    (payload.items || []).forEach(invoice => {
      const tr = document.createElement("tr");
      [invoice.invoice_number, invoice.customer_name, invoice.item_description || "—", Number(invoice.total).toLocaleString("en-IN") + " INR"].forEach(value => {
        const td = document.createElement("td"); td.textContent = value; tr.appendChild(td);
      });
      const statusCell = document.createElement("td");
      const badge = document.createElement("span");
      badge.className = invoice.payment_status === "udhar" ? "badgeudhar" : "badgepaid";
      badge.textContent = invoice.payment_status === "udhar" ? "Pending Udhar" : "Paid";
      statusCell.appendChild(badge); tr.appendChild(statusCell); invBody.appendChild(tr);
    });
    if (!(payload.items || []).length) {
      const tr = document.createElement("tr"), td = document.createElement("td");
      td.colSpan = 5; td.textContent = "No invoices yet."; tr.appendChild(td); invBody.appendChild(tr);
    }
  }

  if (invForm && invBody) {
    if (!token) location.href = "auth.html?mode=login";
    refreshInvoices().catch(error => { const tr=document.createElement("tr"),td=document.createElement("td");td.colSpan=5;td.textContent=error.message;tr.appendChild(td);invBody.replaceChildren(tr); });
    invForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      const button = invForm.querySelector('button[type="submit"]');
      button.disabled = true;
      try {
        const response = await fetch(API + "/api/v1/invoices", {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
          body: JSON.stringify({
            customer_name: document.getElementById("invCust").value.trim(),
            item_description: document.getElementById("invItem").value.trim(),
            total: Number(document.getElementById("invAmt").value),
            payment_status: document.getElementById("invStatus").value
          })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Invoice could not be saved.");
        invForm.reset();
        await refreshInvoices();
      } catch (error) {
        alert(error.message);
      } finally { button.disabled = false; }
    });
  }

  // Schemes Page Readiness Check
  const applyBtns = document.querySelectorAll(".applybtn");
  const schemeNotice = document.getElementById("schemeNotice");

  if (applyBtns.length > 0 && schemeNotice) {
    applyBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        const dict = translations[getCurrentLang()] || translations.en;
        schemeNotice.textContent = dict.schemeReadyMsg;
      });
    });
  }
});