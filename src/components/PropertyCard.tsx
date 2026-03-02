import { MapPin, BedDouble, Bath, Maximize } from "lucide-react";

interface PropertyCardProps {
  image: string;
  title: string;
  location: string;
  price: string;
  beds: number;
  baths: number;
  area: number;
}

const PropertyCard = ({ image, title, location, price, beds, baths, area }: PropertyCardProps) => {
  return (
    <div className="group bg-card rounded-lg overflow-hidden shadow-card hover:shadow-card-hover transition-shadow duration-300">
      <div className="relative overflow-hidden aspect-[4/3]">
        <img
          src={image}
          alt={title}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          loading="lazy"
        />
        <span className="absolute top-3 left-3 bg-accent text-accent-foreground font-body text-xs font-semibold px-3 py-1 rounded-full">
          {price}
        </span>
      </div>
      <div className="p-5">
        <h3 className="font-display text-lg font-semibold text-card-foreground mb-1">{title}</h3>
        <p className="flex items-center gap-1 text-muted-foreground text-sm font-body mb-4">
          <MapPin className="h-3.5 w-3.5" /> {location}
        </p>
        <div className="flex items-center gap-4 text-muted-foreground text-sm font-body border-t border-border pt-4">
          <span className="flex items-center gap-1"><BedDouble className="h-4 w-4" /> {beds}</span>
          <span className="flex items-center gap-1"><Bath className="h-4 w-4" /> {baths}</span>
          <span className="flex items-center gap-1"><Maximize className="h-4 w-4" /> {area}m²</span>
        </div>
      </div>
    </div>
  );
};

export default PropertyCard;
