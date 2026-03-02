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
        "name": "The Homebuyer Guide — Chapter 1 (Free)",
        "price": 0,
        "url_slug": "checklist-and-chill-chapter-1-free",
        "description": (
            "<p>Buying a home is one of the biggest financial decisions most people "
            "make. And most of the stress doesn't come from the process itself — it "
            "comes from not knowing what the process actually looks like before "
            "you're in the middle of it.</p>"
            "\n\n"
            "<p>This is Chapter 1 of the Checklist &amp; Chill Homebuyer Guide. "
            "It covers the very first question: <em>should I even be thinking about "
            "buying right now?</em></p>"
            "\n\n"
            "<p>No scare tactics. No pressure. Just a calm, structured starting "
            "point.</p>"
            "\n\n"
            "<h3>What's inside</h3>"
            "<ul>"
            "<li>How to tell the difference between emotional readiness and "
            "financial readiness (they're not the same thing)</li>"
            "<li>The real timeline of a home purchase — so you know what you're "
            "actually signing up for</li>"
            "<li>Honest questions to sit with before you talk to a lender or "
            "start browsing listings</li>"
            "<li>How the rest of the guide is structured, so you can decide if "
            "it's worth continuing</li>"
            "</ul>"
            "\n\n"
            "<p>This works because it gives you one clear place to start — "
            "instead of 47 browser tabs and conflicting advice from everyone "
            "you know.</p>"
            "\n\n"
            "<p>You don't have to do this perfectly. You just have to start "
            "with the right questions.</p>"
            "\n\n"
            "<p><strong>Free. No email required.</strong></p>"
            "\n\n"
            "<p><em>Clinician-designed structure. Real-world application. "
            "Built by a Board-Certified Music Therapist (MT-BC) using principles "
            "from behavioral science and cognitive accessibility design — "
            "translated into practical, step-by-step tools for first-time "
            "homebuyers.</em></p>"
            "\n\n"
            "<p><em>Checklist &amp; Chill provides educational materials only "
            "and does not offer medical, mental health, legal, or financial "
            "advice.</em></p>"
        ),
    },
    {
        "drive_file_id": "1CYauIMAFsYuoyG4CxPuYnxSukZwroTCh",
        "name": "Homeowner Readiness Checklist Pack",
        "price": 0,
        "url_slug": "homeowner-readiness-checklist-pack",
        "description": (
            "<p>Before you talk to a lender, before you tour a single house — "
            "there's a layer of prep that most first-time buyers skip. Not because "
            "they don't care, but because nobody told them it existed.</p>"
            "\n\n"
            "<p>The Homeowner Readiness Checklist Pack is a set of fillable PDF "
            "worksheets that help you see your financial picture clearly before "
            "you're under pressure to make decisions fast.</p>"
            "\n\n"
            "<p>Think of it as an external brain for the money side of buying "
            "a home. Everything laid out. Nothing left floating in your head.</p>"
            "\n\n"
            "<h3>What's in the pack</h3>"
            "<ul>"
            "<li><strong>Cash to Close Snapshot</strong> — Map out your real "
            "numbers: down payment, closing costs, move-in expenses, and the "
            "post-close cushion most people forget about</li>"
            "<li><strong>DTI Cheat Sheet</strong> — Your debt-to-income ratio "
            "is one of the first things a lender checks. This worksheet helps "
            "you calculate yours before they do</li>"
            "<li><strong>Homeownership Readiness Checklist</strong> — A "
            "step-by-step walkthrough of financial prep, credit, savings targets, "
            "and the order to do them in</li>"
            "<li><strong>Key terms reference</strong> — Plain-language definitions "
            "so you're not Googling mid-conversation with your loan officer</li>"
            "</ul>"
            "\n\n"
            "<h3>Good fit if</h3>"
            "<ul>"
            "<li>You're somewhere in the 6–18 month window before buying and "
            "want to get ahead of the prep</li>"
            "<li>You're not sure how much you actually need saved (it's more "
            "than the down payment — the worksheets show you the full picture)</li>"
            "<li>Your brain works better when things are written down and "
            "visible, not floating around as mental to-do items</li>"
            "</ul>"
            "\n\n"
            "<p>This works because it externalizes the decisions. Your brain "
            "doesn't have to hold everything at once — the worksheets hold it "
            "for you.</p>"
            "\n\n"
            "<p>Works alongside the Checklist &amp; Chill Homebuyer Guide, "
            "but the pack stands on its own too.</p>"
            "\n\n"
            "<p><strong>Free. Yours to keep.</strong></p>"
            "\n\n"
            "<p><em>Clinician-designed structure. Real-world application. "
            "Built by a Board-Certified Music Therapist (MT-BC) using principles "
            "from behavioral science and cognitive accessibility design — "
            "translated into practical decision-support tools for first-time "
            "homebuyers.</em></p>"
            "\n\n"
            "<p><em>Checklist &amp; Chill provides educational materials only "
            "and does not offer medical, mental health, legal, or financial "
            "advice.</em></p>"
        ),
    },
    {
        "drive_file_id": "11lbR9vGBoMPouEEWFmCLfsLOiK64mRzP",
        "name": "Rent vs. Buy Snapshot",
        "price": 0,
        "url_slug": "rent-vs-buy-snapshot",
        "description": (
            "<p>\"Should I rent or buy?\" is one of those questions where "
            "everyone has an opinion — and most of those opinions leave out "
            "the parts that actually matter for your situation.</p>"
            "\n\n"
            "<p>The Rent vs. Buy Snapshot is a one-page reference that helps "
            "you compare the two options using your real numbers, your real "
            "timeline, and your real life — not someone else's.</p>"
            "\n\n"
            "<p>Because the honest answer isn't always \"buy.\" Sometimes "
            "renting is the smarter move. This snapshot helps you see which "
            "one it is right now, for you.</p>"
            "\n\n"
            "<h3>What it covers</h3>"
            "<ul>"
            "<li>The financial factors that actually tip the scale — and the "
            "ones that sound important but don't</li>"
            "<li>A break-even framework: how long you'd need to stay to make "
            "buying worth the upfront costs</li>"
            "<li>Hidden costs on both sides that most rent-vs-buy calculators "
            "skip</li>"
            "<li>A short self-check so you can honestly evaluate where you "
            "stand today</li>"
            "</ul>"
            "\n\n"
            "<h3>Use it when</h3>"
            "<ul>"
            "<li>You're early in the decision and want a grounded starting "
            "point — not a sales pitch</li>"
            "<li>You want something concrete to look at with a partner or "
            "family member instead of going back and forth</li>"
            "<li>You need to figure out whether \"not yet\" is the right "
            "call — and feel good about it</li>"
            "</ul>"
            "\n\n"
            "<p>Quick to read. Easy to come back to. Built for the thinking "
            "stage — before you're deep in mortgage math.</p>"
            "\n\n"
            "<p><strong>Free. No email required.</strong></p>"
            "\n\n"
            "<p><em>Evidence-informed decision tools for overwhelmed brains "
            "navigating real life. Built by a Board-Certified Music Therapist "
            "(MT-BC) using principles from behavioral science and cognitive "
            "accessibility design.</em></p>"
            "\n\n"
            "<p><em>Checklist &amp; Chill provides educational materials only "
            "and does not offer medical, mental health, legal, or financial "
            "advice.</em></p>"
        ),
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
