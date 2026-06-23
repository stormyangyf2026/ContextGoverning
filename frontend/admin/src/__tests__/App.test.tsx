import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import App from "../App";

describe("Admin App", () => {
  it("renders without crashing", () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );
    expect(document.body).toBeTruthy();
  });

  it("renders navigation", () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );
    const nav = document.querySelector("nav");
    expect(nav).toBeTruthy();
  });
});
