import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CHROME, DIVERGING } from "../theme/palette";
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
      <div style={{ marginBottom: 4, fontWeight: 600, textTransform: "capitalize" }}>{d.aspect}</div>
      <div>{d.mentions} menzioni totali</div>
      <div style={{ color: "var(--good)" }}>{d.positive} positive</div>
      <div style={{ color: "var(--critical)" }}>{d.negative} negative</div>
    </div>
  );
}

/** Aspetti piu' menzionati (colazione, personale, prezzo, ...) con il
 * relativo sentiment netto: barre divergenti attorno allo zero, colore
 * rosso/blu in base al segno -- individua a colpo d'occhio quali aspetti
 * sono i piu' apprezzati e quali i piu' criticati. */
export default function AspectsChart({ data }) {
  const scheme = useColorScheme();
  const chrome = CHROME[scheme];
  const diverging = DIVERGING[scheme];
  const ready = useDeferredMount();

  const chartData = [...(data || [])].sort((a, b) => b.mentions - a.mentions).slice(0, 8);
  const height = Math.max(220, chartData.length * 38);

  if (chartData.length === 0) {
    return <div className="empty-state">Nessun aspetto rilevato nelle recensioni analizzate.</div>;
  }

  if (!ready) {
    return <div className="chart-placeholder" style={{ height }} />;
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
      >
        <CartesianGrid stroke={chrome.gridline} horizontal={false} />
        <XAxis
          type="number"
          domain={[-1, 1]}
          tick={{ fill: chrome.muted, fontSize: 12 }}
          axisLine={{ stroke: chrome.baseline }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="aspect"
          tick={{ fill: chrome.textPrimary, fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          width={110}
          style={{ textTransform: "capitalize" }}
        />
        <ReferenceLine x={0} stroke={chrome.baseline} />
        <Tooltip content={<CustomTooltip chrome={chrome} />} cursor={{ fill: chrome.gridline }} />
        <Bar dataKey="net_sentiment" radius={4} maxBarSize={20}>
          {chartData.map((d) => (
            <Cell key={d.aspect} fill={d.net_sentiment >= 0 ? diverging.positive : diverging.negative} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
