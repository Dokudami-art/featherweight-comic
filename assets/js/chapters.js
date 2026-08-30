/* Chapter sort order. Progressive enhancement: with JS off the grid still
   renders newest-first, which is the default state of the control. */
(function () {
  "use strict";
  var KEY = "fw:chaptersort";
  var grid = document.querySelector(".chapgrid");
  if (!grid) return;
  var btns  = Array.prototype.slice.call(document.querySelectorAll(".sortbtn"));
  var cards = Array.prototype.slice.call(grid.children);

  function apply(mode) {
    cards.forEach(function (c) {
      var n = parseInt(c.getAttribute("data-num"), 10) || 0;
      c.style.order = (mode === "oldest") ? n : -n;
    });
    btns.forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-sort") === mode));
    });
    try { localStorage.setItem(KEY, mode); } catch (e) {}
  }

  var saved = "newest";
  try { saved = localStorage.getItem(KEY) || "newest"; } catch (e) {}
  apply(saved === "oldest" ? "oldest" : "newest");

  btns.forEach(function (b) {
    b.addEventListener("click", function () { apply(b.getAttribute("data-sort")); });
  });
})();
