import { useEffect, useState } from "react";

/**
 * Ritarda il primo render effettivo di un componente di due frame di
 * animazione dopo il mount.
 *
 * Motivazione: Recharts `ResponsiveContainer` misura le dimensioni del
 * proprio contenitore tramite ResizeObserver al momento del mount. Quando il
 * grafico monta immediatamente dopo una navigazione client-side (React
 * Router SPA, nessun reload di pagina) il layout della pagina puo' non
 * essersi ancora stabilizzato: in quel caso il ResizeObserver puo' misurare
 * una larghezza incoerente e, poiche' in seguito le dimensioni "logiche" del
 * contenitore non cambiano piu', nessun nuovo evento di resize arriva a
 * correggere il disegno (barre/linee renderizzate con dimensione nulla).
 *
 * Rimandare il mount del grafico di un paio di frame (dopo che il browser ha
 * gia' completato layout/paint del resto della pagina) e' la mitigazione
 * standard per questa race condition nota di Recharts nelle SPA.
 */
export function useDeferredMount(frames = 2) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let raf1, raf2;
    let remaining = frames;
    const step = () => {
      remaining -= 1;
      if (remaining <= 0) {
        setReady(true);
      } else {
        raf2 = requestAnimationFrame(step);
      }
    };
    raf1 = requestAnimationFrame(step);
    return () => {
      cancelAnimationFrame(raf1);
      cancelAnimationFrame(raf2);
    };
  }, [frames]);

  return ready;
}
