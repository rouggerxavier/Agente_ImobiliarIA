import { Bath, BedDouble, MapPin, Maximize } from "lucide-react";
import { Link } from "react-router-dom";

interface PropertyCardProps {
  image: string;
  title: string;
  location: string;
  price: string;
  beds: number;
  baths: number;
  area: number;
  href?: string;
}

const PropertyCard = ({ image, title, location, price, beds, baths, area, href }: PropertyCardProps) => {
  const cardContent = (
    <>
      <div className="relative overflow-hidden aspect-[4/3]">
        <img
          src={image}
          alt={title}
          className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          loading="lazy"
          onError={(event) => {
            event.currentTarget.onerror = null;
            event.currentTarget.src = "/catalogo-fallback.jpg";
          }}
        />
        <span className="absolute left-3 top-3 rounded-full bg-accent px-3 py-1 font-body text-xs font-semibold text-accent-foreground">
          {price}
        </span>
      </div>
      <div className="p-5">
        <h3 className="mb-1 font-display text-lg font-semibold text-card-foreground">{title}</h3>
        <p className="mb-4 flex items-center gap-1 font-body text-sm text-muted-foreground">
          <MapPin className="h-3.5 w-3.5" />
          {location}
        </p>
        <div className="flex items-center gap-4 border-t border-border pt-4 font-body text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <BedDouble className="h-4 w-4" />
            {beds}
          </span>
          <span className="flex items-center gap-1">
            <Bath className="h-4 w-4" />
            {baths}
          </span>
          <span className="flex items-center gap-1">
            <Maximize className="h-4 w-4" />
            {area} m²
          </span>
        </div>
      </div>
    </>
  );

  const cardClassName = "surface-card surface-card-hover group h-full";

  if (href) {
    return (
      <Link
        to={href}
        className={`${cardClassName} block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2`}
      >
        {cardContent}
      </Link>
    );
  }

  return <div className={cardClassName}>{cardContent}</div>;
};

export default PropertyCard;
