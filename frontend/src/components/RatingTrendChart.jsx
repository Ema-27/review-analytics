import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CHROME, CATEGORICAL_LIGHT, CATEGORICAL_DARK } from "../theme/palette";
import { useColorScheme } from "../theme/useColorScheme";
import { useDeferredMount } from "../theme/useDeferredMount";

function CustomTooltip({ active, payload, label, chrome }) {
  if (!active || !payload || !payload.length) return null;
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
      <div style={{ color: chrome.textSecondary, marginBottom: 4 }}>{label}</div>
      <div>
        Valutazione media: <strong>{payload[0].value}</strong> / 5
      </div>
      <div style={{ color: chrome.muted }}>{payload[0].payload.review_count} recensioni</div>
    </div>
  );
}

/** Andamento nel tempo della valutazione media (serie singola -> nessuna
 * legenda necessaria, il titolo del grafico identifica gia' la serie). */
export default function RatingTrendChart({ data }) {
  const scheme = useColorScheme();
  const chrome = CHROME[scheme];
  const seriesColor = (scheme === "dark" ? CATEGORICAL_DARK : CATEGORICAL_LIGHT)[0];
  const ready = useDeferredMount();

  if (!data || data.length === 0) {
    return <div className="empty-state">Nessun dato di trend disponibile.</div>;
  }

  if (!ready) {
    return <div className="chart-placeholder" style={{ height: 260 }} />;
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
        <CartesianGrid stroke={chrome.gridline} vertical={false} />
        <XAxis
          dataKey="period"
          tick={{ fill: chrome.muted, fontSize: 12 }}
          axisLine={{ stroke: chrome.baseline }}
          tickLine={false}
        />
        <YAxis
          domain={[1, 5]}
          tick={{ fill: chrome.muted, fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          width={28}
        />
        <Tooltip content={<CustomTooltip chrome={chrome} />} cursor={{ stroke: chrome.baseline }} />
        <Line
          type="monotone"
          dataKey="average_rating"
          stroke={seriesColor}
          strokeWidth={2}
          dot={{ r: 3, fill: seriesColor, strokeWidth: 0 }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
