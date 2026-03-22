const SITE_NAME = "GranKasa Imóveis";
const HOME_TAGLINE = "Encontre o Imóvel dos Seus Sonhos";

export const DEFAULT_PAGE_TITLE = `${SITE_NAME} - ${HOME_TAGLINE}`;

function decodePathSegment(value: string | undefined): string {
  if (!value) return "";
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

export function getPageTitle(pathname: string): string {
  if (pathname === "/" || pathname === "/inicio") {
    return DEFAULT_PAGE_TITLE;
  }

  if (pathname.startsWith("/locacao")) {
    return `Locação | ${SITE_NAME}`;
  }

  if (pathname.startsWith("/vendas") || pathname.startsWith("/venda")) {
    return `Vendas | ${SITE_NAME}`;
  }

  if (pathname.startsWith("/sobre") || pathname.startsWith("/a-empresa")) {
    return `Sobre a GranKasa | ${SITE_NAME}`;
  }

  if (pathname.startsWith("/fale-conosco")) {
    return `Fale Conosco | ${SITE_NAME}`;
  }

  if (pathname.startsWith("/busca")) {
    return `Busca de Imóveis | ${SITE_NAME}`;
  }

  if (pathname.startsWith("/imovel/")) {
    const codigo = decodePathSegment(pathname.split("/")[2]);
    if (codigo) return `Imóvel ${codigo.toUpperCase()} | ${SITE_NAME}`;
    return `Detalhes do Imóvel | ${SITE_NAME}`;
  }

  return SITE_NAME;
}
