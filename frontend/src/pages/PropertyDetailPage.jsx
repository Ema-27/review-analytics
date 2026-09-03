import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AiAPI, AnalyticsAPI, PropertiesAPI, ReviewsAPI } from "../api/client";
import KpiTile from "../components/KpiTile";
import RatingTrendChart from "../components/RatingTrendChart";
import SentimentBreakdownChart from "../components/SentimentBreakdownChart";
import AspectsChart from "../components/AspectsChart";
import AIReportCard from "../components/AIReportCard";

const TYPE_LABELS = { hotel: "Hotel", restaurant: "Ristorante", attraction: "Attrazione" };

export default function PropertyDetailPage() {
  const { id } = useParams();
  const [property, setProperty] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [summary, setSummary] = useState(null);
  const [suggestions, setSuggestions] = useState(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [aiError, setAiError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoadError(false);
    setSummary(null);
    setSuggestions(null);
    Promise.all([
      PropertiesAPI.get(id).then((d) => !cancelled && setProperty(d)),
      AnalyticsAPI.forProperty(id).then((d) => !cancelled && setAnalytics(d)),
      ReviewsAPI.list(id, 8).then((d) => !cancelled && setReviews(d)),
    ]).catch(() => !cancelled && setLoadError(true));

    // Ripresenta l'ultimo report AI salvato (se c'e'), senza rigenerarlo.
    AiAPI.reports({ property_id: id, report_type: "summary", limit: 1 })
      .then((r) => !cancelled && r[0] && setSummary(r[0]))
      .catch(() => {});
    AiAPI.reports({ property_id: id, report_type: "improvement_suggestions", limit: 1 })
      .then((r) => !cancelled && r[0] && setSuggestions(r[0]))
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loadError) {
    return (
      <main>
        <div className="empty-state card">
          Impossibile caricare i dati della struttura. Verifica che il backend sia raggiungibile.
        </div>
      </main>
    );
  }

  if (!property || !analytics) {
    return (
      <main>
        <div className="empty-state">Caricamento…</div>
      </main>
    );
  }

  const generateSummary = () => {
    setLoadingSummary(true);
    setAiError(null);
    AiAPI.summary(id)
      .then(setSummary)
      .catch(() => setAiError("summary"))
      .finally(() => setLoadingSummary(false));
  };

  const generateSuggestions = () => {
    setLoadingSuggestions(true);
    setAiError(null);
    AiAPI.suggestions(id)
      .then(setSuggestions)
      .catch(() => setAiError("suggestions"))
      .finally(() => setLoadingSuggestions(false));
  };

  return (
    <main>
      <Link to="/" style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
        ← Torna alla dashboard
      </Link>
      <h1 className="page-title" style={{ marginTop: 10 }}>
        {property.name}
      </h1>
      <p className="page-subtitle">
        {TYPE_LABELS[property.type]} · {property.location.city}, {property.location.country}
        {property.category ? ` · ${property.category}` : ""}
      </p>

      <div className="grid grid-kpis">
        <KpiTile label="Recensioni analizzate" value={analytics.review_count} />
        <KpiTile label="Valutazione media" value={analytics.average_rating} suffix="/ 5" />
        <KpiTile label="Aspetti rilevati" value={analytics.top_aspects.length} />
      </div>

      <div className="grid grid-2col" style={{ marginBottom: 16 }}>
        <div className="card">
          <div className="section-title">Andamento delle valutazioni</div>
          <RatingTrendChart data={analytics.rating_trend} />
        </div>
        <div className="card">
          <div className="section-title">Distribuzione del sentiment</div>
          <SentimentBreakdownChart data={analytics.sentiment_breakdown} />
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="section-title">Aspetti piu' apprezzati e criticati</div>
        <AspectsChart data={analytics.top_aspects} />
      </div>

      {aiError && (
        <div className="empty-state card" style={{ marginBottom: 16, color: "var(--warning)" }}>
          Generazione non riuscita. Il modello AI potrebbe essere ancora in avvio: riprova tra
          qualche istante.
        </div>
      )}

      <div className="grid grid-2col" style={{ marginBottom: 16 }}>
        <AIReportCard
          title="Sintesi generata dall'AI"
          onGenerate={generateSummary}
          loading={loadingSummary}
          report={summary}
          actionLabel="Genera sintesi"
        />
        <AIReportCard
          title="Suggerimenti di miglioramento"
          onGenerate={generateSuggestions}
          loading={loadingSuggestions}
          report={suggestions}
          actionLabel="Genera suggerimenti"
        />
      </div>

      <div className="card">
        <div className="section-title">Recensioni recenti</div>
        {reviews.length === 0 && <div className="empty-state">Nessuna recensione disponibile.</div>}
        {reviews.map((r) => (
          <div key={r.id} style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
              <span className="badge">★ {r.rating}</span>
              <span className="tag">{r.language}</span>
              {r.sentiment_label && <span className="tag">{r.sentiment_label}</span>}
              <span style={{ color: "var(--muted)", fontSize: "0.8rem" }}>{r.review_date}</span>
            </div>
            <div style={{ fontSize: "0.9rem" }}>{r.text}</div>
          </div>
        ))}
      </div>
    </main>
  );
}
