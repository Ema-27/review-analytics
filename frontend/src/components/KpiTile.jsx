export default function KpiTile({ label, value, suffix }) {
  return (
    <div className="card kpi-tile">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">
        {value}
        {suffix ? <span style={{ fontSize: "0.9rem", color: "var(--muted)", fontWeight: 500 }}> {suffix}</span> : null}
      </div>
    </div>
  );
}
