import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import App from "../App.jsx";
import { siteContent, zhPageContent } from "../siteContent.js";

const buildHealthResponse = (overrides = {}) => ({
  ok: true,
  json: async () => ({
    status: "ok",
    llm_configured: true,
    chunk_count: 12,
    document_count: 1,
    embedding_model: "test-model",
    llm_probe: { status: "ok" },
    ...overrides
  })
});

describe("PortfolioPage (default route)", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/");
    global.fetch = vi.fn(async () => buildHealthResponse());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the brand and assistant section", async () => {
    render(<App />);
    expect(screen.getByText(siteContent.person.name)).toBeInTheDocument();
    expect(screen.getByText("Assistant AI")).toBeInTheDocument();
    expect(screen.getByLabelText(/votre question/i)).toBeInTheDocument();
  });

  it("hits /api/health on mount and shows ready status", async () => {
    render(<App />);
    await waitFor(() => expect(global.fetch).toHaveBeenCalledWith("/api/health"));
    await waitFor(() =>
      expect(screen.getByText(new RegExp(siteContent.assistant.status.ready))).toBeInTheDocument()
    );
  });

  it("shows degraded status when llm_configured is false", async () => {
    global.fetch = vi.fn(async () => buildHealthResponse({ llm_configured: false }));
    render(<App />);
    await waitFor(() =>
      expect(
        screen.getByText(new RegExp(siteContent.assistant.status.degraded))
      ).toBeInTheDocument()
    );
  });

  it("shows offline status when /api/health fails", async () => {
    global.fetch = vi.fn(async () => ({ ok: false }));
    render(<App />);
    await waitFor(() =>
      expect(
        screen.getByText(new RegExp(siteContent.assistant.status.offline))
      ).toBeInTheDocument()
    );
  });

  it("sends a chat request and renders the answer", async () => {
    const user = userEvent.setup();
    global.fetch = vi.fn(async (url, options) => {
      if (url === "/api/health") return buildHealthResponse();
      if (url === "/api/chat" && options?.method === "POST") {
        return {
          ok: true,
          json: async () => ({
            answer: "Mocked Jiahan answer.",
            sources: [{ source: "profile.md", snippet: "snippet text", score: 0.91 }]
          })
        };
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });

    render(<App />);
    const textarea = screen.getByLabelText(/votre question/i);
    await user.type(textarea, "Qui est Jiahan ?");
    await user.click(screen.getByRole("button", { name: siteContent.assistant.submitLabel }));

    await waitFor(() => expect(screen.getByText("Mocked Jiahan answer.")).toBeInTheDocument());
    expect(screen.getByText("profile.md")).toBeInTheDocument();
  });

  it("renders an error bubble when /api/chat fails", async () => {
    const user = userEvent.setup();
    global.fetch = vi.fn(async (url, options) => {
      if (url === "/api/health") return buildHealthResponse();
      if (url === "/api/chat" && options?.method === "POST") {
        return {
          ok: false,
          json: async () => ({ detail: "LLM down for the test." })
        };
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });

    render(<App />);
    await user.type(screen.getByLabelText(/votre question/i), "ping?");
    await user.click(screen.getByRole("button", { name: siteContent.assistant.submitLabel }));

    await waitFor(() =>
      expect(screen.getByText("LLM down for the test.")).toBeInTheDocument()
    );
  });
});

describe("ChinesePage (/zh route)", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/zh");
    global.fetch = vi.fn(async () => buildHealthResponse());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the Chinese intro title", async () => {
    render(<App />);
    expect(screen.getByText(zhPageContent.introTitle)).toBeInTheDocument();
  });
});
