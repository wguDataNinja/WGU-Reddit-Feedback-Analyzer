(function () {
  const root = document.getElementById("wra-courses");
  if (!root) return;

  const elQ = document.getElementById("wra-course-q");
  const elCollege = document.getElementById("wra-college");
  const elStatus = document.getElementById("wra-course-status");
  const elFilterStatus = document.getElementById("wra-course-filter-status");
  const elList = document.getElementById("wra-course-list");

  if (!elList || !elQ || !elCollege) return;

  const cards = Array.from(elList.querySelectorAll(".wra-card"));
  const items = cards.map(card => {
    const code = String(card.getAttribute("data-code") || "");
    const title = String(card.getAttribute("data-title") || "");
    const rawColleges = String(card.getAttribute("data-colleges") || "");
    const colleges = rawColleges
      .split("|")
      .map(c => String(c || "").trim())
      .filter(Boolean);

    return {
      el: card,
      code,
      title,
      colleges,
      search: (code + " " + title).toLowerCase()
    };
  });

  function norm(s) {
    return String(s || "").toLowerCase();
  }

  function fillCollegeSelect() {
    const set = new Set();
    for (const item of items) {
      for (const c of item.colleges) set.add(c);
    }
    const sorted = Array.from(set).sort((a, b) => a.localeCompare(b));
    for (const c of sorted) {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      elCollege.appendChild(opt);
    }
  }

  function getUrlState() {
    const u = new URL(window.location.href);
    return {
      q: (u.searchParams.get("q") || "").trim(),
      college: (u.searchParams.get("college") || "").trim()
    };
  }

  function applyUrlStateOnce() {
    const st = getUrlState();

    if (st.q) elQ.value = st.q;

    if (st.college) {
      const desired = String(st.college).trim().toLowerCase();
      const match = Array.from(elCollege.options).find(o => norm(o.value) === desired);
      if (match) elCollege.value = match.value;
    }
  }

  function updateFilterStatus(visibleCount) {
    if (!elFilterStatus) return;

    const q = String(elQ.value || "").trim();
    const college = String(elCollege.value || "").trim();

    const parts = [];
    parts.push(college ? ("College: " + college) : "College: All");
    if (q) parts.push("Keyword: " + q);
    parts.push("Matching courses: " + visibleCount);

    elFilterStatus.textContent = parts.join(" | ");
  }

  function applyFilters() {
    const q = norm(elQ.value).trim();
    const college = norm(elCollege.value).trim();
    let visible = 0;

    for (const item of items) {
      let ok = true;
      if (q) ok = item.search.includes(q);
      if (ok && college) {
        ok = item.colleges.some(c => norm(c) === college);
      }
      item.el.style.display = ok ? "" : "none";
      if (ok) visible += 1;
    }

    elStatus.textContent = `Loaded ${items.length}. Showing ${visible}.`;
    updateFilterStatus(visible);
  }

  function wire() {
    let t = null;
    elQ.addEventListener("input", () => {
      if (t) clearTimeout(t);
      t = setTimeout(applyFilters, 150);
    });
    elCollege.addEventListener("change", applyFilters);
  }

  fillCollegeSelect();
  applyUrlStateOnce();
  wire();
  applyFilters();
})();
