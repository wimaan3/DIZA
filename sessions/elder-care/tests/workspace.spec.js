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

test("Imaan's apartment floor plan and repair tools remain available for that building", async ({page,request}) => {
  await unlock(page,"/building");
  await page.getByLabel("Building",{exact:true}).selectOption("apartments");
  await expect(page.getByRole("group",{name:/Building floor plan/})).toBeVisible();
  await page.getByRole("button",{name:/^Unit 2D, floor/}).click();
  await page.getByRole("textbox",{name:"Add a note",exact:true}).fill("Care coordinator checked room access.");
  await page.getByRole("button",{name:"Add note",exact:true}).click();
  await expect(page.locator(".timeline")).toContainText("Care coordinator checked room access.");
  await page.getByRole("combobox",{name:"Assign to",exact:true}).selectOption("hvac");
  await expect.poll(async()=>{
    const data=await(await request.get("/api/building",{headers:auth})).json();
    return data.tickets.find((ticket)=>ticket.unit==="2D")?.assignee;
  }).toBe("hvac");
  await sidebar(page,"Supporter inbox").click();
  await expect(page.getByRole("heading",{name:"Supporter inbox",exact:true})).toBeVisible();
});

function building(page) {return page.frameLocator('iframe[title="Building workspace"]');}

test("Building has one floor plan, mixed queue and detail pane for care and repairs", async ({page,request}) => {
  await unlock(page,"/building");
  const home=building(page);
  await expect(page.getByRole("tab")).toHaveCount(0);
  await expect(home.getByRole("tab")).toHaveCount(0);
  await expect(page.locator("aside nav button")).toHaveCount(3);
  await expect(home.getByRole("group",{name:/Building floor plan/})).toBeVisible();
  await expect(home.getByRole("heading",{name:"Resident check-ins",exact:true})).toBeVisible();
  await expect(home.getByRole("heading",{name:/Building work queue/})).toBeVisible();
  await expect(home.locator(".request-list").getByText("Care request",{exact:true}).first()).toBeVisible();
  await expect(home.locator(".request-list").getByText("Repair incident",{exact:true}).first()).toBeVisible();
  await page.screenshot({path:"workspace-test-results/unified-building-1440.png",fullPage:true});
  await home.getByRole("button",{name:/^Room 101, Margaret Wilson/}).click();
  await expect(home.locator(".room-filter")).toContainText("Room 101");
  const state=await(await request.get("/api/care/state",{headers:auth})).json();
  const ticket=state.facility_workflow.tickets.find((item)=>item.unit==="101"&&!item.merged_into);
  await home.locator(`[data-building-item="repair:${ticket.code}"]`).click();
  await expect(home.getByRole("heading",{name:"Original reports (2)"})).toBeVisible();
  await home.getByText("Call summary & transcript",{exact:true}).first().click();
  await expect(home.getByText("Synthetic demo transcript",{exact:true}).first()).toBeVisible();
  await home.getByLabel("Working as staff member").selectOption("lead-morgan");
  await home.getByRole("button",{name:"Assign facilities / vendor",exact:true}).click();
  await home.getByRole("combobox",{name:"Assigned team member or vendor"}).selectOption("facilities-alex");
  await home.getByRole("button",{name:"Save assignment",exact:true}).click();
  await expect(home.getByRole("dialog")).not.toBeVisible();
  await home.locator(".related-care-link").first().click();
  await expect(home.getByRole("heading",{name:"Margaret Wilson",exact:true})).toBeVisible();
  await expect(home.getByRole("group",{name:/Building floor plan/})).toBeVisible();
  await home.getByRole("button",{name:new RegExp(`^Open ${ticket.code}`)}).click();
  await expect(home.getByRole("heading",{name:"Original reports (2)"})).toBeVisible();
  await expect(home.getByRole("heading",{name:/Building work queue/})).toBeVisible();
  const after=await(await request.get("/api/care/state",{headers:auth})).json();
  expect(after.facility_workflow.tickets.find((item)=>item.code===ticket.code).assignee).toBe("facilities-alex");
});

test("old care links open the merged screen and check-ins create work in the same queue", async ({page,request}) => {
  await page.setViewportSize({width:390,height:844});
  await unlock(page,"/care");
  await expect(page).toHaveURL(/\/building$/);
  const home=building(page);
  await expect(home.getByRole("group",{name:/Building floor plan/})).toBeVisible();
  await home.getByRole("button",{name:"Record check-in for George Park",exact:true}).click();
  await home.getByLabel("Check-in outcome").selectOption("follow_up");
  await home.getByLabel("Observation").fill("Please check that George is comfortable after breakfast.");
  await home.getByRole("button",{name:"Save check-in",exact:true}).click();
  await expect(home.getByRole("dialog")).not.toBeVisible();
  await expect(home.locator(".combined-checkin-row").filter({hasText:"George Park"})).toContainText("Follow-up requested");
  const data=await(await request.get("/api/care/state",{headers:auth})).json();
  expect(data.requests.some((item)=>item.resident_id==="r4"&&item.category==="wellbeing")).toBeTruthy();
  await home.getByLabel("Search building work",{exact:true}).fill("George Park");
  await expect(home.locator(".request-list")).toContainText("Wellbeing");
  await page.screenshot({path:"workspace-test-results/unified-building-390.png",fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  expect(await home.locator("html").evaluate((element)=>element.scrollWidth<=element.clientWidth)).toBeTruthy();
  await sidebar(page,"911 operations").click();
  await expect(page.getByRole("heading",{name:/^Live map/})).toBeVisible();
});

test("care lifecycle, keyboard queue navigation and unsaved notes work in the merged building", async ({page,request}) => {
  const summary=`Company by the garden ${Date.now()}`;
  const result=await request.post("/api/care/requests",{headers:auth,data:{idempotency_key:summary,resident_id:"r6",category:"companionship",summary,reported_by:"Demo staff"}});
  expect(result.ok()).toBeTruthy();
  const item=await result.json();
  await unlock(page,"/building");
  const home=building(page);
  await home.getByLabel("Search building work",{exact:true}).fill(summary);
  await home.getByRole("button",{name:"Add note",exact:true}).click();
  await home.getByLabel("Handoff note",{exact:true}).fill("Offer a seat in the garden.");
  await page.getByLabel("Building",{exact:true}).selectOption("apartments");
  await page.getByLabel("Building",{exact:true}).selectOption("care-home");
  await expect(home.getByLabel("Handoff note",{exact:true})).toHaveValue("Offer a seat in the garden.");
  await home.getByRole("button",{name:"Save note",exact:true}).click();
  await home.getByRole("button",{name:"Accept responsibility",exact:true}).click();
  await home.getByRole("button",{name:"Start care",exact:true}).click();
  await home.getByRole("button",{name:"Record outcome & resolve",exact:true}).click();
  await home.getByLabel("Outcome and follow-up").fill("Resident enjoyed a conversation in the garden.");
  await home.getByRole("button",{name:"Resolve request",exact:true}).click();
  await expect(home.getByRole("dialog")).not.toBeVisible();
  await home.getByRole("button",{name:"Completed",exact:true}).click();
  await expect(home.locator(".request-list")).toContainText(summary);
  const state=await(await request.get("/api/care/state",{headers:auth})).json();
  expect(state.requests.find((record)=>record.id===item.id).status).toBe("resolved");
  await home.getByLabel("Search building work",{exact:true}).fill("");
  await home.getByRole("button",{name:"All open",exact:true}).click();
  const before=await home.locator('.request-list [aria-pressed="true"]').getAttribute("data-request");
  await home.locator("body").press("j");
  const after=await home.locator('.request-list [aria-pressed="true"]').getAttribute("data-request");
  expect(after).not.toBe(before);
});

test("the unified building is accessible on desktop and mobile, including room editing", async ({page}) => {
  await unlock(page,"/building");
  const home=building(page);
  await expect(home.getByRole("group",{name:/Building floor plan/})).toBeVisible();
  let audit=await new AxeBuilder({page}).include("iframe").analyze();
  expect(audit.violations).toEqual([]);
  await home.getByLabel("Working as staff member").selectOption("lead-morgan");
  await home.getByRole("button",{name:"Edit room 101",exact:true}).click();
  await expect(home.getByRole("dialog")).toBeVisible();
  await home.getByLabel("Shared riser").fill("R1");
  await home.getByRole("button",{name:"Save room",exact:true}).click();
  await expect(home.getByRole("dialog")).not.toBeVisible();
  await page.setViewportSize({width:390,height:844});
  audit=await new AxeBuilder({page}).include("iframe").analyze();
  expect(audit.violations).toEqual([]);
});


test("one maintenance report appears as linked care and repair work, with independent outcomes", async ({page,request}) => {
  await unlock(page,"/building");
  const home=building(page),summary=`Reading light needs replacement ${Date.now()}`;
  await home.getByLabel("Working as staff member").selectOption("lead-morgan");
  await home.getByRole("button",{name:"Record a request",exact:true}).click();
  await home.getByRole("combobox",{name:"Resident",exact:true}).selectOption("r6");
  await home.getByRole("combobox",{name:"Type of request",exact:true}).selectOption("maintenance");
  await home.getByRole("combobox",{name:"Room issue type",exact:true}).selectOption("appliance");
  await home.getByLabel("What is needed?").fill(summary);
  await home.getByRole("button",{name:"Record request",exact:true}).click();
  await expect(home.getByRole("dialog")).not.toBeVisible();
  await home.getByLabel("Search building work",{exact:true}).fill(summary);
  await expect(home.locator(".request-list .request-card")).toHaveCount(2);
  const data=await(await request.get("/api/care/state",{headers:auth})).json();
  const care=data.requests.find((item)=>item.summary===summary);
  await home.locator(`[data-building-item="repair:${care.facility_code}"]`).click();
  await home.getByRole("button",{name:"Assign facilities / vendor",exact:true}).click();
  await home.getByRole("combobox",{name:"Assigned team member or vendor"}).selectOption("facilities-alex");
  await home.getByRole("button",{name:"Save assignment",exact:true}).click();
  await home.getByRole("button",{name:"Start repair",exact:true}).click();
  await home.getByRole("button",{name:"Record repair outcome",exact:true}).click();
  await home.getByLabel("Repair outcome",{exact:true}).fill("Replaced the light and checked it with the resident.");
  await home.getByRole("button",{name:"Close repair",exact:true}).click();
  await expect(home.getByRole("dialog")).not.toBeVisible();
  await expect(home.locator(".request-list .request-card")).toHaveCount(1);
  await expect(home.locator(".request-list")).toContainText("Care request");
  const after=await(await request.get("/api/care/state",{headers:auth})).json();
  expect(after.requests.find((item)=>item.id===care.id).status).toBe("new");
  expect(after.facility_workflow.tickets.find((item)=>item.code===care.facility_code).status).toBe("closed");
});
