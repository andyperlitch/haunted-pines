// Haunted Pines service worker: network-first for pages and pins.json, cache fallback offline.
const CACHE = 'haunted-pines-v1';
const PRECACHE = ['/', '/index.html', '/styles.css', '/map.js', '/pins.json', '/manifest.json', '/icon-192.png'];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // let GA, fonts, Leaflet, tiles go straight to network

  const isPage = req.mode === 'navigate' || (req.headers.get('accept') || '').includes('text/html');
  const isPins = url.pathname.endsWith('/pins.json');
  if (!isPage && !isPins) return;

  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() => caches.match(req, { ignoreSearch: isPins }).then((hit) => hit || (isPage ? caches.match('/index.html').then((h) => h || caches.match('/')) : undefined)))
  );
});
