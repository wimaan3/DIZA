import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.beforeEach(async ({ page, request }) => {
  await request.post("/api/care/demo");
  await page.goto("/care");
  await expect(
    page.getByRole("heading", { name: "Care, in good hands." }),
  ).toBeVisible();
});

async function rooms(page) {
  await page
    .getByRole("button", { name: "Rooms & repairs", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Resident rooms & shared systems" }),
  ).toBeVisible();
}

test("care and repairs share rooms, original reports, transcripts, and links", async ({
  page,
}) => {
  await rooms(page);
  await page.getByRole("button", { name: /^Room 101 Margaret Wilson/ }).click();
  await expect(
    page.getByRole("heading", { name: "Room incident queue 1" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Original reports (2)" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /Related incidents \([1-9]/ }),
  ).toBeVisible();
  await page
    .getByText("Call summary & transcript", { exact: true })
    .first()
    .click();
  await expect(
    page.getByText("Synthetic demo transcript", { exact: true }).first(),
  ).toBeVisible();
  await page.locator(".related-care-link").first().click();
  await expect(
    page.getByRole("heading", { name: "Margaret Wilson", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Shared room incident", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: /^Open T-/ }).click();
  await expect(
    page.getByRole("heading", { name: "Resident rooms & shared systems" }),
  ).toBeVisible();
});

test("maintenance intake captures issue type and access permission", async ({
  page,
  request,
}) => {
  const summary = `Reading lamp needs replacement ${Date.now()}`;
  await page
    .getByRole("button", { name: "Record a request", exact: true })
    .first()
    .click();
  await page
    .getByRole("combobox", { name: "Resident", exact: true })
    .selectOption("r6");
  await page
    .getByRole("combobox", { name: "Type of request", exact: true })
    .selectOption("maintenance");
  await page
    .getByRole("combobox", { name: "Room issue type", exact: true })
    .selectOption("appliance");
  await page
    .getByRole("combobox", { name: "Permission to enter", exact: true })
    .selectOption("no");
  await page.getByLabel("What is needed?").fill(summary);
  await page
    .getByLabel("Resident or reporter's exact words")
    .fill("Please arrange a time to visit my room.");
  await page
    .getByRole("button", { name: "Record request", exact: true })
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  const state = await (await request.get("/api/care/state")).json();
  const item = state.requests.find((r) => r.summary === summary);
  expect(item.facility_code).toBeTruthy();
  await rooms(page);
  await page
    .locator(`.incident-queue [data-facility-code="${item.facility_code}"]`)
    .click();
  await expect(
    page.getByText("Do not enter; arrange access", { exact: true }),
  ).toBeVisible();
});

test("vendor repair outcome leaves the individual resident request open", async ({
  page,
  request,
}) => {
  const summary = `Pest review ${Date.now()}`;
  const result = await request.post("/api/care/requests", {
    data: {
      idempotency_key: summary,
      resident_id: "r6",
      category: "maintenance",
      facility_category: "pest",
      summary,
      reported_by: "Demo staff",
    },
  });
  const item = await result.json();
  await page.reload();
  await page
    .getByLabel("Working as staff member")
    .selectOption("facilities-alex");
  await rooms(page);
  await page
    .locator(`.incident-queue [data-facility-code="${item.facility_code}"]`)
    .click();
  await page
    .getByRole("button", { name: "Assign facilities / vendor", exact: true })
    .click();
  await page
    .getByRole("combobox", {
      name: "Assigned team member or vendor",
      exact: true,
    })
    .selectOption("facilities-alex");
  await page
    .getByRole("button", { name: "Save assignment", exact: true })
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.getByRole("button", { name: "Start repair", exact: true }).click();
  await page
    .getByRole("button", { name: "Record repair outcome", exact: true })
    .click();
  await page
    .getByLabel("Repair outcome", { exact: true })
    .fill(
      "Room checked and treatment arranged. Care team to follow up with resident.",
    );
  await page.getByRole("button", { name: "Close repair", exact: true }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.getByRole("button", { name: /^Daily care/ }).click();
  await page.getByLabel("Search care requests").fill(summary);
  await expect(
    page.getByRole("heading", { name: "Samuel Okafor", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Accept responsibility", exact: true }),
  ).toBeEnabled();
});

test("staff link and unmerge related repairs without losing resident records", async ({
  page,
  request,
}) => {
  const stamp = Date.now(),
    items = [];
  for (const resident of ["r1", "r3"]) {
    const response = await request.post("/api/care/requests", {
      data: {
        idempotency_key: `${resident}-${stamp}`,
        resident_id: resident,
        category: "maintenance",
        facility_category: "noise",
        summary: `Shared noise issue ${resident} ${stamp}`,
        reported_by: "Demo staff",
      },
    });
    items.push(await response.json());
  }
  await page.reload();
  await page.getByLabel("Working as staff member").selectOption("lead-morgan");
  await rooms(page);
  await page
    .locator(`.incident-queue [data-facility-code="${items[1].facility_code}"]`)
    .click();
  await page
    .getByRole("button", { name: "Link into shared incident", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "Shared incident", exact: true })
    .selectOption(items[0].facility_code);
  await page
    .getByLabel("Facilities note", { exact: true })
    .fill("Both reports describe the same noise source.");
  await page
    .getByRole("button", { name: "Link incidents", exact: true })
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page
    .locator(`.incident-queue [data-facility-code="${items[0].facility_code}"]`)
    .click();
  await expect(page.locator(".linked-care .related-care-link")).toHaveCount(2);
  await page
    .getByRole("button", {
      name: `Unmerge ${items[1].facility_code}`,
      exact: true,
    })
    .click();
  await page
    .getByLabel("Facilities note", { exact: true })
    .fill("Staff confirmed two different sources.");
  await page
    .getByRole("button", { name: "Unmerge incident", exact: true })
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(
    page.locator(
      `.incident-queue [data-facility-code="${items[1].facility_code}"]`,
    ),
  ).toBeVisible();
});

test("facilities can separate a duplicate and navigate with J and K", async ({
  page,
}) => {
  await page
    .getByLabel("Working as staff member")
    .selectOption("facilities-alex");
  await rooms(page);
  await page.getByRole("button", { name: /^Room 101 Margaret Wilson/ }).click();
  const count = await page.locator(".incident-queue .request-card").count();
  await page
    .getByRole("button", { name: "Separate this report", exact: true })
    .last()
    .click();
  await page
    .getByLabel("Facilities note", { exact: true })
    .fill("Staff found a separate heater issue.");
  await page
    .getByRole("button", { name: "Separate report", exact: true })
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(page.locator(".incident-queue .request-card")).toHaveCount(
    count + 1,
  );
  const before = await page
    .locator('.incident-queue [aria-pressed="true"]')
    .getAttribute("data-facility-code");
  await page.locator('.incident-queue [aria-pressed="true"]').focus();
  await page.keyboard.press("j");
  const after = await page
    .locator('.incident-queue [aria-pressed="true"]')
    .getAttribute("data-facility-code");
  expect(after).not.toBe(before);
  await page.keyboard.press("k");
  await expect(
    page.locator('.incident-queue [aria-pressed="true"]'),
  ).toHaveAttribute("data-facility-code", before);
});

test("combined room workspace and assignment dialog pass desktop and mobile accessibility checks", async ({
  page,
}) => {
  await page.getByLabel("Working as staff member").selectOption("lead-morgan");
  await rooms(page);
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 950 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    await page.screenshot({
      path: `test-results/combined-rooms-${width}.png`,
      fullPage: true,
    });
    const scan = await new AxeBuilder({ page }).analyze();
    expect(
      scan.violations.map((v) => ({
        id: v.id,
        nodes: v.nodes.map((n) => ({
          target: n.target,
          reason: n.failureSummary,
        })),
      })),
    ).toEqual([]);
  }
  await page
    .getByRole("button", {
      name: /Assign facilities \/ vendor|Change assignee/,
    })
    .click();
  const scan = await new AxeBuilder({ page }).analyze();
  expect(scan.violations.map((v) => v.id)).toEqual([]);
});

test("room metadata editing keeps resident links and updates shared-system context", async ({
  page,
}) => {
  await page
    .getByLabel("Working as staff member")
    .selectOption("facilities-alex");
  await rooms(page);
  await page
    .getByRole("button", { name: "Edit room 103", exact: true })
    .click();
  await page.getByLabel("HVAC zone", { exact: true }).fill("Garden east");
  await page.getByRole("button", { name: "Save room", exact: true }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(
    page.getByText("Riser R3 · HVAC Garden east", { exact: true }),
  ).toBeVisible();
});
