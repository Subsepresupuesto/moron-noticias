"""Genera el hash de un acceso (usuario + contraseña) para ``docs/clave.js``.

Uso:
    cd sitio/scraper
    python -m monitoreo.hash_clave <usuario> "<contraseña>"

El hash es  sha256("monitoreo-prensa-zona-oeste|<usuario>|<contraseña>")  con el
usuario en minúsculas. La contraseña nunca se guarda; en el sitio solo queda su
hash. Es una barrera simple para uso interno, no una protección fuerte: el
archivo de noticias es un JSON estático y quien tenga su URL puede leerlo igual.
"""

from __future__ import annotations

import hashlib
import sys

_SALT = "monitoreo-prensa-zona-oeste"


def hash_de(usuario: str, clave: str) -> str:
    usuario = usuario.strip().lower()
    return hashlib.sha256(f"{_SALT}|{usuario}|{clave}".encode("utf-8")).hexdigest()


def main() -> int:
    if len(sys.argv) != 3 or not sys.argv[1] or not sys.argv[2]:
        print('Uso: python -m monitoreo.hash_clave <usuario> "<contraseña>"', file=sys.stderr)
        return 2
    usuario = sys.argv[1].strip().lower()
    h = hash_de(usuario, sys.argv[2])
    print()
    print("Pegá / reemplazá esta línea en la lista window.CLAVE_HASHES de docs/clave.js:")
    print()
    print(f'  "{h}", // {usuario}')
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
