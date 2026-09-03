import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CATEGORICAL_DARK, CATEGORICAL_LIGHT, CHROME } from "../theme/palette";
import { useColorScheme } from "../theme/useColorScheme";
import { useDeferredMount } from "../theme/useDeferredMount";

export function propertyColor(index, scheme = "light") {
  const set = scheme === "dark" ? CATEGORICAL_DARK : CATEGORICAL_LIGHT;
  return set[index % set.length];
}

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
      <div style={{ marginBottom: 4, fontWeight: 600 }}>{d.name}</div>
      <div>Valutazione media: {d.average_rating} / 5</div>
      <div style={{ color: chrome.muted }}>{d.review_count} recensioni</div>
    </div>
  );
}

/** Confronto della valutazione media tra strutture: ogni barra e' etichettata
 * direttamente sull'asse col nome della struttura (identita' mai affidata
 * al solo colore), colore categorico in ordine fisso per struttura. */
export default function ComparisonBarChart({ properties }) {
  const scheme = useColorScheme();
  const chrome = CHROME[scheme];
  const ready = useDeferredMount();

  const data = properties.map((p) => ({
    name: p.name.length > 18 ? p.name.slice(0, 16) + "…" : p.name,
    average_rating: p.average_rating,
    review_count: p.review_count,
  }));

  if (!ready) {
    return <div className="chart-placeholder" style={{ height: 280 }} />;
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 8, right: 12, left: -12, bottom: 24 }}>
        <CartesianGrid stroke={chrome.gridline} vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fill: chrome.muted, fontSize: 11 }}
          axisLine={{ stroke: chrome.baseline }}
          tickLine={false}
          angle={-20}
          textAnchor="end"
          interval={0}
          height={50}
        />
        <YAxis domain={[0, 5]} tick={{ fill: chrome.muted, fontSize: 12 }} axisLine={false} tickLine={false} width={28} />
        <Tooltip content={<CustomTooltip chrome={chrome} />} cursor={{ fill: chrome.gridline }} />
        <Bar dataKey="average_rating" radius={[4, 4, 0, 0]} maxBarSize={48}>
          {data.map((_, i) => (
            <Cell key={i} fill={propertyColor(i, scheme)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
