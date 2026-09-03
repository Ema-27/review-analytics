export default function AIReportCard({ title, onGenerate, loading, report, actionLabel }) {
  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <div className="section-title" style={{ margin: 0 }}>
          {title}
        </div>
        <button className="btn primary" onClick={onGenerate} disabled={loading}>
          {loading ? "Generazione in corso…" : actionLabel || "Genera con AI"}
        </button>
      </div>

      {!report && !loading && (
        <div className="empty-state">Nessun report generato. Usa il pulsante qui sopra.</div>
      )}
      {loading && <div className="empty-state">Il modello sta elaborando le recensioni…</div>}
      {report && (
        <>
          <div className="ai-report">{report.content}</div>
          <div className="ai-report-meta">
            Generato da {report.ai_provider} ({report.ai_model}) il{" "}
            {new Date(report.generated_at).toLocaleString("it-IT")}
          </div>
        </>
      )}
    </div>
  );
}
