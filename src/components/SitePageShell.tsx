import { type ReactNode } from "react";

import Navbar from "@/components/Navbar";

type SitePageShellProps = {
  hero: ReactNode;
  children: ReactNode;
  mainClassName?: string;
};

const SITE_PAGE_CLASS = "min-h-screen flex flex-col bg-[hsl(38_35%_92%)]";

const SitePageShell = ({ hero, children, mainClassName = "flex-1" }: SitePageShellProps) => {
  return (
    <div className={SITE_PAGE_CLASS}>
      <Navbar />
      {hero}
      <main className={mainClassName}>{children}</main>
    </div>
  );
};

export default SitePageShell;