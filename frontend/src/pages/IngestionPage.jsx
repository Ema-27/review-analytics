import { useState } from "react";
import { IngestionAPI } from "../api/client";

const EMPTY_FORM = {
  property_name: "",
  property_type: "hotel",
  city: "",
  country: "Italia",
  tripadvisor_url: "",
  max_reviews: 100,
};

export default function IngestionPage() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [result, setResult] = useState(null);
  const [seedResult, setSeedResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState(null);

  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const submit = (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    setError(null);
    const payload = { ...form, tripadvisor_url: form.tripadvisor_url || undefined };
    IngestionAPI.run(payload)
      .then(setResult)
      .catch(() =>
        setError(
          "Acquisizione non riuscita. Con molte recensioni l'operazione può richiedere diversi minuti: verifica i log del backend e riprova."
        )
      )
      .finally(() => setLoading(false));
  };

  const seedDemo = () => {
    setSeeding(true);
    setSeedResult(null);
    setError(null);
    IngestionAPI.seedDemoData()
      .then(setSeedResult)
      .catch(() => setError("Popolamento dei dati di esempio non riuscito. Riprova."))
      .finally(() => setSeeding(false));
  };

  return (
    <main>
      <h1 className="page-title">Acquisizione dati</h1>
      <p className="page-subtitle">
        Acquisisci recensioni da Tripadvisor tramite Apify, oppure popola rapidamente il sistema con
        il dataset dimostrativo incluso (usato automaticamente anche come fallback se Apify non e'
        configurato o non risponde).
      </p>

      {error && (
        <div className="empty-state card" style={{ marginBottom: 16, color: "var(--warning)" }}>
          {error}
        </div>
      )}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="section-title">Dataset dimostrativo</div>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", marginTop: 0 }}>
          Popola il database con 12 strutture (hotel, ristoranti, attrazioni) in 4 citta' europee e
          centinaia di recensioni multilingua sintetiche, pronte per essere analizzate.
        </p>
        <button className="btn primary" onClick={seedDemo} disabled={seeding}>
          {seeding ? "Popolamento in corso…" : "Popola dati demo"}
        </button>
        {seedResult && (
          <div className="ai-report-meta" style={{ marginTop: 10 }}>
            {seedResult.properties} strutture, {seedResult.reviews} recensioni caricate.
          </div>
        )}
      </div>

      <div className="card">
        <div className="section-title">Nuova acquisizione mirata</div>
        <form onSubmit={submit} className="form-grid">
          <label>
            Nome struttura
            <input value={form.property_name} onChange={update("property_name")} required />
          </label>
          <label>
            Tipo
            <select value={form.property_type} onChange={update("property_type")}>
              <option value="hotel">Hotel</option>
              <option value="restaurant">Ristorante</option>
              <option value="attraction">Attrazione</option>
            </select>
          </label>
          <label>
            Citta'
            <input value={form.city} onChange={update("city")} required />
          </label>
          <label>
            Paese
            <input value={form.country} onChange={update("country")} required />
          </label>
          <label style={{ gridColumn: "1 / -1" }}>
            URL Tripadvisor (opzionale)
            <input
              value={form.tripadvisor_url}
              onChange={update("tripadvisor_url")}
              placeholder="https://www.tripadvisor.it/Hotel_Review-..."
            />
          </label>
          <label>
            Numero massimo recensioni
            <input type="number" min={1} max={500} value={form.max_reviews} onChange={update("max_reviews")} />
          </label>
          <div style={{ alignSelf: "end" }}>
            <button className="btn primary" type="submit" disabled={loading}>
              {loading ? "Acquisizione in corso…" : "Avvia acquisizione"}
            </button>
          </div>
        </form>

        {result && (
          <div className="ai-report-meta" style={{ marginTop: 14 }}>
            Stato: {result.status} · Fonte: {result.source} · Recensioni acquisite:{" "}
            {result.records_ingested}
            {result.error_message && (
              <div style={{ color: "var(--warning)", marginTop: 4 }}>{result.error_message}</div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
