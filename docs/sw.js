// Service worker de Monitoreo de Prensa.
// Recibe el "push" (sin contenido) del Worker de Cloudflare, vuelve a leer
// notas.json y muestra una notificación por las noticias que todavía no avisó.

var CACHE = "mp-notif";
var ARCHIVO = "vistos";

self.addEventListener("install", function () {
  self.skipWaiting();
});
self.addEventListener("activate", function (e) {
  e.waitUntil(self.clients.claim());
});

// La página, al suscribirse, manda la lista actual para no avisar retroactivamente.
self.addEventListener("message", function (e) {
  if (e.data && e.data.type === "seed") {
    e.waitUntil(
      caches.open(CACHE).then(function (c) {
        return c.put(ARCHIVO, new Response(JSON.stringify(e.data.ids || [])));
      })
    );
  }
});

self.addEventListener("push", function (event) {
  event.waitUntil(
    (async function () {
      var notas = [];
      try {
        var r = await fetch("./data/notas.json", { cache: "no-store" });
        if (r.ok) notas = await r.json();
      } catch (e) {}
      if (!Array.isArray(notas) || !notas.length) return;

      var cache = await caches.open(CACHE);
      var previa = await cache.match(ARCHIVO);
      var ids = notas.map(function (n) { return n.id; });

      if (!previa) {
        // primer push tras suscribirse: fija la base, no avisa
        await cache.put(ARCHIVO, new Response(JSON.stringify(ids)));
        return;
      }

      var vistos = [];
      try { vistos = await previa.json(); } catch (e) {}
      var nuevas = notas.filter(function (n) { return vistos.indexOf(n.id) < 0; });
      await cache.put(ARCHIVO, new Response(JSON.stringify(ids)));
      if (!nuevas.length) return;

      var cuerpo =
        nuevas.length === 1
          ? nuevas[0].titulo
          : nuevas.length + " noticias nuevas · " + nuevas[0].titulo;

      await self.registration.showNotification("Monitoreo de Prensa", {
        body: cuerpo,
        tag: "mp-noticias",
        renotify: true,
        data: { url: "./" },
      });
    })()
  );
});

self.addEventListener("notificationclick", function (event) {
  event.notification.close();
  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then(function (lista) {
        for (var i = 0; i < lista.length; i++) {
          if ("focus" in lista[i]) return lista[i].focus();
        }
        if (self.clients.openWindow) return self.clients.openWindow("./");
      })
  );
});
