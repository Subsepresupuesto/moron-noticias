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
  // Con userVisibleOnly:true el navegador EXIGE que cada push muestre una
  // notificación. Si no, penaliza y termina dando de baja la suscripción.
  // Por eso este handler SIEMPRE llama a showNotification, aunque no logre
  // leer notas.json o no encuentre el detalle de la novedad.
  event.waitUntil(
    (async function () {
      var titulo = "Portal de Noticias Morón";
      var cuerpo = "Hay novedades. Abrí el panel para verlas.";

      try {
        var r = await fetch("./data/notas.json", { cache: "no-store" });
        if (r.ok) {
          var notas = await r.json();
          if (Array.isArray(notas) && notas.length) {
            var ids = notas.map(function (n) { return n.id; });
            var cache = await caches.open(CACHE);
            var previa = await cache.match(ARCHIVO);
            var vistos = null;
            if (previa) {
              try { vistos = await previa.json(); } catch (e) {}
            }
            await cache.put(ARCHIVO, new Response(JSON.stringify(ids)));

            if (vistos && vistos.length) {
              var nuevas = notas.filter(function (n) { return vistos.indexOf(n.id) < 0; });
              if (nuevas.length === 1) {
                cuerpo = nuevas[0].titulo;
              } else if (nuevas.length > 1) {
                cuerpo = nuevas.length + " noticias nuevas · " + nuevas[0].titulo;
              }
              // si nuevas.length === 0 igual avisamos (mensaje genérico)
            } else {
              // sin base previa: mostramos la más reciente
              cuerpo = notas[0].titulo;
            }
          }
        }
      } catch (e) {}

      await self.registration.showNotification(titulo, {
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
