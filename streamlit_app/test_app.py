import asyncio
from playwright.async_api import async_playwright

async def main():
    errors = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        await page.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        async def screenshot(name):
            await page.screenshot(path=f"/home/claude/shot_{name}.png")

        # 1. Overview page loads
        title = await page.text_content("h1")
        print("Overview title:", title)
        await screenshot("01_overview")

        # 2. Paper selection - check selectbox exists
        print("Paper selector present:", await page.locator("text=Paper").count() > 0)

        # 3. Navigate to Document page
        await page.get_by_role("button", name="Document", exact=True).click()
        await page.wait_for_timeout(1000)
        assert await page.locator("text=⟦b:0006⟧").count() > 0
        print("Document page OK, anchors visible")
        await screenshot("02_document")

        # 4. Navigate to Citation page
        await page.get_by_role("button", name="Citation", exact=True).click()
        await page.wait_for_timeout(1000)
        assert await page.locator("text=citation-1").count() > 0
        print("Citation page loaded")
        await screenshot("03_citation")

        # 5. Click "View source" for a field
        view_source_btns = page.get_by_role("button", name="View source")
        count = await view_source_btns.count()
        print("View source buttons:", count)
        if count > 0:
            await view_source_btns.first.click()
            await page.wait_for_timeout(1000)
            assert await page.locator("text=Provenance").count() > 0
            print("Provenance panel opened OK")
            await screenshot("04_provenance")

        # 6. Click Edit on citation record
        edit_btns = page.get_by_role("button", name="Edit", exact=True)
        if await edit_btns.count() > 0:
            await edit_btns.first.click()
            await page.wait_for_timeout(1000)
            assert await page.locator("text=Save changes").count() > 0
            print("Edit mode OK")
            await screenshot("05_edit_mode")
            # Cancel
            cancel_btn = page.get_by_role("button", name="Cancel")
            if await cancel_btn.count() > 0:
                await cancel_btn.first.click()
                await page.wait_for_timeout(1000)
                print("Cancel edit OK")

        # 7. Click Accept on citation record
        accept_btns = page.get_by_role("button", name="Accept", exact=True)
        if await accept_btns.count() > 0:
            await accept_btns.first.click()
            await page.wait_for_timeout(1000)
            assert await page.locator("text=ACCEPTED").count() > 0
            print("Accept action OK - status changed")
            await screenshot("06_accepted")

        # 8. Navigate to Unresolved page
        await page.get_by_role("button", name="Unresolved", exact=True).click()
        await page.wait_for_timeout(1000)
        assert await page.locator("text=Unresolved Items").count() > 0
        print("Unresolved page OK")
        await screenshot("07_unresolved")

        # 9. Navigate to Final Review
        await page.get_by_role("button", name="Final Review", exact=True).click()
        await page.wait_for_timeout(1000)
        assert await page.locator("text=Final Review").count() > 0
        print("Final Review page OK")
        await screenshot("08_final_review")

        # 10. Click Commit Dataset
        commit_btn = page.get_by_role("button", name="Commit Dataset")
        if await commit_btn.count() > 0:
            await commit_btn.first.click()
            await page.wait_for_timeout(1000)
            assert await page.locator("text=prototype").count() > 0
            print("Commit Dataset mock message OK")
            await screenshot("09_commit")

        # 11. Navigate to Treatments (test relationships / multi record)
        await page.get_by_role("button", name="Treatments", exact=True).click()
        await page.wait_for_timeout(1000)
        assert await page.locator("text=treatment-1").count() > 0
        print("Treatments page OK")

        await browser.close()

    print("\n=== Console errors captured ===")
    for e in errors:
        print(e)
    print("=== END ===")

asyncio.run(main())