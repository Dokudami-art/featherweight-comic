/* Featherweight reader — progress bar, auto-hiding header, keyboard nav,
   back to top. Everything here is an enhancement: with JS off the chapter
   still reads top to bottom. */
(function () {
  "use strict";
  var tag  = document.currentScript;
  var prev = tag.dataset.prev || "";
  var next = tag.dataset.next || "";

  var bar  = document.getElementById("readerbar");
  var pbar = document.getElementById("pbar");
  var help = document.getElementById("helppanel");

  function maxScroll() {
    return Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
  }

  /* ---- progress bar + auto-hiding header ---- */
  var lastY = window.scrollY, ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      var y = window.scrollY;
      pbar.style.width = Math.min(100, (y / maxScroll()) * 100).toFixed(2) + "%";
      if (y > lastY + 6 && y > 300) bar.classList.add("hidden");
      else if (y < lastY - 6) bar.classList.remove("hidden");
      lastY = y;
      ticking = false;
    });
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });

  /* ---- help panel ---- */
  function toggleHelp(on) {
    if (!help) return;
    help.hidden = on === undefined ? !help.hidden : !on;
  }
  var hb = document.getElementById("helpbtn");
  if (hb) hb.addEventListener("click", function () { toggleHelp(); });
  var hc = document.getElementById("helpclose");
  if (hc) hc.addEventListener("click", function () { toggleHelp(false); });

  /* ---- back to top ---- */
  var totop = document.querySelector(".totop");
  if (totop) totop.addEventListener("click", function (ev) {
    ev.preventDefault();
    /* Instant, deliberately. A chapter is ~40,000px tall: an animated scroll
       that far is either ignored outright by the browser or forces it to
       decode every image on the way past, which locks the page up. */
    window.scrollTo({ top: 0, behavior: "instant" });
  });

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
      case "Escape": toggleHelp(false); break;
    }
  });

  onScroll();
})();
