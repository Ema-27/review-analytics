import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PropertiesAPI } from "../api/client";
import KpiTile from "../components/KpiTile";
import PropertyCard from "../components/PropertyCard";

const TYPES = [
  { value: "", label: "Tutti i tipi" },
  { value: "hotel", label: "Hotel" },
  { value: "restaurant", label: "Ristoranti" },
  { value: "attraction", label: "Attrazioni" },
];

export default function DashboardPage() {
  const [properties, setProperties] = useState(null);
  const [type, setType] = useState("");
  const [city, setCity] = useState("");
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    PropertiesAPI.list({ type: type || undefined, city: city || undefined })
      .then((data) => !cancelled && setProperties(data))
      .catch((e) => !cancelled && setError(e));
    return () => {
      cancelled = true;
    };
  }, [type, city]);

  const kpis = useMemo(() => {
    if (!properties) return null;
    const totalReviews = properties.reduce((s, p) => s + p.review_count, 0);
    const rated = properties.filter((p) => p.average_rating != null);
    const avgRating = rated.length
      ? (rated.reduce((s, p) => s + p.average_rating, 0) / rated.length).toFixed(2)
      : "n/d";
    return { totalProperties: properties.length, totalReviews, avgRating };
  }, [properties]);

  return (
    <main>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-subtitle">
        Monitoraggio della soddisfazione degli utenti su strutture e servizi turistici.
      </p>

      {kpis && (
        <div className="grid grid-kpis">
          <KpiTile label="Strutture censite" value={kpis.totalProperties} />
          <KpiTile label="Recensioni totali" value={kpis.totalReviews} />
          <KpiTile label="Valutazione media" value={kpis.avgRating} suffix="/ 5" />
        </div>
      )}

      <div className="filter-bar">
        <select value={type} onChange={(e) => setType(e.target.value)}>
          {TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Filtra per citta'…"
          value={city}
          onChange={(e) => setCity(e.target.value)}
        />
      </div>

      {error && <div className="empty-state">Errore nel caricamento dei dati dal backend.</div>}

      {properties && properties.length === 0 && (
        <div className="empty-state card">
          Nessuna struttura presente nel database.
          <br />
          Vai alla pagina{" "}
          <Link to="/acquisizione">Acquisizione dati</Link> per popolare il sistema con il dataset
          dimostrativo o avviare una nuova acquisizione.
        </div>
      )}

      {properties && properties.length > 0 && (
        <div className="property-list">
          {properties.map((p) => (
            <PropertyCard key={p.id} property={p} />
          ))}
        </div>
      )}
    </main>
  );
}
