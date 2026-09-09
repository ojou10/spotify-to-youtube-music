import { render, screen } from "@testing-library/react";

import { App } from "./App";

it("identifies the product", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: /playlist bridge/i })).toBeVisible();
});
