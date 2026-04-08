import { type ReactNode } from "react";

import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";

type MarketingPageShellProps = {
  eyebrow: string;
  title: string;
  children: ReactNode;
  mainClassName?: string;
  titleAlign?: "left" | "center";
};

const PAGE_SHELL_CLASS = "min-h-screen flex flex-col bg-[hsl(38_35%_92%)]";
const HERO_CLASS = "w-full pt-[var(--navbar-offset)] relative overflow-hidden";
const HERO_BACKGROUND_STYLE = {
  background: "linear-gradient(130deg, hsl(229 73% 28%), hsl(222 68% 17%))",
};
const HERO_OVERLAY_STYLE = {
  backgroundImage:
    "radial-gradient(circle at 15% 25%, hsl(220 80% 58% / 0.35) 0, transparent 42%), radial-gradient(circle at 86% 32%, hsl(240 80% 72% / 0.2) 0, transparent 40%)",
};
const TITLE_STYLE = {
  fontFamily: "'Sora', 'Playfair Display', serif",
  letterSpacing: "0.09em",
};

const MarketingPageShell = ({
  eyebrow,
  title,
  children,
  mainClassName = "flex-1",
  titleAlign = "left",
}: MarketingPageShellProps) => {
  const isCentered = titleAlign === "center";

  return (
    <div className={PAGE_SHELL_CLASS}>
      <Navbar />

      <section className={HERO_CLASS} style={HERO_BACKGROUND_STYLE}>
        <div className="absolute inset-0 opacity-30" style={HERO_OVERLAY_STYLE} />
        <div className={`relative mx-auto px-4 py-11 ${isCentered ? "max-w-4xl text-center" : "max-w-6xl"}`}>
          <p className="text-[11px] uppercase tracking-[0.28em] text-white/75 font-semibold">{eyebrow}</p>
          <h1 className="mt-2 text-3xl md:text-4xl text-white uppercase" style={TITLE_STYLE}>
            {title}
          </h1>
        </div>
      </section>

      <main className={mainClassName}>{children}</main>

      <Footer />
    </div>
  );
};

export default MarketingPageShell;
