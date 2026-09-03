import { Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import DashboardPage from "./pages/DashboardPage";
import PropertyDetailPage from "./pages/PropertyDetailPage";
import ComparisonPage from "./pages/ComparisonPage";
import IngestionPage from "./pages/IngestionPage";

export default function App() {
  return (
    <div className="app-shell">
      <Navbar />
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/strutture/:id" element={<PropertyDetailPage />} />
        <Route path="/confronto" element={<ComparisonPage />} />
        <Route path="/acquisizione" element={<IngestionPage />} />
      </Routes>
      <footer className="app-footer">
        TourInsight - analisi di recensioni turistiche
      </footer>
    </div>
  );
}
