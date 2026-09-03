import { Link } from "react-router-dom";

const TYPE_LABELS = { hotel: "Hotel", restaurant: "Ristorante", attraction: "Attrazione" };

export default function PropertyCard({ property }) {
  return (
    <Link to={`/strutture/${property.id}`} className="property-card">
      <div className="prop-type">{TYPE_LABELS[property.type] || property.type}</div>
      <div className="prop-name">{property.name}</div>
      <div className="prop-city">
        {property.city}, {property.country}
      </div>
      <div className="prop-stats">
        <span className="badge">★ {property.average_rating ?? "n/d"}</span>
        <span className="badge">{property.review_count} recensioni</span>
      </div>
    </Link>
  );
}
