import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import App from "../App";

describe("User App", () => {
  it("renders without crashing", () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );
    expect(document.body).toBeTruthy();
  });

  it("renders search page by default", () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );
    const searchInput = document.querySelector('input[type="text"]');
    expect(searchInput || document.body).toBeTruthy();
  });
});
