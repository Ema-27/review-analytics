import { useEffect, useState } from "react";
import { AiAPI, AnalyticsAPI, PropertiesAPI } from "../api/client";
import ComparisonBarChart, { propertyColor } from "../components/ComparisonBarChart";
import AIReportCard from "../components/AIReportCard";
import { useColorScheme } from "../theme/useColorScheme";

export default function ComparisonPage() {
  const [properties, setProperties] = useState([]);
  const [selected, setSelected] = useState([]);
  const [comparisonStats, setComparisonStats] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const scheme = useColorScheme();

  useEffect(() => {
    PropertiesAPI.list()
      .then(setProperties)
      .catch(() => setError("Impossibile caricare l'elenco delle strutture."));
  }, []);

  const toggle = (id) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : prev.length < 6 ? [...prev, id] : prev
    );
  };

  const sameSet = (a, b) =>
    a && b && a.length === b.length && [...a].sort().join() === [...b].sort().join();

  const loadStats = async () => {
    const statsList = await Promise.all(selected.map((id) => AnalyticsAPI.forProperty(id)));
    setComparisonStats(
      statsList.map((s) => ({
        id: s.property_id,
        name: s.property_name,
        average_rating: s.average_rating,
        review_count: s.review_count,
      }))
    );
  };

  // Se esiste gia' un confronto salvato per esattamente le strutture selezionate,
  // lo ripresenta senza rigenerarlo.
  useEffect(() => {
    setReport(null);
    setComparisonStats(null);
    if (selected.length < 2) return;
    let cancelled = false;
    AiAPI.reports({ report_type: "competitive_comparison", limit: 25 })
      .then(async (reports) => {
        const match = reports.find((r) => sameSet(r.property_ids, selected));
        if (match && !cancelled) {
          setReport(match);
          await loadStats();
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  const runComparison = async () => {
    setLoading(true);
    setReport(null);
    setError(null);
    try {
      await loadStats();
      const comparisonReport = await AiAPI.comparison(selected);
      setReport(comparisonReport);
    } catch {
      setError(
        "Confronto non riuscito. Il modello AI potrebbe essere ancora in avvio: riprova tra qualche istante."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <main>
      <h1 className="page-title">Confronto tra strutture</h1>
      <p className="page-subtitle">
        Seleziona da 2 a 6 strutture simili per confrontarne reputazione, valutazioni e fattori
        distintivi tramite analisi comparativa generata dall'AI.
      </p>

      <div className="checkbox-list">
        {properties.map((p, i) => (
          <label key={p.id}>
            <input type="checkbox" checked={selected.includes(p.id)} onChange={() => toggle(p.id)} />
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: selected.includes(p.id) ? propertyColor(selected.indexOf(p.id), scheme) : "var(--border)",
                display: "inline-block",
              }}
            />
            {p.name} <span style={{ color: "var(--muted)" }}>({p.city})</span>
          </label>
        ))}
      </div>

      <div className="btn-row">
        <button className="btn primary" disabled={selected.length < 2 || loading} onClick={runComparison}>
          {loading ? "Analisi in corso…" : `Confronta ${selected.length} strutture`}
        </button>
      </div>

      {error && (
        <div className="empty-state card" style={{ marginBottom: 16, color: "var(--warning)" }}>
          {error}
        </div>
      )}

      {comparisonStats && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="section-title">Valutazione media a confronto</div>
          <ComparisonBarChart properties={comparisonStats} />
        </div>
      )}

      {(report || loading) && (
        <AIReportCard
          title="Analisi competitiva generata dall'AI"
          onGenerate={runComparison}
          loading={loading}
          report={report}
          actionLabel="Rigenera confronto"
        />
      )}
    </main>
  );
}
