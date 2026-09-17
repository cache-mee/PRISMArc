import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import App from "../src/App";

describe("App", () => {
  it("renders the placeholder heading", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "Salon App" }),
    ).toBeInTheDocument();
  });
});
