import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import FeaturedProperties from "@/components/FeaturedProperties";
import About from "@/components/About";
import Testimonials from "@/components/Testimonials";
import CtaSection from "@/components/CtaSection";
import Footer from "@/components/Footer";

const Index = () => {
  return (
    <main className="min-h-screen bg-surface-base">
      <Navbar />
      <Hero />
      <FeaturedProperties />
      <About />
      <Testimonials />
      <CtaSection />
      <Footer />
    </main>
  );
};

export default Index;
