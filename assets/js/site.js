/* Theme toggle. Storage is a per-viewer convenience: every access is guarded,
   and the page renders correctly when it is unavailable (private window,
   blocked site data). */
(function () {
  "use strict";

  var KEY = "bas-ba-theme";

  function read() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function write(v) {
    try { if (v) { localStorage.setItem(KEY, v); } else { localStorage.removeItem(KEY); } }
    catch (e) { /* non-fatal */ }
  }
  function systemDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  function effective() {
    var s = read();
    if (s === "dark" || s === "light") { return s; }
    return systemDark() ? "dark" : "light";
  }
  function apply(mode) {
    var root = document.documentElement;
    if (mode === "dark" || mode === "light") { root.setAttribute("data-theme", mode); }
    else { root.removeAttribute("data-theme"); }
  }

  function label(btn) {
    var now = effective();
    var next = now === "dark" ? "light" : "dark";
    btn.textContent = now === "dark" ? "Light mode" : "Dark mode";
    btn.setAttribute("aria-label", "Switch to " + next + " mode");
  }

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("theme-toggle");
    if (!btn) { return; }
    btn.hidden = false;
    label(btn);
    btn.addEventListener("click", function () {
      apply(effective() === "dark" ? "light" : "dark");
      write(document.documentElement.getAttribute("data-theme"));
      label(btn);
    });
    if (window.matchMedia) {
      var mq = window.matchMedia("(prefers-color-scheme: dark)");
      var onChange = function () { if (!read()) { label(btn); } };
      if (mq.addEventListener) { mq.addEventListener("change", onChange); }
      else if (mq.addListener) { mq.addListener(onChange); }
    }
  });
})();

/* Shared hover/focus tooltip for the SVG figures. Every hoverable mark is also
   keyboard-focusable and carries its own text label, so the tooltip is an
   enhancement rather than the only way to read the figure. */
window.basTip = function (frameSel, markSel, build) {
  "use strict";
  var frame = document.querySelector(frameSel);
  if (!frame) { return; }
  var tip = frame.querySelector(".tip");
  if (!tip) { return; }
  var marks = Array.prototype.slice.call(frame.querySelectorAll(markSel));

  function show(el, evt) {
    tip.innerHTML = build(el);
    tip.style.opacity = "1";
    var fr = frame.getBoundingClientRect();
    var x, y;
    if (evt && typeof evt.clientX === "number" && evt.type === "mousemove") {
      x = evt.clientX - fr.left + 14;
      y = evt.clientY - fr.top - 10;
    } else {
      var b = el.getBoundingClientRect();
      x = b.left - fr.left + b.width / 2 - tip.offsetWidth / 2;
      y = b.top - fr.top - tip.offsetHeight - 10;
    }
    tip.style.left = Math.min(Math.max(x, 4), Math.max(fr.width - tip.offsetWidth - 4, 4)) + "px";
    tip.style.top = Math.max(y, 4) + "px";
  }
  function hide() { tip.style.opacity = "0"; }

  marks.forEach(function (el) {
    el.addEventListener("mousemove", function (e) { show(el, e); });
    el.addEventListener("mouseleave", hide);
    el.addEventListener("focus", function () { show(el, null); });
    el.addEventListener("blur", hide);
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") { hide(); } });
};
