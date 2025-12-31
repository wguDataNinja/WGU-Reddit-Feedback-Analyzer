(function () {
  const root = document.getElementById("wra-raw-posts");
  if (!root) return;

  const indexUrl = root.getAttribute("data-index-url");
  const elQ = document.getElementById("wra-q");
  const elCourse = document.getElementById("wra-course");
  const elPageSize = document.getElementById("wra-page-size");
  const elStatus = document.getElementById("wra-status");
  const elFilterStatus = document.getElementById("wra-filter-status");
  const elResults = document.getElementById("wra-results");
  const elPrev = document.getElementById("wra-prev");
  const elNext = document.getElementById("wra-next");
  const elPage = document.getElementById("wra-page");

  let all = [];
  let filtered = [];
  let page = 1;

  const BODY_PREVIEW_CHARS = 240;

  function norm(s) { return String(s || "").toLowerCase(); }

  function stripUrls(s) {
    return String(s || "").replace(/https?:\/\/\S+/g, "").replace(/\s+/g, " ").trim();
  }

  function trunc(s, n) {
    const x = String(s || "").replace(/\s+/g, " ").trim();
    if (!x) return "";
    return x.length <= n ? x : (x.slice(0, n - 1) + "…");
  }

  function fmtDate(utc) {
    const n = Number(utc);
    if (!Number.isFinite(n) || n <= 0) return "";
    const d = new Date(n * 1000);
    if (isNaN(d.getTime())) return "";
    return d.toISOString().slice(0, 10);
  }

  function getCourseCode(p) {
    if (!p || typeof p !== "object") return "";
    // tolerate alternate keys
    const v = p.course_code || p.course || p.courseCode || "";
    return String(v || "").trim().toUpperCase();
  }

  function getBody(p) {
    if (!p || typeof p !== "object") return "";
    // tolerate alternate trunc fields
    return String(p.body_trunc_1k || p.body_trunc || p.body || "");
  }

  function toPostList(data) {
    if (Array.isArray(data)) return data;
    if (data && typeof data === "object") {
      const candidates = ["posts", "post_index", "items", "data"];
      for (const k of candidates) {
        if (Array.isArray(data[k])) return data[k];
      }
      // map-of-objects fallback
      const keys = Object.keys(data);
      if (keys.length && data[keys[0]] && typeof data[keys[0]] === "object") {
        return keys.map(id => {
          const o = data[id];
          if (o && typeof o === "object" && !o.post_id) o.post_id = id;
          return o;
        });
      }
    }
    return null;
  }

  function uniqCourses(posts) {
    const s = new Set();
    for (const p of posts) {
      const cc = getCourseCode(p);
      if (cc) s.add(cc);
    }
    return Array.from(s).sort((a, b) => a.localeCompare(b));
  }

  function fillCourseSelect(posts) {
    elCourse.innerHTML = '<option value="">All courses</option>';
    const courses = uniqCourses(posts);
    for (const c of courses) {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      elCourse.appendChild(opt);
    }
  }

  function getUrlState() {
    const u = new URL(window.location.href);
    return {
      q: (u.searchParams.get("q") || "").trim(),
      course: (u.searchParams.get("course") || "").trim(),
      pageSize: (u.searchParams.get("pagesize") || "").trim()
    };
  }

  function applyUrlStateOnce() {
    const st = getUrlState();

    if (st.q) elQ.value = st.q;

    if (st.pageSize && elPageSize) {
      const allowed = new Set(Array.from(elPageSize.options).map(o => String(o.value)));
      if (allowed.has(String(st.pageSize))) elPageSize.value = String(st.pageSize);
    }

    if (st.course) {
      const desired = String(st.course).trim().toUpperCase();
      const hasOption = Array.from(elCourse.options).some(o => String(o.value).toUpperCase() === desired);
      if (hasOption) elCourse.value = desired;
    }
  }

  function updateFilterStatus() {
    if (!elFilterStatus) return;

    const course = String(elCourse.value || "").trim();
    const q = String(elQ.value || "").trim();

    const courseSet = new Set();
    for (const p of filtered) {
      const cc = getCourseCode(p);
      if (cc) courseSet.add(cc);
    }

    const parts = [];
    parts.push(course ? ("Course: " + course) : "Course: All");
    if (q) parts.push("Keyword: " + q);
    parts.push("Matching posts: " + filtered.length);
    parts.push("Matching courses: " + courseSet.size);

    elFilterStatus.textContent = parts.join(" | ");
  }

  function applyFilters() {
    const q = norm(elQ.value).trim();
    const course = String(elCourse.value || "").trim().toUpperCase();

    filtered = all.filter(p => {
      if (!p) return false;
      const cc = getCourseCode(p);
      if (course && cc !== course) return false;
      if (!q) return true;
      const t = norm(p.title);
      const b = norm(getBody(p));
      return t.includes(q) || b.includes(q);
    });

    page = 1;
    render();
  }

  function pageSize() {
    const n = Number(elPageSize.value);
    return Number.isFinite(n) && n > 0 ? n : 50;
  }

  function bestRedditUrl(p) {
    const permalink = String(p.permalink || "");
    if (permalink) return "https://www.reddit.com" + permalink;
    const url = String(p.url || "");
    return url || "";
  }

  function render() {
    const ps = pageSize();
    const total = filtered.length;
    const totalPages = Math.max(1, Math.ceil(total / ps));
    if (page > totalPages) page = totalPages;

    const start = (page - 1) * ps;
    const end = start + ps;
    const slice = filtered.slice(start, end);

    elResults.innerHTML = "";
    for (const p of slice) {
      const code = getCourseCode(p);
      const postTitle = String(p.title || "(untitled)");
      const url = bestRedditUrl(p);
      const created = fmtDate(p.created_utc);
      const bodyPreview = trunc(stripUrls(getBody(p)), BODY_PREVIEW_CHARS);

      const card = document.createElement("div");
      card.className = "wra-card";

      const h2 = document.createElement("h2");
      h2.textContent = postTitle;
      card.appendChild(h2);

      const meta = document.createElement("div");
      meta.className = "wra-meta";

      if (code) {
        const small = document.createElement("span");
        small.className = "wra-muted";
        small.textContent = code;
        meta.appendChild(small);
      }

      const b2 = document.createElement("span");
      b2.className = "wra-badge";
      b2.textContent = created ? created : "no date";
      meta.appendChild(b2);

      if (url) {
        const a = document.createElement("a");
        a.href = url;
        a.target = "_blank";
        a.rel = "noreferrer";
        a.textContent = "Open on Reddit";
        meta.appendChild(a);
      }

      card.appendChild(meta);

      const pBody = document.createElement("p");
      pBody.className = "wra-muted";
      pBody.textContent = bodyPreview ? bodyPreview : "No text available.";
      card.appendChild(pBody);

      elResults.appendChild(card);
    }

    elStatus.textContent = `Loaded ${all.length}. Showing ${slice.length} of ${total}.`;
    elPage.textContent = `Page ${page} of ${totalPages}`;
    elPrev.disabled = page <= 1;
    elNext.disabled = page >= totalPages;

    updateFilterStatus();
  }

  function wire() {
    let t = null;
    elQ.addEventListener("input", () => {
      if (t) clearTimeout(t);
      t = setTimeout(applyFilters, 150);
    });
    elCourse.addEventListener("change", applyFilters);
    elPageSize.addEventListener("change", applyFilters);
    elPrev.addEventListener("click", () => { page = Math.max(1, page - 1); render(); });
    elNext.addEventListener("click", () => { page = page + 1; render(); });
  }

  async function load() {
    try {
      elStatus.textContent = "Loading…";

      const res = await fetch(indexUrl, { cache: "no-store" });
      if (!res.ok) throw new Error(`fetch ${indexUrl} HTTP ${res.status}`);
      const data = await res.json();

      const list = toPostList(data);
      if (!list) throw new Error("Unsupported post_index.json shape");

      all = list;
      fillCourseSelect(all);

      wire();

      applyUrlStateOnce();
      applyFilters();
    } catch (e) {
      const msg = String(e && e.message ? e.message : e);
      elStatus.textContent = `Failed to load posts: ${msg}`;
      if (elFilterStatus) elFilterStatus.textContent = "";
      elResults.innerHTML = `<div class="wra-card"><p class="wra-muted">${msg}</p></div>`;
      elPrev.disabled = true;
      elNext.disabled = true;
      console.error(e);
    }
  }

  load();
})();