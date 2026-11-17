"""Paired desktop/mobile browser verification against the local Docker app.

Reads the owner token from the ignored env file; never prints it.
"""

import json
import os
from pathlib import Path

from dotenv import dotenv_values
from playwright.sync_api import expect, sync_playwright


def main():
    token = dotenv_values(os.environ.get("TRUSTSQL_SMOKE_TOKEN_FILE", ".env.docker")).get(
        "TRUSTSQL_API_TOKEN", ""
    )
    assert token, "Configure a workspace token in the smoke test's ignored env file"
    output = Path("artifacts/browser")
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(
            os.environ.get("TRUSTSQL_SMOKE_BASE_URL", "http://127.0.0.1:8088"), wait_until="networkidle"
        )
        expect(page.locator("#connection-notice")).to_be_visible()
        expect(page.locator("#connection-settings")).to_have_attribute("open", "")
        expect(page.locator("#global-error")).to_be_hidden()
        expect(page.locator("#run-button")).to_be_disabled()
        page.screenshot(path=str(output / "connection-desktop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        expect(page.get_by_label("Workspace API token")).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(output / "connection-mobile.png"), full_page=True)
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.get_by_label("Workspace API token").fill("synthetic-invalid-token")
        page.get_by_role("button", name="Connect", exact=True).click()
        expect(page.locator("#token-error")).to_contain_text("not accepted")
        expect(page.locator("#api-token")).to_have_attribute("aria-invalid", "true")
        expect(page.locator("#api-token")).to_have_value("")
        page.get_by_label("Workspace API token").fill(token)
        page.get_by_role("button", name="Connect", exact=True).click()
        expect(page.locator("#mode-badge")).to_have_text("Deterministic demo")
        expect(page.locator("#connection-notice")).to_be_hidden()
        expect(page.locator("#token-error")).to_be_hidden()
        page.locator(".connection-settings summary").click()
        page.get_by_label("What would you like to understand?").fill("What was our net revenue last month?")
        page.get_by_role("button", name="Run analysis").click()
        expect(page.locator("#answer-status")).to_have_text("Analysis complete")
        expect(page.locator("#result-table")).to_contain_text("4,96,825.20")
        expect(page.locator("#result-table th")).to_have_text("net revenue (INR)")
        page.get_by_role("tab", name="SQL query").click()
        expect(page.locator("#sql-code")).to_contain_text("refund_totals")
        expect(page.locator("#lineage-table")).to_contain_text("refunds.amount_cents")
        page.get_by_role("tab", name="Execution trace").click()
        expect(page.locator("#trace-list")).to_contain_text("Redacted run record persisted")
        page.get_by_role("tab", name="Results").click()
        page.screenshot(path=str(output / "desktop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
            "Mobile document overflows"
        )
        page.screenshot(path=str(output / "mobile.png"), full_page=True)
        page.get_by_label("What would you like to understand?").fill("What was revenue last month?")
        page.get_by_role("button", name="Run analysis").click()
        expect(page.locator("#answer-status")).to_have_text("Clarification needed")
        page.get_by_role("button", name="Data catalog").click()
        expect(page.locator(".catalog-entry")).to_have_count(6)
        page.locator(".catalog-entry summary").first.click()
        expect(page.locator(".catalog-entry-content").first).to_be_visible()
        page.get_by_role("button", name="Evaluations", exact=True).click()
        evaluation_text = (
            "No evaluation report yet."
            if os.environ.get("TRUSTSQL_SMOKE_EVALUATION", "report") == "empty"
            else "not LLM accuracy"
        )
        expect(page.locator("#evaluation-content")).to_contain_text(evaluation_text)
        page.get_by_role("button", name="Run history").click()
        expect(page.locator("#history-content tbody tr").first).to_be_visible()
        page.get_by_role("button", name="SQL analyst", exact=True).click()
        page.get_by_label("What would you like to understand?").fill(
            "Top five products by gross revenue last month"
        )
        page.get_by_role("button", name="Run analysis").click()
        expect(page.locator("#answer-status")).to_have_text("Analysis complete")
        expect(page.locator("#result-table tbody tr")).to_have_count(5)
        expect(page.locator("#result-chart svg")).to_be_visible()
        page.reload(wait_until="networkidle")
        expect(page.locator("#connection-notice")).to_be_visible()
        expect(page.locator("#api-token")).to_have_value("")
        expect(page.locator("#global-error")).to_be_hidden()
        assert not errors, errors
        browser.close()
    print(
        json.dumps(
            {
                "desktop": "passed",
                "mobile": "passed",
                "query": "passed",
                "clarification": "passed",
                "catalog": "passed",
                "evaluations": "passed",
                "history": "passed",
                "chart": "passed",
                "page_errors": errors,
                "authentication_onboarding": "passed",
            }
        )
    )


if __name__ == "__main__":
    main()
