import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PreviewIframe } from "../preview-iframe";

describe("PreviewIframe", () => {
  const SAMPLE_HTML = `<!DOCTYPE html><html><head></head><body>
    <table><tr><td style="color:#333333; font-size:14px">Test</td></tr></table>
  </body></html>`;

  it("renders iframe with sandbox=allow-same-origin", () => {
    render(
      <PreviewIframe
        compiledHtml={SAMPLE_HTML}
        viewport="desktop"
        darkMode={false}
        zoom={100}
        isCompiling={false}
      />,
    );
    const iframe = screen.getByTitle("Email preview");
    expect(iframe).toHaveAttribute("sandbox", "allow-same-origin");
  });

  it("sandbox does NOT include allow-scripts", () => {
    render(
      <PreviewIframe
        compiledHtml={SAMPLE_HTML}
        viewport="desktop"
        darkMode={false}
        zoom={100}
        isCompiling={false}
      />,
    );
    const iframe = screen.getByTitle("Email preview");
    expect(iframe.getAttribute("sandbox")).not.toContain("allow-scripts");
  });

  it("shows compile prompt when compiledHtml is null", () => {
    render(
      <PreviewIframe
        compiledHtml={null}
        viewport="desktop"
        darkMode={false}
        zoom={100}
        isCompiling={false}
      />,
    );
    expect(screen.getByText(/Ctrl\+S/)).toBeDefined();
  });

  it("shows loading spinner when compiling", () => {
    render(
      <PreviewIframe
        compiledHtml={null}
        viewport="desktop"
        darkMode={false}
        zoom={100}
        isCompiling={true}
      />,
    );
    expect(screen.getByText("Compiling...")).toBeDefined();
  });
});
