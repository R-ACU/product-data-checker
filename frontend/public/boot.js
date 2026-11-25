// Runs before the first paint (a file, not inline: the CSP allows only scripts from
// this origin). Picks the accent from ?firma=<slug> by own-property lookup in a fixed
// list; unknown, empty, differently cased or hostile values end in "neutral". The URL
// value itself is never written anywhere, only the slug from this list.
// Light/dark comes from localStorage ("pdc-mode"), light by default.
"use strict";
(function () {
  var FIRMS = { neutral: 1, gedore: 1, pohl: 1, amalock: 1, metergrid: 1 };
  var wanted = null;
  try {
    wanted = new URLSearchParams(window.location.search).get("firma");
  } catch (e) {
    wanted = null;
  }
  var slug = typeof wanted === "string" && Object.prototype.hasOwnProperty.call(FIRMS, wanted) ? wanted : "neutral";
  var mode = "light";
  try {
    if (window.localStorage.getItem("pdc-mode") === "dark") mode = "dark";
  } catch (e) {
    mode = "light";
  }
  var root = document.documentElement;
  root.setAttribute("data-theme", slug);
  root.setAttribute("data-mode", mode);
  root.style.colorScheme = mode;
})();
