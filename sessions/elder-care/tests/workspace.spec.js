import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const auth = { Authorization: "Bearer workspace-test-token" };

test.beforeEach(async ({ request }) => {
  const reset = await request.post("/api/demo/reset", { headers: auth });
  expect(reset.ok()).toBeTruthy();
  for (const path of ["/api/demo/seed?mode=crisis", "/api/demo/seed?mode=building", "/api/care/demo"]) {
    const response = await request.post(path, { headers: auth });
    expect(response.ok()).toBeTruthy();
  }
});

async function unlock(page, path = "/") {
  await page.goto(path);
  await page.getByPlaceholder("Operator token").fill("workspace-test-token");
  await page.getByRole("button", { name: "Unlock", exact: true }).click();
  await expect(page.locator("aside").getByRole("button", { name: /^Building/ })).toBeVisible();
}

function sidebar(page, name) {
  return page.locator("aside").getByRole("button", { name: name === "Building" ? /^Building/ : name, exact: true });
}

test("operations remains the default with the original map, lanes, metrics and tools", async ({ page, request }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await unlock(page);
  await expect(page).toHaveURL(/\/ops$/);
  await expect(page.getByRole("heading", { name: /^Live map/ })).toBeVisible();
  await expect(page.locator(".leaflet-container")).toBeVisible();
  await expect(page.getByRole("heading", { name: /Urgent/ }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /Not urgent/ }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Incident card", exact: true })).toBeVisible();
  for (const name of ["Draw zone", "Offline map", /^Take call/, /^Callback/, /^Reviewed/, /^Merge/]) {
    await expect(page.getByRole("button", { name }).first()).toBeVisible();
  }
  await page.getByRole("button", { name: "Offline map", exact: true }).click();
  await expect(page.getByText("Offline outline map · US Census TIGER data")).toBeVisible();
  await page.getByRole("button", { name: "Draw zone", exact: true }).click();
  const map = page.locator(".leaflet-container");
  for (const position of [{x:140,y:100},{x:240,y:100},{x:200,y:180}]) await map.click({position});
  await page.getByRole("button", { name: "Finish", exact: true }).click();
  await page.getByPlaceholder(/Zone name/).fill("Care home evacuation assembly");
  await page.getByRole("button", { name: "Save zone", exact: true }).click();
  await expect(page.locator(".zone-list")).toContainText("Care home evacuation assembly");
  await page.getByRole("button", { name: /P0 Location not given yet.*place on map/ }).click();
  await expect(page.locator(".map-place")).toBeVisible();
  await map.click({position:{x:320,y:210}});
  await expect(page.locator(".map-place")).not.toBeVisible();
  const located = await (await request.get("/api/ops",{headers:auth})).json();
  expect(located.incidents.find((i)=>i.category==="other").lat).not.toBeNull();
  await page.getByRole("button",{name:/^Callback/}).click();
  await expect.poll(async()=>{
    const data = await (await request.get("/api/state",{headers:auth})).json();
    return data.cases.some((c)=>c.type==="callback");
  }).toBeTruthy();
  await page.screenshot({ path: "workspace-test-results/workspace-ops-1440.png", fullPage: true });
  expect(errors).toEqual([]);
});

test("original language controls and wall view remain available", async ({page}) => {
  await unlock(page);
  await page.getByRole("combobox",{name:"Language",exact:true}).selectOption("es");
  await expect(page.getByRole("heading",{name:"Mapa en vivo"})).toBeVisible();
  await page.getByRole("combobox").filter({has:page.locator('option[value="en"]')}).selectOption("en");
  const popupPromise=page.waitForEvent("popup");
  await page.getByRole("link",{name:/Wall view/}).click();
  const wall=await popupPromise;
  // The upstream link uses noreferrer, so a new tab does not inherit the
  // operator token in sessionStorage. Unlock the protected wall view explicitly.
  await wall.getByPlaceholder("Operator token").fill("workspace-test-token");
  await wall.getByRole("button",{name:"Unlock",exact:true}).click();
  await expect(wall.locator(".wall-grid")).toBeVisible();
  await expect(wall.getByRole("heading",{name:/^Live map/})).toBeVisible();
  await wall.close();
});

test("Imaan's building floor plan, assignment, notes and supporter inbox remain usable", async ({ page, request }) => {
  await unlock(page, "/building");
  await expect(page.getByRole("group", { name: /Building floor plan/ })).toBeVisible();
  await page.getByRole("button", { name: /^Unit 2D, floor/ }).click();
  await expect(page.getByRole("heading", { name: /Unit 2D/ })).toBeVisible();
  await page.getByRole("textbox", { name: "Add a note", exact: true }).fill("Care coordinator checked room access.");
  await page.getByRole("button", { name: "Add note", exact: true }).click();
  await expect(page.locator(".timeline")).toContainText("Care coordinator checked room access.");
  await page.getByRole("combobox", { name: "Assign to", exact: true }).selectOption("hvac");
  await expect.poll(async () => {
    const data = await (await request.get("/api/building", {headers:auth})).json();
    return data.tickets.find((t) => t.unit === "2D")?.assignee;
  }).toBe("hvac");
  await sidebar(page, "Supporter inbox").click();
  await expect(page.getByRole("heading", { name: "Supporter inbox", exact: true })).toBeVisible();
  await sidebar(page, "911 operations").click();
  await expect(page.getByRole("heading", { name: /^Live map/ })).toBeVisible();
});

test("resident care lives inside Building with shared sign-in and working care actions", async ({ page, request }) => {
  await unlock(page);
  await sidebar(page, "Building").click();
  await expect(page.locator("aside nav").getByRole("button")).toHaveCount(3);
  await expect(page.locator("aside").getByRole("button", {name:/Resident care/})).toHaveCount(0);
  await expect(page.getByRole("heading", {name:/Resident care at Willow House/})).toBeVisible();
  await page.getByRole("tab", {name:/Resident care/}).click();
  await expect(page).toHaveURL(/\/building\?section=care/);
  await expect(page.getByRole("tab", {name:/Resident care/})).toHaveAttribute("aria-selected", "true");
  const care = page.frameLocator('iframe[title="Resident care workspace"]');
  await expect(care.getByRole("heading", { name: "Care, in good hands." })).toBeVisible();
  await expect(care.getByLabel("Working as staff member")).toBeVisible();
  await care.getByRole("button", {name:"Rooms & repairs",exact:true}).click();
  await expect(care.getByRole("heading", {name:"Resident rooms & shared systems"})).toBeVisible();
  await care.getByLabel("Working as staff member").selectOption("lead-morgan");
  await care.getByRole("button", {name:/^Room 101 Margaret Wilson/}).click();
  await expect(care.getByRole("heading", {name:"Original reports (2)"})).toBeVisible();
  await care.getByText("Call summary & transcript",{exact:true}).first().click();
  await expect(care.getByText("Synthetic demo transcript",{exact:true}).first()).toBeVisible();
  await care.getByRole("button", {name:"Assign facilities / vendor",exact:true}).click();
  await care.getByRole("combobox", {name:"Assigned team member or vendor"}).selectOption("facilities-alex");
  await care.getByRole("button", {name:"Save assignment",exact:true}).click();
  await expect(care.getByRole("dialog")).not.toBeVisible();
  const data = await (await request.get("/api/care/state",{headers:auth})).json();
  expect(data.facility_workflow.tickets.find((t)=>t.unit==="101").assignee).toBe("facilities-alex");
  await page.screenshot({ path: "workspace-test-results/workspace-care-1440.png", fullPage: true });
  const accessibility = await new AxeBuilder({page}).include("iframe").analyze();
  expect(accessibility.violations).toEqual([]);
  await sidebar(page,"911 operations").click();
  await expect(page.getByRole("heading", {name:/^Live map/})).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", {name:/^Live map/})).toBeVisible();
});

test("direct care links and mobile navigation preserve operations and all care sections", async ({page}) => {
  await page.setViewportSize({width:390,height:844});
  await unlock(page,"/care");
  await expect(page).toHaveURL(/\/building\?section=care/);
  await expect(page.locator("aside nav").getByRole("button")).toHaveCount(3);
  const care = page.frameLocator('iframe[title="Resident care workspace"]');
  await expect(care.getByRole("heading",{name:"Care, in good hands."})).toBeVisible();
  await care.getByRole("button",{name:"Residents & check-ins",exact:true}).click();
  await expect(care.getByRole("heading",{name:"A little attention. Every day."})).toBeVisible();
  await page.screenshot({path:"workspace-test-results/workspace-care-390.png",fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  await sidebar(page,"911 operations").click();
  await expect(page.getByRole("heading",{name:/^Live map/})).toBeVisible();
  await page.screenshot({path:"workspace-test-results/workspace-ops-390.png",fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  await sidebar(page,"Building").click();
  await expect(page.getByRole("group",{name:/Building floor plan/})).toBeVisible();
});


test("Building care shortcuts, keyboard tabs and drafts survive switching to the floor plan", async ({page}) => {
  await unlock(page,"/building");
  await expect(page.getByRole("group",{name:/Building floor plan/})).toBeVisible();
  const accessibility = await new AxeBuilder({page}).include(".building-care-summary").include(".building-tabs").analyze();
  expect(accessibility.violations).toEqual([]);
  await page.screenshot({path:"workspace-test-results/building-overview-1440.png",fullPage:true});
  await page.getByRole("button",{name:/^Urgent care/}).click();
  const care = page.frameLocator('iframe[title="Resident care workspace"]');
  await expect(care.getByRole("heading",{name:"Every urgent need, seen."})).toBeVisible();
  await expect(page).toHaveURL(/careView=urgent/);
  await page.getByRole("tab",{name:/Resident care/}).focus();
  await page.keyboard.press("ArrowLeft");
  await expect(page.getByRole("tab",{name:"Repairs & floor plan"})).toHaveAttribute("aria-selected","true");
  await expect(page.getByRole("group",{name:/Building floor plan/})).toBeVisible();
  await page.keyboard.press("ArrowRight");
  await expect(care.getByRole("heading",{name:"Every urgent need, seen."})).toBeVisible();
  await care.getByRole("button",{name:"Add note",exact:true}).click();
  await care.getByLabel("Handoff note",{exact:true}).fill("Please confirm Margaret is comfortable after the repair.");
  await page.getByRole("tab",{name:"Repairs & floor plan"}).click();
  await page.getByRole("tab",{name:/Resident care/}).click();
  await expect(care.getByLabel("Handoff note",{exact:true})).toHaveValue("Please confirm Margaret is comfortable after the repair.");
  await care.getByRole("button",{name:"Close dialog",exact:true}).click();
  await care.getByRole("button",{name:"Residents & check-ins",exact:true}).click();
  await page.getByRole("tab",{name:"Repairs & floor plan"}).click();
  await page.getByRole("tab",{name:/Resident care/}).click();
  await expect(care.getByRole("heading",{name:"A little attention. Every day."})).toBeVisible();
  await page.getByRole("tab",{name:"Repairs & floor plan"}).click();
  await page.getByRole("button",{name:/^Care-home repairs/}).click();
  await expect(care.getByRole("heading",{name:"Resident rooms & shared systems"})).toBeVisible();
  await page.reload();
  await expect(care.getByRole("heading",{name:"Resident rooms & shared systems"})).toBeVisible();
});
