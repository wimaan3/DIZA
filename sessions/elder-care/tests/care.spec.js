import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const violations = (result) =>
  result.violations.map((v) => ({
    id: v.id,
    nodes: v.nodes.map((n) => ({ target: n.target, reason: n.failureSummary })),
  }));

test.beforeEach(async ({ page, request }) => {
  await request.post("/api/care/demo");
  await page.goto("/care");
  await expect(
    page.getByRole("heading", { name: "Care, in good hands." }),
  ).toBeVisible();
});

test("daily care request can be recorded, accepted, completed, and reviewed", async ({
  page,
}) => {
  const summary = `Help choosing lunch ${Date.now()}`;
  await page
    .getByRole("button", { name: "Record a request", exact: true })
    .first()
    .click();
  const dialog = page.getByRole("dialog");
  await dialog
    .getByRole("combobox", { name: "Resident", exact: true })
    .selectOption("r3");
  await dialog.getByLabel("Type of request").selectOption("meal");
  await dialog.getByLabel("What is needed?").fill(summary);
  await dialog
    .getByLabel("Resident or reporter's exact words")
    .fill("I would like some water and the lunch menu.");
  await dialog
    .getByRole("button", { name: "Record request", exact: true })
    .click();
  await expect(dialog).not.toBeVisible();
  await page.getByLabel("Search care requests").fill(summary);
  await expect(
    page.getByRole("heading", { name: "Elena Garcia", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Accept responsibility", exact: true })
    .click();
  await page.getByRole("button", { name: "Start care", exact: true }).click();
  await page
    .getByRole("button", { name: "Record outcome & resolve", exact: true })
    .click();
  await page
    .getByLabel("Outcome and follow-up")
    .fill("Water provided and menu explained. Resident comfortable.");
  await page
    .getByRole("button", { name: "Resolve request", exact: true })
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page
    .getByRole("button", { name: "Completed care", exact: true })
    .click();
  await page.getByLabel("Search care requests").fill(summary);
  await expect(
    page.getByText(
      "Resolved by staff: Water provided and menu explained. Resident comfortable.",
      { exact: true },
    ),
  ).toBeVisible();
  await page.reload();
  await page
    .getByRole("button", { name: "Completed care", exact: true })
    .click();
  await page.getByLabel("Search care requests").fill(summary);
  await expect(
    page.getByRole("heading", { name: "Elena Garcia", exact: true }),
  ).toBeVisible();
});

test("original words raise a daily report to urgent and only a nurse can accept", async ({
  page,
}) => {
  const summary = `Needs a hand ${Date.now()}`;
  await page
    .getByRole("button", { name: "Record a request", exact: true })
    .first()
    .click();
  await page
    .getByRole("combobox", { name: "Resident", exact: true })
    .selectOption("r1");
  await page.getByLabel("What is needed?").fill(summary);
  await page
    .getByLabel("Resident or reporter's exact words")
    .fill("I fell beside the armchair.");
  await page
    .getByRole("button", { name: "Record request", exact: true })
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.getByRole("button", { name: /^Urgent response/ }).click();
  await page.getByLabel("Search care requests").fill(summary);
  await expect(
    page.getByText("Urgent human review", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/Escalation cue "fell"/).first()).toBeVisible();
  await page.getByLabel("Working as staff member").selectOption("care-amira");
  await expect(
    page.getByRole("button", { name: "Accept responsibility", exact: true }),
  ).toBeDisabled();
  await page.getByLabel("Working as staff member").selectOption("nurse-jordan");
  await page
    .getByRole("button", { name: "Accept responsibility", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Start care", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(/No emergency services have been contacted by DIZA/),
  ).toBeVisible();
});

test("check-in concerns become visible queue work", async ({ page }) => {
  await page
    .getByRole("button", { name: "Residents & check-ins", exact: true })
    .click();
  const resident = page.getByRole("article").filter({
    has: page.getByRole("heading", { name: "Samuel Okafor", exact: true }),
  });
  await resident.getByRole("button", { name: /check-in/ }).click();
  await page.getByLabel("Check-in outcome").selectOption("no_response");
  await page
    .getByLabel("Observation", { exact: true })
    .fill("Knocked twice after breakfast; no answer. Please visit the room.");
  await page
    .getByRole("button", { name: "Save check-in", exact: true })
    .click();
  await expect(
    resident.getByText("No response recorded", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: /^Daily care/ }).click();
  await page.getByLabel("Search care requests").fill("Samuel");
  await expect(
    page.getByRole("button", { name: /No response at check-in/ }),
  ).toBeVisible();
  await expect(
    page
      .getByText(
        "Knocked twice after breakfast; no answer. Please visit the room.",
        { exact: false },
      )
      .first(),
  ).toBeVisible();
});

test("staff can escalate an accepted routine request and it returns to nurse review", async ({
  page,
  request,
}) => {
  const summary = `Escalation scenario ${Date.now()}`;
  const result = await request.post("/api/care/requests", {
    data: {
      idempotency_key: summary,
      resident_id: "r5",
      category: "personal_care",
      summary,
      reported_by: "Test staff",
    },
  });
  expect(result.ok()).toBeTruthy();
  await page.reload();
  await page.getByLabel("Search care requests").fill(summary);
  await page.getByLabel("Working as staff member").selectOption("care-amira");
  await page
    .getByRole("button", { name: "Accept responsibility", exact: true })
    .click();
  await page.getByRole("button", { name: "Mark urgent", exact: true }).click();
  await page
    .getByLabel("Reason for urgency")
    .fill("New concern reported by the resident; nurse review requested.");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Mark urgent", exact: true })
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.getByRole("button", { name: /^Urgent response/ }).click();
  await page.getByLabel("Search care requests").fill(summary);
  await expect(
    page.getByRole("button", { name: "Accept responsibility", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByText("Not yet accepted", { exact: true }),
  ).toBeVisible();
});

test("desktop daily and urgent queues pass accessibility checks", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page.screenshot({
    path: "test-results/daily-desktop.png",
    fullPage: true,
  });
  const daily = await new AxeBuilder({ page }).analyze();
  expect(violations(daily)).toEqual([]);
  await page.getByRole("button", { name: /^Urgent response/ }).click();
  await page.screenshot({
    path: "test-results/urgent-desktop.png",
    fullPage: true,
  });
  const urgent = await new AxeBuilder({ page }).analyze();
  expect(violations(urgent)).toEqual([]);
});

test("mobile roster and request dialog fit the viewport and are accessible", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page
    .getByRole("button", { name: "Residents & check-ins", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Today's wellbeing check-ins" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "test-results/residents-mobile.png",
    fullPage: true,
  });
  expect(
    await page.locator(".nav-item > span").evaluateAll((labels) =>
      labels.every((label) => {
        const text = label.getBoundingClientRect();
        const button = label.parentElement.getBoundingClientRect();
        return text.left >= button.left && text.right <= button.right;
      }),
    ),
  ).toBeTruthy();
  const roster = await new AxeBuilder({ page }).analyze();
  expect(violations(roster)).toEqual([]);
  await page
    .getByRole("button", { name: "Record a request", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  const box = await dialog.boundingBox();
  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width).toBeLessThanOrEqual(390);
  const form = await new AxeBuilder({ page }).analyze();
  expect(violations(form)).toEqual([]);
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
});

test("polling preserves an in-progress handoff note and reports API errors", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Add note", exact: true }).click();
  await page
    .getByLabel("Handoff note", { exact: true })
    .fill("Please offer a seat by the garden.");
  await page.clock.install();
  await page.clock.fastForward(8000);
  await expect(page.getByLabel("Handoff note", { exact: true })).toHaveValue(
    "Please offer a seat by the garden.",
  );
  await page.route("**/api/care/requests/*/actions", (route) =>
    route.fulfill({
      status: 409,
      contentType: "application/json",
      body: JSON.stringify({
        detail: "This request changed. Refresh and review it before acting.",
      }),
    }),
  );
  await page.getByRole("button", { name: "Save note", exact: true }).click();
  await expect(page.getByRole("dialog").getByRole("alert")).toHaveText(
    "This request changed. Refresh and review it before acting.",
  );
  await expect(page.getByLabel("Handoff note", { exact: true })).toHaveValue(
    "Please offer a seat by the garden.",
  );
});

test("network loss blocks staff actions and recovery restores the queue", async ({
  page,
}) => {
  await page.route("**/api/care/state", (route) => route.abort());
  await page.getByRole("button", { name: /^Daily care/ }).click();
  await expect(
    page.getByText(
      "Connection lost. Requests may be out of date. Reconnect before acting.",
    ),
  ).toBeVisible({ timeout: 12000 });
  await expect(
    page.getByRole("button", { name: "Record a request", exact: true }).first(),
  ).toBeDisabled();
  await page.unroute("**/api/care/state");
  await page.getByRole("button", { name: "Reconnect", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Record a request", exact: true }).first(),
  ).toBeEnabled();
});

test("background refresh preserves keyboard focus on staff controls", async ({
  page,
}) => {
  await page.clock.install();
  const nav = page.getByRole("button", { name: /^Daily care/ });
  await nav.focus();
  await page.clock.fastForward(8000);
  await expect(nav).toBeFocused();
});
