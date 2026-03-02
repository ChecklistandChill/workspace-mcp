"""
Checklist & Chill — Gumroad Product Listings Creator

Pulls the three free product PDFs from the Google Drive 'products' folder and
creates (or updates) their listings in the connected Gumroad store.

Usage:
    GUMROAD_ACCESS_TOKEN=<your_token> python -m gumroad.create_listings

Products created:
  1. product-freebie-chapter-1          → Chapter 1 free lead-magnet
  2. product-homeownership-readiness-checklist → Homeowner Readiness Checklist Pack
  3. product-rent-vs-buy-snapshot       → Rent vs. Buy Snapshot
"""

import asyncio
import logging
import os

import httpx

logger = logging.getLogger(__name__)

GUMROAD_API_BASE = "https://api.gumroad.com/v2"

# ---------------------------------------------------------------------------
# Product definitions
# Google Drive file IDs come from the 'products' folder
# (folder ID: 1UJLPz5-xG-Es38rh1oJU68s9a3LOyGNE)
# ---------------------------------------------------------------------------
PRODUCTS = [
    {
        "drive_file_id": "1Xy12--WrU3KX3nHurGJN6M99I4s0y0IC",
        "name": "Is Homeownership Right for You? (Free Chapter 1)",
        "price": 0,
        "url_slug": "checklist-and-chill-chapter-1-free",
        "description": """<h2>Your homebuying journey starts here — and it's completely free.</h2>

<p>Chapter 1 of the <strong>Checklist & Chill Homebuyer Guide</strong> walks you through the very first question every aspiring homeowner faces: <em>Is now actually the right time for me to buy?</em></p>

<p>Written in plain English — no jargon, no pressure — this chapter helps you cut through the noise and figure out where you really stand before you ever talk to a lender or tour a single home.</p>

<h3>What's inside:</h3>
<ul>
  <li>The honest questions to ask yourself before starting the homebuying process</li>
  <li>How to separate emotional readiness from financial readiness</li>
  <li>A clear-eyed look at what the homebuying process actually involves (so nothing surprises you later)</li>
  <li>How this guide is structured — and how to use it to build real confidence, one chapter at a time</li>
</ul>

<p>This is the foundation chapter. Everything that comes next — the money prep, the mortgage math, the house hunt — makes a lot more sense once you've worked through this first.</p>

<p><strong>100% free. No catch.</strong> Just download, read at your own pace, and decide if homeownership is the next move for you.</p>

<p><em>From Checklist & Chill — calm, practical homebuying guidance for real people.</em></p>""",
    },
    {
        "drive_file_id": "1CYauIMAFsYuoyG4CxPuYnxSukZwroTCh",
        "name": "Homeowner Readiness Checklist Pack",
        "price": 0,
        "url_slug": "homeowner-readiness-checklist-pack",
        "description": """<h2>Stop guessing. Start knowing exactly where you stand.</h2>

<p>The <strong>Homeowner Readiness Checklist Pack</strong> from Checklist & Chill is a practical, fillable PDF toolkit designed to help first-time homebuyers get organized, get clear, and move forward with confidence.</p>

<p>This isn't a vague to-do list. Every worksheet targets a real sticking point in the homebuying process — the stuff that trips people up before they even get to the house-hunting stage.</p>

<h3>What's included:</h3>
<ul>
  <li><strong>Cash to Close Snapshot</strong> — Map out exactly how much cash you need: down payment, closing costs, upfront expenses, and your post-move cushion</li>
  <li><strong>DTI Cheat Sheet</strong> — Calculate your debt-to-income ratio and see how your current debts affect how much home you can qualify for</li>
  <li><strong>Homeownership Readiness Checklist</strong> — A step-by-step checklist covering financial prep, credit, savings, and next steps</li>
  <li><strong>Bonus reference materials</strong> — Key terms defined simply so you're never lost in a lender conversation</li>
</ul>

<h3>Perfect for you if:</h3>
<ul>
  <li>You're 6–18 months away from wanting to buy and want to get ahead of the prep</li>
  <li>You're not sure how much you actually need saved (hint: it's more than just the down payment)</li>
  <li>You want a clear picture of your financial position before talking to a lender</li>
  <li>You're a visual person who thinks better when things are written down</li>
</ul>

<p>Works perfectly alongside the <em>Checklist & Chill Homebuyer Guide</em> — but the worksheets are useful on their own too.</p>

<p><strong>Free to download. Yours to keep.</strong></p>

<p><em>From Checklist & Chill — calm, practical homebuying guidance for real people.</em></p>""",
    },
    {
        "drive_file_id": "11lbR9vGBoMPouEEWFmCLfsLOiK64mRzP",
        "name": "Rent vs. Buy Snapshot",
        "price": 0,
        "url_slug": "rent-vs-buy-snapshot",
        "description": """<h2>One page. One decision. Total clarity.</h2>

<p>The <strong>Rent vs. Buy Snapshot</strong> is a clean, no-fluff one-page reference from Checklist & Chill that helps you quickly compare where you stand — financially and practically — on the rent vs. buy question.</p>

<p>Because the real answer isn't "buying is always better" or "renting is throwing money away." The real answer depends on <em>your</em> numbers, <em>your</em> timeline, and <em>your</em> life — and this snapshot helps you see that clearly.</p>

<h3>What it covers:</h3>
<ul>
  <li>The key financial factors that actually tip the scale toward buying vs. renting</li>
  <li>The break-even framework — how long you'd need to stay to make buying worth it</li>
  <li>Hidden costs of both renting and owning that most comparisons skip</li>
  <li>A simple self-assessment so you can honestly evaluate your own situation</li>
</ul>

<h3>Use it to:</h3>
<ul>
  <li>Cut through the noise when family and friends all have different opinions</li>
  <li>Ground a conversation with your partner about your actual options</li>
  <li>Figure out if now is the right time — or if waiting makes more financial sense</li>
</ul>

<p>Quick to read. Easy to reference. Built for the early stage of the decision — before you're deep in mortgage math or house tours.</p>

<p><strong>Free download. No email required.</strong></p>

<p><em>From Checklist & Chill — calm, practical homebuying guidance for real people.</em></p>""",
    },
]


def _get_access_token() -> str:
    token = os.environ.get("GUMROAD_ACCESS_TOKEN")
    if not token:
        raise ValueError(
            "GUMROAD_ACCESS_TOKEN environment variable not set. "
            "Get your token from https://app.gumroad.com/settings/advanced"
        )
    return token


async def create_or_update_product(client: httpx.AsyncClient, token: str, product: dict) -> dict:
    """Create a product on Gumroad. Returns the created product dict."""
    form_data = {
        "access_token": token,
        "name": product["name"],
        "price": str(product["price"]),
        "description": product["description"],
        "url": product["url_slug"],
    }

    response = await client.post(
        f"{GUMROAD_API_BASE}/products",
        data=form_data,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    if not data.get("success"):
        raise RuntimeError(f"Gumroad API error: {data.get('message', 'Unknown error')}")

    return data["product"]


async def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    token = _get_access_token()

    logger.info("Creating %d Gumroad product listings for Checklist & Chill…", len(PRODUCTS))

    async with httpx.AsyncClient() as client:
        for product in PRODUCTS:
            logger.info("Creating: %s", product["name"])
            try:
                result = await create_or_update_product(client, token, product)
                price_display = "Free" if result.get("price", 0) == 0 else f"${result['price'] / 100:.2f}"
                logger.info(
                    "  ✓ Created | ID: %s | Price: %s | URL: %s",
                    result.get("id"),
                    price_display,
                    result.get("short_url", result.get("url", "N/A")),
                )
            except Exception as e:
                logger.error("  ✗ Failed to create '%s': %s", product["name"], e)

    logger.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())
