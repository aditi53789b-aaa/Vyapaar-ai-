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

  // Invoices Generator Form
  const invForm = document.getElementById("invForm");
  const invBody = document.getElementById("invBody");
  let invCounter = 104;

  if (invForm && invBody) {
    invForm.addEventListener("submit", function (event) {
      event.preventDefault();
      const dict = translations[getCurrentLang()] || translations.en;

      const cust = document.getElementById("invCust").value.trim();
      const item = document.getElementById("invItem").value.trim();
      const amt = Number(document.getElementById("invAmt").value);
      const status = document.getElementById("invStatus").value;

      if (!cust || !item || amt <= 0) return;

      const tr = document.createElement("tr");

      const tdId = document.createElement("td");
      tdId.textContent = "#INV-" + invCounter++;

      const tdCust = document.createElement("td");
      tdCust.textContent = cust;

      const tdItem = document.createElement("td");
      tdItem.textContent = item;

      const tdAmt = document.createElement("td");
      tdAmt.textContent = amt + " INR";

      const tdStat = document.createElement("td");
      const span = document.createElement("span");
      span.className = status === "udhar" ? "badgeudhar" : "badgepaid";
      span.textContent = status === "udhar" ? dict.statusUdhar : dict.statusPaid;
      tdStat.appendChild(span);

      tr.appendChild(tdId);
      tr.appendChild(tdCust);
      tr.appendChild(tdItem);
      tr.appendChild(tdAmt);
      tr.appendChild(tdStat);
      invBody.prepend(tr);

      invForm.reset();
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