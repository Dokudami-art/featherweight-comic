/* Light/dark toggle. Defaults to the reader's system setting until they
   choose explicitly; the choice is then remembered on their device. */
(function () {
  "use strict";
  var KEY = "fw:theme", root = document.documentElement;

  function systemDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  function stored() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function effective() {
    return stored() || (systemDark() ? "dark" : "light");
  }
  function paint(theme) {
    root.setAttribute("data-theme", theme);
    var next = theme === "dark" ? "light" : "dark";
    [].forEach.call(document.querySelectorAll(".themetoggle"), function (b) {
      b.setAttribute("aria-label", "Switch to " + next + " mode");
      b.setAttribute("title", "Switch to " + next + " mode");
      b.setAttribute("aria-pressed", String(theme === "dark"));
      b.textContent = theme === "dark" ? "\u263C" : "\u263D";   /* sun when dark, moon when light */
    });
  }

  paint(effective());

  document.addEventListener("click", function (ev) {
    var b = ev.target.closest && ev.target.closest(".themetoggle");
    if (!b) return;
    var next = effective() === "dark" ? "light" : "dark";
    try { localStorage.setItem(KEY, next); } catch (e) {}
    paint(next);
  });

  /* follow the system if the reader has never chosen */
  if (window.matchMedia) {
    var mq = window.matchMedia("(prefers-color-scheme: dark)");
    var onChange = function () { if (!stored()) paint(systemDark() ? "dark" : "light"); };
    if (mq.addEventListener) mq.addEventListener("change", onChange);
    else if (mq.addListener) mq.addListener(onChange);
  }
})();
