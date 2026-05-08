import { expect, test } from "@playwright/test";

const HEALTH_OK = {
  status: "ok",
  llm_configured: true,
  chunk_count: 12,
  document_count: 1,
  embedding_model: "test-model",
  llm_probe: { status: "ok" }
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(HEALTH_OK) })
  );
});

test("loads the homepage with brand and assistant section", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Jiahan Wang/);
  await expect(page.getByText("Jiahan Wang").first()).toBeVisible();
  await expect(page.getByText("Assistant AI")).toBeVisible();
  await expect(page.getByLabel(/votre question/i)).toBeVisible();
});

test("loads the Chinese landing page", async ({ page }) => {
  await page.goto("/zh");
  await expect(page).toHaveTitle(/王稼瀚/);
});

test("submits a chat question and renders the answer", async ({ page }) => {
  await page.route("**/api/chat", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        answer: "E2E mocked answer about Jiahan.",
        sources: [{ source: "profile.md", snippet: "snippet from profile", score: 0.87 }]
      })
    })
  );

  await page.goto("/");
  const textarea = page.getByLabel(/votre question/i);
  await textarea.fill("Quels sont ses projets ?");
  await page.getByRole("button", { name: "Envoyer" }).click();

  await expect(page.getByText("E2E mocked answer about Jiahan.")).toBeVisible();
  await expect(page.getByText("profile.md")).toBeVisible();
});

test("clicking a prompt tag triggers a chat request", async ({ page }) => {
  let chatRequestSeen = false;
  await page.route("**/api/chat", async (route) => {
    chatRequestSeen = true;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        answer: "Prompt-tag answer.",
        sources: []
      })
    });
  });

  await page.goto("/");
  const firstPrompt = page.locator(".prompt-tag").first();
  await firstPrompt.click();

  await expect(page.getByText("Prompt-tag answer.")).toBeVisible();
  expect(chatRequestSeen).toBe(true);
});
