// Hashes de acceso al panel.
//
// Cada hash es  sha256("monitoreo-prensa-zona-oeste|<usuario>|<contraseña>")
// con el usuario en minúsculas. La contraseña nunca se guarda: solo su hash.
// Es una barrera simple para uso interno, no una protección fuerte (el archivo
// de noticias es un JSON estático y quien tenga su URL lo lee igual).
//
// Para regenerar un hash:
//   cd scraper
//   python -m monitoreo.hash_clave <usuario> "<contraseña>"
// y reemplazá el valor que corresponda.

window.CLAVE_HASHES = [
  "0a25abb4a646f737498147853bcec0a3cbd467398fcefee42db971cddd380b03", // subse_presupuesto
  "b1635d574b6caa576bb6db62686ef6eaf08cb69762f20c6b6c89cecc7a59fcc6"  // guido_napolitano
];
