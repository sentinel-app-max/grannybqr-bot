var CACHE_NAME = 'grannybqr-v2';
var URLS_TO_CACHE = [
  '/',
  '/granny-b-logo.png',
  '/granny-b-logo.svg',
  '/granny-b-tin.png',
  '/granny-b-animated.mp4',
  '/pwa-icon-192.png',
  '/pwa-icon-512.png',
  '/manifest.json'
];

self.addEventListener('install', function(event) {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(URLS_TO_CACHE);
    })
  );
});

self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.filter(function(name) {
          return name !== CACHE_NAME;
        }).map(function(name) {
          return caches.delete(name);
        })
      );
    }).then(function() {
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', function(event) {
  var url = new URL(event.request.url);

  if (url.pathname.startsWith('/api/') ||
      url.pathname === '/chat' ||
      url.pathname === '/lead' ||
      url.pathname === '/tts' ||
      url.pathname === '/stt' ||
      url.pathname === '/recap') {
    event.respondWith(fetch(event.request));
    return;
  }

  event.respondWith(
    caches.match(event.request).then(function(response) {
      return response || fetch(event.request);
    })
  );
});
