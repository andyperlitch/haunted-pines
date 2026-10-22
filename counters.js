// House-count ribbon (from pins.json) and retro visitor counter (abacus.jasoncameron.dev).
(function () {
  var ribbon = document.getElementById("house-ribbon");
  fetch("pins.json?v=" + Math.floor(Date.now() / 600000), { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (d) {
      var n = d && (d.count != null ? d.count : (d.pins || []).length);
      if (!n) return;
      document.getElementById("house-count").textContent = n;
      ribbon.hidden = false;
      document.body.classList.add("has-ribbon");
    })
    .catch(function () {});

  var box = document.getElementById("visitor-counter");
  var base = "https://abacus.jasoncameron.dev/";
  var counted = false;
  try { counted = sessionStorage.getItem("hp-visit-counted") === "1"; } catch (e) {}
  fetch(base + (counted ? "get" : "hit") + "/hauntedpines/visits")
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (d) {
      var v = d && d.value;
      if (typeof v !== "number") return;
      try { sessionStorage.setItem("hp-visit-counted", "1"); } catch (e) {}
      var s = String(v).padStart(6, "0");
      document.getElementById("visitor-digits").innerHTML = s.split("").map(function (c) { return "<span>" + c + "</span>"; }).join("");
      document.getElementById("visitor-digits").setAttribute("aria-label", "Visitor number " + v);
      box.hidden = false;
    })
    .catch(function () {});
})();
