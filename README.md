# Monitoreo de Prensa Zona Oeste — versión GitHub Pages

Página interna de la Secretaría: muestra las noticias de los medios de la zona
oeste (y de algunos nacionales) que mencionan al **Municipio de Morón** y que
además tocan a los funcionarios o ejes temáticos que se siguen de cerca.

- **No hay servidor ni base de datos.** GitHub Actions corre el scraper cada ~30 min
  y deja el resultado en `docs/data/notas.json`.
- **GitHub Pages** publica la carpeta `docs/` como sitio web.
- El acceso tiene una **clave compartida** (barrera simple para uso interno, no
  seguridad fuerte: el `notas.json` es un archivo público).

## Estructura

```
.github/workflows/actualizar.yml   cron: corre el scraper y publica docs/data/
scraper/                           código Python del scraper
  config/monitoreo.yaml            medios y términos (Nivel A / Nivel B)
  monitoreo/                       filtrado, lectores de medios, build.py
  tests/
docs/                              lo que publica GitHub Pages
  index.html                       el panel (lee ./data/notas.json)
  clave.js                         hash de la clave de acceso
  data/notas.json                  noticias (lo regenera el workflow)
  data/estado.json                 estado de cada fuente
```

## Publicar (una sola vez)

1. Crear un repositorio en GitHub y subir el contenido de esta carpeta a la raíz.
2. En **Settings → Pages**: *Source* = **Deploy from a branch**, rama `main`,
   carpeta **`/docs`**. Guardar. A los minutos queda la URL
   `https://<usuario>.github.io/<repo>/`.
3. En **Settings → Actions → General**: en *Workflow permissions*, dejar
   **Read and write permissions** (para que el bot pueda publicar el `notas.json`).
4. En la pestaña **Actions**, abrir "Actualizar noticias" y correrlo una vez a
   mano (*Run workflow*) para tener noticias desde el arranque. Después se ejecuta
   solo cada ~30 minutos (GitHub puede demorarlo bajo carga).

## Cambiar la clave de acceso

```bash
cd scraper
python -m monitoreo.hash_clave "la-nueva-clave"
```

Pegar el valor que imprime en `docs/clave.js` y subir el cambio. Todos los
dispositivos vuelven a pedir la clave una vez.

## Cambiar los medios o los términos

Editar `scraper/config/monitoreo.yaml` y subir el cambio. La próxima corrida del
workflow ya usa la lista nueva.

## Probar localmente

```bash
cd scraper
pip install -r requirements.txt
python -m monitoreo.build          # genera ../docs/data/*.json
pytest -q                          # pruebas

cd ../docs
python -m http.server 8000         # abrir http://localhost:8000
```

> Nota: la validación de la clave usa Web Crypto, que solo funciona por
> `https://` o `http://localhost` (no abriendo el `index.html` como archivo).
