import { test, expect } from "@playwright/test";

const headers = { Authorization: "Bearer hotel-demo-local" };
async function data(request) {
  const response = await request.get("/api/hotel/state", { headers });
  expect(response.ok()).toBeTruthy();
  return response.json();
}
const errors = [];
test.beforeEach(async ({ page }) => {
  page.on("pageerror", (error) => errors.push(error.message));
});
test.afterEach(() => {
  expect(errors.splice(0)).toEqual([]);
});

test("guest answer, confirmed housekeeping request, staff completion, and handover note", async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 1512, height: 1100 });
  await page.goto("/hotel");
  await expect(page.locator("#connection")).toHaveText("Live workspace");
  await expect(page.locator("#open-count")).toHaveText("4");
  await page.getByRole("button", { name: "Wi-Fi help", exact: true }).click();
  await expect(page.locator("#conversation")).toContainText(
    "HarborHouse-Guest",
  );
  await expect(page.locator("#answered-count")).toHaveText("1");
  await expect(page.locator("#open-count")).toHaveText("4");
  await page.getByRole("button", { name: "Extra towels", exact: true }).click();
  await expect(page.locator("#request-readback")).toBeVisible();
  await expect(page.locator("#open-count")).toHaveText("4");
  await page.locator("#entry-permission").check();
  await page
    .getByRole("button", { name: "Confirm request", exact: true })
    .click();
  await expect(page.locator("#guest-tasks")).toContainText("Awaiting owner");
  await expect(page.locator("#open-count")).toHaveText("5");
  const task = (await data(request)).tickets.find(
    (t) => t.room === "402" && t.category === "housekeeping",
  );
  expect(task.access_ok).toBeTruthy();
  await page.screenshot({
    path: "../artifacts/hotel-desktop.png",
    fullPage: true,
  });
  await page.locator(`[data-ticket="${task.id}"]`).click();
  await page.getByLabel("Assign request to staff").selectOption("ana");
  await page
    .getByRole("button", { name: "Accept request", exact: true })
    .click();
  await expect(page.locator("#ticket-body")).toContainText(
    "Owner: Ana Morales",
  );
  await page.getByRole("button", { name: "Start work", exact: true }).click();
  await page
    .getByRole("button", { name: "Record completed", exact: true })
    .click();
  await expect(page.locator("#guest-tasks")).toContainText(
    "Completed · Ana Morales",
  );
  const completed = (await data(request)).tickets.find(
    (t) => t.id === task.id,
  ).completed;
  await page
    .getByLabel("Staff handover note")
    .fill("Delivered the towels to the guest.");
  await page.getByRole("button", { name: "Save note", exact: true }).click();
  await expect(page.locator(".timeline")).toContainText(
    "Delivered the towels to the guest.",
  );
  expect(
    (await data(request)).tickets.find((t) => t.id === task.id).completed,
  ).toBe(completed);
  await page
    .getByRole("button", { name: "Close request", exact: true })
    .click();
  await page.reload();
  await expect(page.locator("#guest-tasks")).toContainText(
    "Completed · Ana Morales",
  );
});

test("Spanish guest requests and the staff queue fit a phone screen", async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/building");
  await expect(page.locator("#connection")).toHaveText("Live workspace");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.getByLabel("Demo room", { exact: true }).selectOption("403");
  await page.getByLabel("Guest language", { exact: true }).selectOption("es");
  await page
    .getByRole("button", { name: "El aire no enfría", exact: true })
    .click();
  await expect(page.locator("#conversation")).toContainText(
    "Puedo registrar tu solicitud",
  );
  await expect(page.locator("#readback-title")).toContainText("Habitación 403");
  await page
    .getByRole("button", { name: "Confirmar solicitud", exact: true })
    .click();
  await expect(page.locator("#guest-tasks")).toContainText(
    "Esperando responsable",
  );
  const ticket = (await data(request)).tickets.find((t) => t.room === "403");
  expect(ticket.access_ok).toBeFalsy();
  await page
    .getByRole("searchbox", { name: "Find a room or request" })
    .fill("403");
  await expect(page.locator("#request-list .request-row")).toHaveCount(1);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "../artifacts/hotel-mobile.png",
    fullPage: true,
  });
});

test("lost confirmation response can be retried without creating another staff task", async ({
  page,
  request,
}) => {
  await page.goto("/hotel");
  await page.getByLabel("Demo room", { exact: true }).selectOption("404");
  await page.getByRole("button", { name: "Extra towels", exact: true }).click();
  await expect(page.locator("#request-readback")).toBeVisible();
  let calls = 0;
  await page.route("**/api/hotel/guest/*/confirm", async (route) => {
    if (calls++ === 0) {
      await route.fetch();
      await route.abort("failed");
    } else await route.continue();
  });
  await page
    .getByRole("button", { name: "Confirm request", exact: true })
    .click();
  await expect(page.locator("#guest-status")).toContainText(
    "Connection interrupted",
  );
  await page
    .getByRole("button", { name: "Confirm request", exact: true })
    .click();
  await expect(page.locator("#guest-tasks")).toContainText("Awaiting owner");
  expect(
    (await data(request)).tickets.filter(
      (t) => t.room === "404" && t.category === "housekeeping",
    ),
  ).toHaveLength(1);
  await page.reload();
  await expect(page.locator("#guest-tasks")).toContainText("Awaiting owner");
});
