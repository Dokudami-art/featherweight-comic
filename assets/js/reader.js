/* Featherweight reader — progress, auto-hiding bar, keyboard nav, resume.
   Everything here is an enhancement: with JS off the chapter still reads. */
(function () {
  "use strict";
  var tag  = document.currentScript;
  var id   = tag.dataset.chapter || "ch";
  var prev = tag.dataset.prev || "";
  var next = tag.dataset.next || "";
  var KEY  = "fw:pos:" + id;

  var bar    = document.getElementById("readerbar");
  var pbar   = document.getElementById("pbar");
  var resume = document.getElementById("resume");
  var help   = document.getElementById("helppanel");

  function maxScroll() {
    return Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
  }
  function frac() { return window.scrollY / maxScroll(); }

  /* ---- progress bar + auto-hiding header ---- */
  var lastY = window.scrollY, ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      var y = window.scrollY;
      pbar.style.width = Math.min(100, frac() * 100).toFixed(2) + "%";
      if (y > lastY + 6 && y > 300) bar.classList.add("hidden");
      else if (y < lastY - 6) bar.classList.remove("hidden");
      lastY = y;
      ticking = false;
    });
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });

  /* ---- remember position ---- */
  var saveTimer;
  function save() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      try { localStorage.setItem(KEY, frac().toFixed(4)); } catch (e) {}
    }, 400);
  }
  window.addEventListener("scroll", save, { passive: true });
  window.addEventListener("pagehide", function () {
    try { localStorage.setItem(KEY, frac().toFixed(4)); } catch (e) {}
  });

  /* ---- offer to resume ---- */
  var saved = 0;
  try { saved = parseFloat(localStorage.getItem(KEY) || "0"); } catch (e) {}
  if (resume && saved > 0.04 && saved < 0.95 && window.scrollY < 40) {
    resume.hidden = false;
    document.getElementById("resumego").addEventListener("click", function () {
      window.scrollTo({ top: saved * maxScroll(), behavior: "auto" });
      resume.hidden = true;
    });
    document.getElementById("resumeno").addEventListener("click", function () {
      try { localStorage.removeItem(KEY); } catch (e) {}
      resume.hidden = true;
    });
    setTimeout(function () { resume.hidden = true; }, 12000);
  }

  /* ---- help panel ---- */
  function toggleHelp(on) {
    if (!help) return;
    help.hidden = on === undefined ? !help.hidden : !on;
  }
  var hb = document.getElementById("helpbtn");
  if (hb) hb.addEventListener("click", function () { toggleHelp(); });
  var hc = document.getElementById("helpclose");
  if (hc) hc.addEventListener("click", function () { toggleHelp(false); });

  /* ---- keyboard ---- */
  function go(where) { if (where) location.href = "../" + where; }
  document.addEventListener("keydown", function (ev) {
    var t = ev.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
    if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
    var step = Math.round(window.innerHeight * 0.88);
    switch (ev.key) {
      case "j": case "J":
        window.scrollBy({ top: step, behavior: "smooth" }); ev.preventDefault(); break;
      case "k": case "K":
        window.scrollBy({ top: -step, behavior: "smooth" }); ev.preventDefault(); break;
      case "[": go(prev); break;
      case "]": go(next); break;
      case "c": case "C": location.href = "../../chapters.html"; break;
      case "?": toggleHelp(); ev.preventDefault(); break;
      case "Escape": toggleHelp(false); if (resume) resume.hidden = true; break;
    }
  });

  /* ---- back to top ---- */
  var totop = document.querySelector(".totop");
  if (totop) totop.addEventListener("click", function (ev) {
    ev.preventDefault();
    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
  });

  onScroll();
})();
