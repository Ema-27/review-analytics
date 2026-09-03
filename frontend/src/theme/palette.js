// Palette dati validata (vedi skill "dataviz"): otto tinte categoriche in
// ordine fisso safe-per-daltonismo, una scala sequenziale blu e una coppia
// divergente blu<->rosso con midpoint grigio neutro. Le tinte "dark" sono lo
// stesso schema ri-calibrato per la superficie scura, non una palette diversa.
export const CATEGORICAL_LIGHT = [
  "#2a78d6", // 1 blue
  "#eb6834", // 2 orange
  "#1baf7a", // 3 aqua
  "#eda100", // 4 yellow
  "#e87ba4", // 5 magenta
  "#008300", // 6 green
  "#4a3aa7", // 7 violet
  "#e34948", // 8 red
];

export const CATEGORICAL_DARK = [
  "#3987e5",
  "#d95926",
  "#199e70",
  "#c98500",
  "#d55181",
  "#008300",
  "#9085e9",
  "#e66767",
];

export const DIVERGING = {
  light: { negative: "#e34948", neutral: "#f0efec", positive: "#2a78d6" },
  dark: { negative: "#e66767", neutral: "#383835", positive: "#3987e5" },
};

export const SEQUENTIAL_BLUE = {
  light: ["#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#184f95"],
  dark: ["#cde2fb", "#6da7ec", "#3987e5", "#1c5cab", "#0d366b"],
};

export const STATUS = {
  good: "#0ca30c",
  warning: "#fab219",
  serious: "#ec835a",
  critical: "#d03b3b",
};

export const CHROME = {
  light: {
    surface: "#fcfcfb",
    page: "#f9f9f7",
    textPrimary: "#0b0b0b",
    textSecondary: "#52514e",
    muted: "#898781",
    gridline: "#e1e0d9",
    baseline: "#c3c2b7",
  },
  dark: {
    surface: "#1a1a19",
    page: "#0d0d0d",
    textPrimary: "#ffffff",
    textSecondary: "#c3c2b7",
    muted: "#898781",
    gridline: "#2c2c2a",
    baseline: "#383835",
  },
};

// Mappa fissa: ogni etichetta di sentiment ha SEMPRE lo stesso colore,
// indipendentemente da quali altre categorie sono presenti nel grafico
// (l'identita' segue l'entita', mai il suo rango).
export function sentimentColor(label, scheme = "light") {
  const d = DIVERGING[scheme];
  switch (label) {
    case "very_negative":
      return scheme === "light" ? "#b73433" : "#e34948";
    case "negative":
      return d.negative;
    case "neutral":
      return d.neutral;
    case "positive":
      return d.positive;
    case "very_positive":
      return scheme === "light" ? "#184f95" : "#1c5cab";
    default:
      return d.neutral;
  }
}

export const SENTIMENT_ORDER = ["very_negative", "negative", "neutral", "positive", "very_positive"];
export const SENTIMENT_LABELS_IT = {
  very_negative: "Molto negativo",
  negative: "Negativo",
  neutral: "Neutro",
  positive: "Positivo",
  very_positive: "Molto positivo",
};
