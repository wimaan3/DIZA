import { test, expect } from "@playwright/test";

const operator = { Authorization: "Bearer relay-demo-local" };
const errors = [];
test.beforeEach(async ({ page }) => {
  page.on("pageerror", (error) => errors.push(error.message));
});
test.afterEach(() => {
  expect(errors.splice(0)).toEqual([]);
});

async function dashboard(request) {
  const response = await request.get("/api/relay/dashboard", {
    headers: operator,
  });
  expect(response.ok()).toBeTruthy();
  return response.json();
}
async function login(page) {
  await page.goto("/ops");
  await page.getByLabel("Operator token").fill("relay-demo-local");
  await page.getByRole("button", { name: "Open workspace" }).click();
  await expect(page.getByText("Live workspace", { exact: true })).toBeVisible();
}

test("a Spanish response, revised instruction, and owned assistance stay in one record", async ({
  page,
  context,
  request,
}) => {
  await page.setViewportSize({ width: 1440, height: 1100 });
  await login(page);
  const data = await dashboard(request);
  const record = data.records.find((r) =>
    r.resident.name.startsWith("Marisol"),
  );
  const resident = await context.newPage();
  await resident.goto(record.response_url);
  await expect(resident.locator("#approved-label")).toHaveText(
    "AVISO APROBADO DE LA COMUNIDAD",
  );
  await expect(resident.locator("#draft-status")).toHaveText("Sin enviar");
  await resident.locator("#next-step").fill("Usaré la entrada norte");
  await resident.getByLabel("Sí, necesito ayuda", { exact: true }).check();
  await resident
    .locator("#assistance-details")
    .fill("Uso un andador y necesito ayuda para llegar a la entrada.");
  await resident.locator("#confirm-assistance").check();
  await resident
    .getByRole("button", { name: "Guardar mi respuesta", exact: true })
    .click();
  await expect(resident.locator("#saved-summary")).toContainText(
    "Última instrucción confirmada",
  );
  await expect(resident.locator("#saved-summary")).toContainText(
    "esperando responsable",
  );
  await page.getByRole("button", { name: "Refresh", exact: false }).click();
  await expect(page.locator("#confirmed-count")).toHaveText("2");
  await page.screenshot({
    path: "../artifacts/relay-coordinator-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Revise notice" }).click();
  const form = page.locator("#publish-form");
  await form
    .locator('[name="en_text"]')
    .fill(
      "Today's community shuttle pickup has moved to the east entrance. Please arrive by 3:00 PM.",
    );
  await form
    .locator('[name="es_text"]')
    .fill(
      "La recogida de hoy se ha trasladado a la entrada este. Llega a las 3:00 p. m.",
    );
  await form.locator('[name="en_step"]').fill("east entrance");
  await form.locator('[name="es_step"]').fill("entrada este");
  await form
    .locator('[name="reason"]')
    .fill("The north entrance is unavailable");
  await page.locator("#publish-approval").check();
  await page
    .getByRole("button", { name: "Publish update", exact: true })
    .click();
  await expect(page.locator("#notice-version")).toHaveText("V2");
  await expect(page.locator("#updated-count")).toHaveText("2");
  const row = page.locator(`tr[data-record="${record.record_id}"]`);
  await expect(row).toContainText("Updated notice awaiting confirmation");
  await expect(row).toContainText("Awaiting owner");
  await resident.reload();
  await expect(resident.locator("#resident-version")).toHaveText("V2");
  await expect(resident.locator("#next-step")).toHaveValue("");
  await resident.locator("#next-step").fill("Usaré la entrada este");
  await resident
    .getByRole("button", { name: "Guardar mi respuesta", exact: true })
    .click();
  await expect(resident.locator("#saved-summary")).toContainText("V1:");
  await expect(resident.locator("#saved-summary")).toContainText("V2:");
  await page
    .getByRole("button", { name: "View Marisol (demo) record", exact: true })
    .click();
  await page.getByLabel("Assistance coordinator name").fill("Ana");
  await page.getByRole("button", { name: "Accept assistance request" }).click();
  await expect(page.locator("#record-body")).toContainText("Owner: Ana");
  await expect(page.locator("#record-body")).toContainText("V1 ·");
  await expect(page.locator("#record-body")).toContainText("V2 ·");
  await page
    .getByRole("button", { name: "Record assistance completed" })
    .click();
  await expect(page.locator("#record-body")).toContainText("Completed");
  await page.getByRole("button", { name: "Close", exact: true }).last().click();
  await page.screenshot({
    path: "../artifacts/relay-coordinator-updated.png",
    fullPage: true,
  });
  await resident.setViewportSize({ width: 390, height: 844 });
  await resident.reload();
  await expect(resident.locator("#saved-summary")).toContainText(
    "Ayuda completada por Ana",
  );
  expect(
    await resident.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await resident.screenshot({
    path: "../artifacts/relay-resident-mobile.png",
    fullPage: true,
  });
  await resident.close();
});

test("an offline draft survives reload and syncs against its original notice version", async ({
  browser,
  request,
}) => {
  const data = await dashboard(request);
  const record = data.records.find((r) => r.resident.name.startsWith("Luis"));
  const context = await browser.newContext();
  const page = await context.newPage();
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(record.response_url);
  await page.getByRole("button", { name: "English", exact: true }).click();
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await expect
    .poll(() =>
      page.evaluate(() => Boolean(navigator.serviceWorker.controller)),
    )
    .toBeTruthy();
  await context.setOffline(true);
  const originalStep = `I will use the ${data.notice.content.en.next_steps[0]}`;
  await page.locator("#next-step").fill(originalStep);
  await page.getByLabel("Yes, I need a hand", { exact: true }).check();
  await page
    .locator("#assistance-details")
    .fill("Please help me reach the pickup point.");
  await page.locator("#confirm-assistance").check();
  await page
    .getByRole("button", { name: "Save my response", exact: true })
    .click();
  await expect(page.locator("#draft-status")).toHaveText("Not sent");
  await expect(page.locator("#resident-message")).toContainText(
    "will be sent when the connection returns",
  );
  await page.reload();
  await expect(page.locator("#next-step")).toHaveValue(originalStep);
  await expect(page.locator("#draft-status")).toHaveText("Not sent");
  const current = (await dashboard(request)).notice;
  const content = {
    en: {
      text: "The pickup has moved to the south entrance.",
      question: "Which entrance will you use?",
      next_steps: ["south entrance"],
    },
    es: {
      text: "La recogida está ahora en la entrada sur.",
      question: "¿Qué entrada usarás?",
      next_steps: ["entrada sur"],
    },
  };
  const published = await request.post(
    `/api/relay/notices/${current.id}/publish`,
    {
      headers: operator,
      data: {
        idempotency_key: crypto.randomUUID(),
        expected_version: current.version,
        title: current.title,
        content,
        reason: "East entrance unavailable",
        published_by: "E2E coordinator",
      },
    },
  );
  expect(published.ok()).toBeTruthy();
  await context.setOffline(false);
  await expect(page.locator("#resident-message")).toContainText(
    "saved to its original notice version",
  );
  await expect(page.locator("#resident-version")).toHaveText(
    `V${current.version + 1}`,
  );
  await expect(page.locator("#saved-summary")).toContainText(
    `V${current.version}:`,
  );
  await expect(page.locator("#saved-summary")).toContainText(
    "Latest instruction still needs confirmation",
  );
  const saved = (await dashboard(request)).records.find(
    (r) => r.record_id === record.record_id,
  );
  expect(saved.communication_status).toBe(
    "updated_notice_awaiting_confirmation",
  );
  expect(saved.confirmed_version).toBe(current.version);
  expect(saved.assistance.status).toBe("requested");
  await page.reload();
  expect(
    (await dashboard(request)).records.find(
      (r) => r.record_id === record.record_id,
    ).assistance.id,
  ).toBe(saved.assistance.id);
  await context.close();
});

test("mobile coordinator can filter people and record a missed contact without confirming", async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  const layout = await page.evaluate(() => ({
    width: innerWidth,
    scroll: document.documentElement.scrollWidth,
    overflowing: [...document.querySelectorAll("body *")]
      .filter(
        (n) =>
          n.getBoundingClientRect().right > innerWidth &&
          !n.closest(".table-scroll"),
      )
      .map((n) => `${n.tagName}.${n.className}`),
  }));
  expect(layout.scroll, JSON.stringify(layout)).toBeLessThanOrEqual(
    layout.width,
  );
  await page
    .getByRole("button", { name: "Needs follow-up", exact: true })
    .click();
  await page.getByRole("searchbox", { name: "Find a resident" }).fill("Sam");
  await expect(page.locator("#people tr")).toHaveCount(1);
  await page.getByRole("button", { name: "View Sam (demo) record" }).click();
  await page.getByRole("button", { name: "Save attempt" }).click();
  await expect(page.locator("#record-body")).toContainText(
    "Contact attempt: no answer",
  );
  const saved = (await dashboard(request)).records.find((r) =>
    r.resident.name.startsWith("Sam"),
  );
  expect(saved.communication_status).not.toBe("confirmed_current");
  await page.getByRole("button", { name: "Close", exact: true }).last().click();
  await page.getByRole("searchbox", { name: "Find a resident" }).fill("");
  await page.screenshot({
    path: "../artifacts/relay-coordinator-mobile.png",
    fullPage: true,
  });
});

test("retrying after a lost server response keeps one assistance task and one confirmation", async ({
  page,
  request,
}) => {
  const created = await request.post("/api/relay/residents", {
    headers: operator,
    data: {
      idempotency_key: crypto.randomUUID(),
      name: "Retry resident (demo)",
      language: "en",
      opt_in: true,
    },
  });
  expect(created.ok()).toBeTruthy();
  const id = (await created.json()).record_id;
  const resident = (await dashboard(request)).records.find(
    (r) => r.record_id === id,
  );
  await page.goto(resident.response_url);
  await page
    .locator("#next-step")
    .fill(`I will use the ${resident.notice.content.en.next_steps[0]}`);
  await page.getByLabel("Yes, I need a hand", { exact: true }).check();
  await page
    .locator("#assistance-details")
    .fill("Please help me reach the shuttle.");
  await page.locator("#confirm-assistance").check();
  let calls = 0;
  const bodies = [];
  await page.route(`**/api/relay/resident/${id}/response`, async (route) => {
    bodies.push(route.request().postDataJSON());
    if (calls++ === 0) {
      await route.fetch();
      await route.abort("failed");
    } else await route.continue();
  });
  await page
    .getByRole("button", { name: "Save my response", exact: true })
    .click();
  await expect(page.locator("#draft-status")).toHaveText("Not sent");
  await expect(page.locator("#resident-message")).toContainText(
    "not been confirmed by the server",
  );
  const first = (await dashboard(request)).records.find(
    (r) => r.record_id === id,
  );
  await page
    .getByRole("button", { name: "Retry sending", exact: true })
    .click();
  await expect(page.locator("#draft-status")).toHaveText(
    "Saved to your record",
  );
  const second = (await dashboard(request)).records.find(
    (r) => r.record_id === id,
  );
  expect(second.assistance.id).toBe(first.assistance.id);
  expect(second.confirmation_history).toHaveLength(1);
  expect(bodies).toHaveLength(2);
  expect(bodies[0]).toEqual(bodies[1]);
});
