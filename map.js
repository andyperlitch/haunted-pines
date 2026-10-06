// Candy map: pins come from pins.json (address + coordinates only),
// rebuilt automatically from the sign-up form.
(function () {
  var el = document.getElementById("map");
  var countEl = document.getElementById("map-count");
  if (!el || !window.L) {
    if (countEl) countEl.textContent = "The map couldn't load. Just follow the red balloons!";
    return;
  }

  var CENTER = [37.0400, -122.0385];
  var map = L.map(el, { scrollWheelZoom: false, tap: true }).setView(CENTER, 16);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);

  // Re-enable scroll zoom once someone clicks into the map.
  map.on("focus click", function () { map.scrollWheelZoom.enable(); });
  map.on("blur", function () { map.scrollWheelZoom.disable(); });

  var balloonSvg =
    '<svg viewBox="0 0 32 48" width="30" height="45" aria-hidden="true">' +
      '<path d="M16 34 C15 38 18 40 16 44 C14 47 17 48 16 48" stroke="#fbf1dc" stroke-width="1.4" fill="none"/>' +
      '<path d="M16 2 C8 2 3 8.5 3 15.5 C3 24 10 31 16 33 C22 31 29 24 29 15.5 C29 8.5 24 2 16 2 Z" fill="#d4161c" stroke="#5a0a0d" stroke-width="1.2"/>' +
      '<path d="M13.5 33 L18.5 33 L16 36 Z" fill="#a51015"/>' +
      '<ellipse cx="11" cy="10.5" rx="3.2" ry="5" fill="#fff" opacity=".35" transform="rotate(-20 11 10.5)"/>' +
    '</svg>';
  var icon = L.divIcon({
    className: "balloon-pin",
    html: balloonSvg,
    iconSize: [30, 45],
    iconAnchor: [15, 45]
  });

  fetch("pins.json?v=" + Math.floor(Date.now() / 600000), { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (data) {
      var pins = (data && data.pins) || [];
      if (!pins.length) {
        countEl.textContent = "No houses on the map yet. Check back soon!";
        return;
      }
      var markers = pins.map(function (p) {
        // Pins are decorative only: no popups, hover titles, clicks, or keyboard focus.
        return L.marker([p.lat, p.lng], { icon: icon, alt: p.address, interactive: false, keyboard: false });
      });
      var group = L.featureGroup(markers).addTo(map);
      map.fitBounds(group.getBounds(), { paddingTopLeft: [30, 55], paddingBottomRight: [30, 15], maxZoom: 17 });
      countEl.innerHTML = "<strong>" + pins.length + "</strong> " +
        (pins.length === 1 ? "house" : "houses") + " and counting 🎈";
    })
    .catch(function () {
      countEl.textContent = "Couldn't load the houses right now. Just follow the red balloons!";
    });
})();
