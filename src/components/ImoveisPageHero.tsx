import type { ReactNode } from "react";

interface ImoveisPageHeroProps {
  eyebrow: string;
  title: string;
  description?: string;
  children?: ReactNode;
}

const ImoveisPageHero = ({ eyebrow, title, description, children }: ImoveisPageHeroProps) => {
  return (
    <section className="relative w-full overflow-hidden bg-[linear-gradient(130deg,hsl(229_73%_28%),hsl(222_68%_17%))]">
      <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_15%_25%,hsl(220_80%_58%_/_0.35)_0,transparent_42%),radial-gradient(circle_at_86%_32%,hsl(240_80%_72%_/_0.2)_0,transparent_40%)]" />
      <div className="relative mx-auto max-w-6xl px-4 py-11">
        <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/75">{eyebrow}</p>
        <h1 className="mt-2 font-display text-3xl text-white md:text-4xl uppercase tracking-[0.09em]">
          {title}
        </h1>
        {description ? (
          <p className="mt-3 max-w-2xl font-body text-sm text-white/85">{description}</p>
        ) : null}
        {children ? <div className="mt-6">{children}</div> : null}
      </div>
    </section>
  );
};

export default ImoveisPageHero;
