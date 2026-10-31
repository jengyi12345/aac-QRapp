/* 離線快取。更新 index.html 或 audio/ 之後，請把 VERSION 數字加 1。 */
const VERSION = 'aac-v2';

const SHELL = ['./', 'index.html'];

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(VERSION);
    await cache.addAll(SHELL);
    // 預先下載預設卡片清單（在 index.html 裡）列出的所有音檔，讓離線也能播放
    try {
      const html = await (await fetch('index.html', { cache: 'no-cache' })).text();
      const m = html.match(/<script type="application\/json" id="vocab-data">([\s\S]*?)<\/script>/);
      const vocab = m ? JSON.parse(m[1]) : {};
      const files = [...new Set(Object.values(vocab).map((v) => v && v.file).filter(Boolean))];
      await Promise.all(files.map((f) =>
        cache.add('audio/' + encodeURIComponent(f)).catch(() => console.warn('音檔快取失敗', f))
      ));
    } catch (e) {
      console.warn('預先快取音檔失敗', e);
    }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // 網頁本身：先抓網路（拿到最新內容），沒網路時用快取
  const networkFirst = req.mode === 'navigate' || url.pathname.endsWith('/index.html');
  event.respondWith(networkFirst ? fromNetwork(req) : fromCache(req));
});

async function fromNetwork(req) {
  const cache = await caches.open(VERSION);
  try {
    const res = await fetch(req);
    if (res.ok) cache.put(req, res.clone());
    return res;
  } catch (e) {
    return (await cache.match(req, { ignoreSearch: true })) ||
           (await cache.match('index.html')) ||
           Response.error();
  }
}

// 音檔：先用快取（速度快），同時在背景更新
async function fromCache(req) {
  const cache = await caches.open(VERSION);
  const cached = await cache.match(req, { ignoreSearch: true });
  const update = fetch(req).then((res) => {
    if (res.ok) cache.put(req, res.clone());
    return res;
  }).catch(() => null);
  return cached || (await update) || Response.error();
}
