import { NavLink } from "react-router-dom";

export default function Navbar() {
  return (
    <header className="navbar">
      <div className="brand">TourInsight</div>
      <nav>
        <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
          Dashboard
        </NavLink>
        <NavLink to="/confronto" className={({ isActive }) => (isActive ? "active" : "")}>
          Confronto strutture
        </NavLink>
        <NavLink to="/acquisizione" className={({ isActive }) => (isActive ? "active" : "")}>
          Acquisizione dati
        </NavLink>
      </nav>
    </header>
  );
}
