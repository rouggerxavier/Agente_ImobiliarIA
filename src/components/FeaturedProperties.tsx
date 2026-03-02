import PropertyCard from "./PropertyCard";
import property1 from "@/assets/property-1.jpg";
import property2 from "@/assets/property-2.jpg";
import property3 from "@/assets/property-3.jpg";

const properties = [
  {
    image: property1,
    title: "Apartamento Vista Mar",
    location: "Leblon, Rio de Janeiro",
    price: "R$ 1.850.000",
    beds: 3,
    baths: 2,
    area: 142,
  },
  {
    image: property2,
    title: "Cobertura Duplex",
    location: "Vila Madalena, São Paulo",
    price: "R$ 2.400.000",
    beds: 4,
    baths: 3,
    area: 210,
  },
  {
    image: property3,
    title: "Penthouse Premium",
    location: "Asa Sul, Brasília",
    price: "R$ 3.200.000",
    beds: 5,
    baths: 4,
    area: 320,
  },
];

const FeaturedProperties = () => {
  return (
    <section id="imoveis" className="py-20 bg-secondary">
      <div className="container mx-auto px-4">
        <div className="text-center mb-14">
          <p className="font-body text-accent text-sm font-semibold uppercase tracking-wider mb-2">Destaques</p>
          <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
            Imóveis em destaque
          </h2>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {properties.map((p) => (
            <PropertyCard key={p.title} {...p} />
          ))}
        </div>
      </div>
    </section>
  );
};

export default FeaturedProperties;
