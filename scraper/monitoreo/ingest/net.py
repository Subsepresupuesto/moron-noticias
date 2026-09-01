"""Cliente HTTP para la ingesta (Anexo I, punto 8).

- User-Agent descriptivo que identifica al municipio.
- Tiempo de espera acotado.
- Requests condicionales (If-None-Match / If-Modified-Since) para aligerar.
- Respeto de robots.txt por host (con caché).
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib import robotparser
from urllib.parse import urlsplit

_ROBOTS: dict[str, robotparser.RobotFileParser] = {}


@dataclass
class Respuesta:
    status: int
    texto: str
    etag: str | None = None
    last_modified: str | None = None
    no_modificado: bool = False


class ClienteHTTP:
    """Envuelve un ``httpx.Client``. Cerrar con ``close()`` o usar como context manager."""

    def __init__(self, user_agent: str, timeout: float = 15.0) -> None:
        import httpx

        self.user_agent = user_agent
        self._cli = httpx.Client(
            headers={
                "User-Agent": user_agent,
                "Accept-Language": "es-AR,es;q=0.9",
            },
            timeout=timeout,
            follow_redirects=True,
        )

    # -- ciclo de vida --
    def close(self) -> None:
        self._cli.close()

    def __enter__(self) -> "ClienteHTTP":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    # -- robots.txt --
    def robots_permite(self, url: str) -> bool:
        try:
            p = urlsplit(url)
            base = f"{p.scheme}://{p.netloc}"
            rp = _ROBOTS.get(base)
            if rp is None:
                rp = robotparser.RobotFileParser()
                try:
                    r = self._cli.get(base + "/robots.txt", timeout=8.0)
                    rp.parse(r.text.splitlines() if r.status_code == 200 else [])
                except Exception:
                    rp.parse([])  # sin robots.txt legible -> sin restricciones
                _ROBOTS[base] = rp
            return rp.can_fetch(self.user_agent, url)
        except Exception:
            return True  # ante la duda, permitir (feeds públicos)

    # -- GET --
    def get(self, url: str, *, etag: str | None = None, last_modified: str | None = None) -> Respuesta:
        headers: dict[str, str] = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        r = self._cli.get(url, headers=headers)
        if r.status_code == 304:
            return Respuesta(304, "", etag, last_modified, no_modificado=True)
        r.raise_for_status()
        return Respuesta(
            r.status_code,
            r.text,
            r.headers.get("ETag"),
            r.headers.get("Last-Modified"),
        )
