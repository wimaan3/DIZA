"""Exercise operator login against the real local backend without printing tokens."""

import argparse
import asyncio
import os
import sys
from pathlib import Path

import httpx
from playwright.async_api import async_playwright, expect

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "agents"))
from retell_api import load_dotenv


async def check(base_url, artifacts):
    load_dotenv()
    token = os.environ.get("OPS_API_TOKEN", "")
    if not token:
        raise SystemExit("Configure OPS_API_TOKEN in the root .env first.")
    async with httpx.AsyncClient(base_url=base_url, timeout=10) as client:
        assert (await client.get("/api/state")).status_code == 401
        assert (await client.get("/api/state", headers={"Authorization": "Bearer wrong"})).status_code == 401
        assert (await client.get("/api/state", headers={"Authorization": "Bearer " + token})).status_code == 200

    async with async_playwright() as play:
        options = {"headless": True}
        if executable := os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"):
            options["executable_path"] = executable
        browser = await play.chromium.launch(**options)
        for label, pasted in (
            ("token value", token),
            ("copied env line", "OPS_API_TOKEN=" + token),
            ("quoted env line with spaces", "  OPS_API_TOKEN = '" + token + "'  "),
        ):
            context = await browser.new_context(viewport={"width": 1440, "height": 1050})
            page = await context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.goto(base_url + "/ops", wait_until="domcontentloaded")
            await expect(page.get_by_role("alert")).to_contain_text("Enter the operator token")
            await page.get_by_label("Operator token", exact=True).fill(pasted)
            await page.get_by_role("button", name="Connect", exact=True).click()
            await expect(page.get_by_text("Local backend connected", exact=False)).to_be_visible()
            await expect(page.get_by_role("alert")).to_have_count(0)
            await expect(page.locator("button.report").first).to_be_visible()
            await page.reload(wait_until="domcontentloaded")
            await expect(page.get_by_text("Local backend connected", exact=False)).to_be_visible()
            await expect(page.get_by_role("alert")).to_have_count(0)
            assert not errors, errors
            if artifacts and label == "token value":
                artifacts.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(artifacts / "desktop-after.png"), full_page=True)
            print("PASS:", label, "connects cleanly and survives reload")
            await context.close()

        context = await browser.new_context(viewport={"width": 390, "height": 844})
        page = await context.new_page()
        submitted_credentials = []
        page.on("request", lambda request: submitted_credentials.append(request.headers.get("authorization")) if request.url.endswith("/api/state") else None)
        await page.goto(base_url + "/ops", wait_until="domcontentloaded")
        await expect(page.get_by_role("alert")).to_contain_text("Enter the operator token")
        field = page.get_by_label("Operator token", exact=True)
        await field.fill("wrong-token")
        assert "Bearer wrong-token" not in submitted_credentials
        await page.get_by_role("button", name="Connect", exact=True).click()
        await expect(page.get_by_role("alert")).to_contain_text("was not accepted")
        await expect(page.locator("button.report")).to_have_count(0)
        assert not await page.evaluate("document.documentElement.scrollWidth > innerWidth")
        if artifacts:
            await page.screenshot(path=str(artifacts / "mobile-login.png"), full_page=True)
        await field.fill(token)
        await field.press("Enter")
        await expect(page.get_by_label("Operator token", exact=True)).to_have_count(0)
        await expect(page.locator("button.report").first).to_be_visible()
        await expect(page.get_by_role("alert")).to_have_count(0)
        assert not await page.evaluate("document.documentElement.scrollWidth > innerWidth")
        if artifacts:
            await page.screenshot(path=str(artifacts / "mobile-after.png"), full_page=True)
        print("PASS: incorrect token stays blocked; Enter reconnects with the correct token on mobile")
        await context.close()

        # Delay the initial unauthorized response until after a successful login.
        context = await browser.new_context()
        page = await context.new_page()
        initial_started = asyncio.Event()
        release_initial = asyncio.Event()
        initial_finished = asyncio.Event()

        async def delay_initial(route):
            if route.request.headers.get("authorization"):
                await route.continue_()
                return
            response = await route.fetch()
            initial_started.set()
            await release_initial.wait()
            try:
                await route.fulfill(response=response)
            finally:
                initial_finished.set()

        await context.route("**/api/state", delay_initial)
        await page.goto(base_url + "/ops", wait_until="domcontentloaded")
        await asyncio.wait_for(initial_started.wait(), timeout=10)
        await page.get_by_label("Operator token", exact=True).fill(token)
        await page.get_by_role("button", name="Connect", exact=True).click()
        await expect(page.get_by_text("Local backend connected", exact=False)).to_be_visible()
        release_initial.set()
        await asyncio.wait_for(initial_finished.wait(), timeout=10)
        await expect(page.get_by_role("alert")).to_have_count(0)
        await expect(page.get_by_text("Local backend connected", exact=False)).to_be_visible()
        print("PASS: a late unauthorized response cannot undo a successful connection")
        await context.close()
        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()
    asyncio.run(check(args.base_url.rstrip("/"), args.artifacts))
