import { describe, expect, it } from "vitest";

import { buildMapsEmbedUrl, buildMapsSearchUrl } from "@/lib/maps";

describe("maps helpers", () => {
  it("gera URL de busca para link de embed com parÃ¢metro origin", () => {
    const embedUrl =
      "https://www.google.com/maps/embed?origin=Professor+Silvio+Elias+55+Vargem+Grande+Rio+De+Janeiro&pb=!1m2!1m1!1sProfessor+Silvio+Elias+55+Vargem+Grande+Rio+De+Janeiro";

    const link = buildMapsSearchUrl(embedUrl);
    expect(link).toBe(
      "https://www.google.com/maps/search/?api=1&query=Professor%20Silvio%20Elias%2055%20Vargem%20Grande%20Rio%20De%20Janeiro",
    );
  });

  it("mantÃ©m URL externa quando nÃ£o for Google Maps", () => {
    const link = buildMapsSearchUrl("https://maps.example.com/asset/123");
    expect(link).toBe("https://maps.example.com/asset/123");
  });

  it("gera embed via fallback quando sÃ³ existe query textual", () => {
    const embed = buildMapsEmbedUrl(null, "Copacabana, Rio de Janeiro");
    expect(embed).toBe("https://www.google.com/maps?q=Copacabana%2C%20Rio%20de%20Janeiro&output=embed");
  });
});
