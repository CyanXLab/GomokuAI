/**
 * Welcome to your Workbox-powered service worker!
 *
 * You'll need to register this file in your web app and you should
 * disable HTTP caching for this file too.
 * See https://goo.gl/nhQhGp
 *
 * The rest of the code is auto-generated. Please don't update this file
 * directly; instead, make changes to your Workbox build configuration
 * and re-run your build process.
 * See https://goo.gl/2aRDsh
 */

importScripts("/workbox-v4.3.1/workbox-sw.js");
workbox.setConfig({modulePathPrefix: "/workbox-v4.3.1"});

importScripts(
  "/precache-manifest.fd27df2b3bf0021ae4759013aedcbe0e.js"
);

workbox.core.setCacheNameDetails({prefix: "gomoku-ai"});

workbox.core.skipWaiting();

/**
 * The workboxSW.precacheAndRoute() method efficiently caches and responds to
 * requests for URLs in the manifest.
 * See https://goo.gl/S9QRab
 */
self.__precacheManifest = [].concat(self.__precacheManifest || []);
workbox.precaching.precacheAndRoute(self.__precacheManifest, {});

workbox.precaching.cleanupOutdatedCaches();

workbox.routing.registerRoute(/^(?!.*\.html$).*$/, new workbox.strategies.CacheFirst({ "cacheName":"all-resources-cache", plugins: [new workbox.expiration.Plugin({ maxEntries: 500, maxAgeSeconds: 1296000, purgeOnQuotaError: true }), new workbox.cacheableResponse.Plugin({ statuses: [ 0, 200 ] })] }), 'GET');
workbox.routing.registerRoute(/\.html$/, new workbox.strategies.StaleWhileRevalidate({ "cacheName":"html-cache", plugins: [new workbox.cacheableResponse.Plugin({ statuses: [ 0, 200 ] })] }), 'GET');

workbox.googleAnalytics.initialize({});
