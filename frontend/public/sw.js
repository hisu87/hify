const CACHE_NAME = 'hify-v1';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(clients.claim());
});

self.addEventListener('fetch', (event) => {
  // We keep this minimal just to satisfy the PWA requirements
  // We don't want to aggressively cache audio or API calls yet
});
