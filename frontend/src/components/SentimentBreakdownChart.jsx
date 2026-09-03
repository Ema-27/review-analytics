import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CHROME, SENTIMENT_LABELS_IT, SENTIMENT_ORDER, sentimentColor } from "../theme/palette";
import { useColorScheme } from "../theme/useColorScheme";
import { useDeferredMount } from "../theme/useDeferredMount";

function CustomTooltip({ active, payload, chrome }) {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0].payload;
  return (
    <div
      style={{
        background: chrome.surface,
        border: `1px solid ${chrome.gridline}`,
        borderRadius: 8,
        padding: "8px 12px",
        fontSize: 13,
        color: chrome.textPrimary,
      }}
    >
      <div style={{ marginBottom: 4, fontWeight: 600 }}>{d.labelIt}</div>
      <div>
        {d.count} recensioni ({d.percentage}%)
      </div>
    </div>
  );
}

/** Distribuzione del sentiment (scala ordinale di polarita': molto negativo
 * -> molto positivo). Ogni barra rappresenta una categoria distinta gia'
 * etichettata sull'asse: il colore segue la polarita' (divergente
 * rosso/grigio/blu), niente legenda necessaria per una serie singola. */
export default function SentimentBreakdownChart({ data }) {
  const scheme = useColorScheme();
  const chrome = CHROME[scheme];
  const ready = useDeferredMount();

  const byLabel = Object.fromEntries((data || []).map((d) => [d.label, d]));
  const chartData = SENTIMENT_ORDER.map((label) => ({
    label,
    labelIt: SENTIMENT_LABELS_IT[label],
    count: byLabel[label]?.count ?? 0,
    percentage: byLabel[label]?.percentage ?? 0,
  }));

  const hasData = chartData.some((d) => d.count > 0);
  if (!hasData) {
    return <div className="empty-state">Nessuna recensione ancora analizzata.</div>;
  }

  if (!ready) {
    return <div className="chart-placeholder" style={{ height: 260 }} />;
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={chartData} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
        <CartesianGrid stroke={chrome.gridline} vertical={false} />
        <XAxis
          dataKey="labelIt"
          tick={{ fill: chrome.muted, fontSize: 11 }}
          axisLine={{ stroke: chrome.baseline }}
          tickLine={false}
          interval={0}
        />
        <YAxis tick={{ fill: chrome.muted, fontSize: 12 }} axisLine={false} tickLine={false} width={28} />
        <Tooltip content={<CustomTooltip chrome={chrome} />} cursor={{ fill: chrome.gridline }} />
        <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={56}>
          {chartData.map((d) => (
            <Cell key={d.label} fill={sentimentColor(d.label, scheme)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
