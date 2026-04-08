import { describe, expect, it } from "vitest";

import { DEFAULT_PAGE_TITLE, getPageTitle } from "@/lib/page-metadata";

describe("page-metadata", () => {
  it("mantem titulo da home para / e /inicio", () => {
    expect(getPageTitle("/")).toBe(DEFAULT_PAGE_TITLE);
    expect(getPageTitle("/inicio")).toBe(DEFAULT_PAGE_TITLE);
  });

  it("resolve titulos para rotas publicas principais", () => {
    expect(getPageTitle("/locacao")).toBe("Locação | GranKasa Imóveis");
    expect(getPageTitle("/vendas")).toBe("Vendas | GranKasa Imóveis");
    expect(getPageTitle("/venda")).toBe("Vendas | GranKasa Imóveis");
    expect(getPageTitle("/sobre")).toBe("Sobre a GranKasa | GranKasa Imóveis");
    expect(getPageTitle("/a-empresa")).toBe("Sobre a GranKasa | GranKasa Imóveis");
  });

  it("usa codigo do imovel no titulo de detalhe", () => {
    expect(getPageTitle("/imovel/ab-123")).toBe("Imóvel AB-123 | GranKasa Imóveis");
  });

  it("retorna titulo neutro para rotas desconhecidas", () => {
    expect(getPageTitle("/rota-nao-existe")).toBe("GranKasa Imóveis");
  });
});
