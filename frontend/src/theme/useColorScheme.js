import { useEffect, useState } from "react";

/** Rileva lo schema colore preferito dal sistema operativo dell'utente
 * (chiaro/scuro) e si aggiorna reattivamente se cambia durante l'uso. */
export function useColorScheme() {
  const [scheme, setScheme] = useState(
    window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
  );

  useEffect(() => {
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e) => setScheme(e.matches ? "dark" : "light");
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  return scheme;
}
