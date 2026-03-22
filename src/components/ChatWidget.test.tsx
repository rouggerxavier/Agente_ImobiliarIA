import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ChatWidget from "@/components/ChatWidget";

describe("ChatWidget", () => {
  beforeEach(() => {
    vi.stubGlobal("crypto", { randomUUID: () => "session-test-id" });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("evita container full-width quando fechado no mobile", () => {
    render(<ChatWidget />);

    const openButton = screen.getByRole("button", { name: "Abrir chat com assistente virtual" });
    const closedContainer = openButton.parentElement;

    expect(closedContainer).toBeTruthy();
    expect(closedContainer).toHaveClass("right-4");
    expect(closedContainer).not.toHaveClass("left-4");

    fireEvent.click(openButton);

    const closeButton = screen.getByRole("button", { name: "Fechar chat com assistente virtual" });
    const openedContainer = closeButton.parentElement;

    expect(openedContainer).toBeTruthy();
    expect(openedContainer).toHaveClass("left-4");
    expect(openedContainer).toHaveClass("right-4");
  });
});
