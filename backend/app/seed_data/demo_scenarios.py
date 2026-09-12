"""
The 3 hackathon demo scenarios, as data.

This is the single source of truth for demo content -- both `app/seed.py`
(pre-populates 3 fully-processed inspections at startup so the dashboard/
repository aren't empty) and `POST /api/demo/load` (lets an officer spawn a
fresh one live, then walk it through the real OCR -> extraction -> analysis
pipeline) import from here. See CLAUDE.md for *why* each scenario resolves
the way it does -- this file just holds the label text and confidences.

Every line of "OCR text" below is what a MockOCRProvider canned lookup
returns for that image; nothing here is manually mapped to a declaration --
the regex extractor in app/services/extraction/regex_extractor.py runs
against this text exactly as it would against real OCR output.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from ..models import EvidenceType, SupplyType

CATEGORY_FOOD = "Food & Beverages"
CATEGORY_COSMETICS = "Cosmetics & Personal Care"
CATEGORY_HOUSEHOLD = "Household Products"
CATEGORY_ELECTRONICS = "Electronics"
CATEGORY_APPAREL = "Textiles & Apparel"
CATEGORY_PHARMA = "Pharmaceuticals (OTC)"
CATEGORY_OTHER = "Other"

PRODUCT_CATEGORIES = [
    CATEGORY_FOOD,
    CATEGORY_COSMETICS,
    CATEGORY_HOUSEHOLD,
    CATEGORY_ELECTRONICS,
    CATEGORY_APPAREL,
    CATEGORY_PHARMA,
    CATEGORY_OTHER,
]

# Categories where a best-before / use-by declaration is expected.
BEST_BEFORE_APPLICABLE_CATEGORIES = [CATEGORY_FOOD, CATEGORY_COSMETICS, CATEGORY_PHARMA]


@dataclass
class LineSpec:
    text: str
    confidence: float  # 0-100, simulates per-line OCR confidence


@dataclass
class ImageSpec:
    image_type: EvidenceType
    slug: str  # used to build the generated filename, e.g. "front"
    lines: List[LineSpec]
    blurred: bool = False  # visually + numerically simulate poor capture quality

    @property
    def full_text(self) -> str:
        return "\n".join(l.text for l in self.lines)

    @property
    def overall_confidence(self) -> float:
        if not self.lines:
            return 0.0
        return round(sum(l.confidence for l in self.lines) / len(self.lines), 1)


@dataclass
class DemoScenario:
    key: str  # "compliant" | "non_compliant" | "review"
    label: str
    product_name: str
    brand: str
    category: str
    supply_type: SupplyType
    batch_lot: str
    manufacturer_name: str
    inspection_location: str
    images: List[ImageSpec] = field(default_factory=list)
    listing_url: Optional[str] = None
    expected_overall_result: str = ""  # documentation only, asserted in tests


SCENARIOS: dict[str, DemoScenario] = {
    "compliant": DemoScenario(
        key="compliant",
        label="Demo 1 — Compliant packaged food product",
        product_name="Solara Multigrain Muesli",
        brand="Solara Foods",
        category=CATEGORY_FOOD,
        supply_type=SupplyType.DOMESTIC,
        batch_lot="SLM-2311-B7",
        manufacturer_name="Solara Foods Pvt. Ltd.",
        inspection_location="Sector 17 Consumer Market, Chandigarh",
        expected_overall_result="COMPLIANT",
        images=[
            ImageSpec(
                image_type=EvidenceType.FRONT,
                slug="front",
                lines=[
                    LineSpec("SOLARA FOODS", 95),
                    LineSpec("Multigrain Muesli with Nuts & Seeds", 95),
                    LineSpec("Net Wt: 500 g", 96),
                    LineSpec("MRP: Rs. 249 (Incl. of all taxes)", 94),
                ],
            ),
            ImageSpec(
                image_type=EvidenceType.BACK,
                slug="back",
                lines=[
                    LineSpec("Mfd. by: Solara Foods Pvt. Ltd.", 95),
                    LineSpec("Plot 14, Industrial Area Phase II, Panchkula, Haryana - 134113, India", 93),
                    LineSpec("Pkd On: 15/12/2025", 96),
                    LineSpec("Best Before: 15/09/2026", 95),
                    LineSpec("Customer Care: 1800-121-3456, care@solarafoods.example", 97),
                ],
            ),
        ],
    ),
    "non_compliant": DemoScenario(
        key="non_compliant",
        label="Demo 2 — Non-compliant imported product",
        product_name="Northstar Belgian Choco Wafers",
        brand="Northstar Imports",
        category=CATEGORY_FOOD,
        supply_type=SupplyType.IMPORTED,
        batch_lot="NB-0092",
        manufacturer_name="Northstar Imports Pvt. Ltd.",
        inspection_location="Bandra West Retail Cluster, Mumbai",
        expected_overall_result="NON_COMPLIANT",
        images=[
            ImageSpec(
                image_type=EvidenceType.FRONT,
                slug="front",
                lines=[
                    LineSpec("NORTHSTAR IMPORTS", 90),
                    LineSpec("Belgian Choco Wafers", 90),
                    LineSpec("Net Wt: 6 x 25 g (150 g)", 88),
                    LineSpec("MRP: Rs. 149", 90),
                ],
            ),
            ImageSpec(
                image_type=EvidenceType.BACK,
                slug="back",
                lines=[
                    LineSpec("Imported & Marketed by: Northstar Imports Pvt. Ltd.", 89),
                    LineSpec("4th Floor, Cross Point Mall, Bandra West, Mumbai - 400050", 87),
                    LineSpec("Imported On: 10/01/2026", 86),
                    LineSpec("Best Before: 20/03/2027", 85),
                    # Deliberately absent: country of origin, consumer care,
                    # unit sale price -- these are the intended violations.
                ],
            ),
        ],
    ),
    "review": DemoScenario(
        key="review",
        label="Demo 3 — Review required (OCR/readability uncertainty)",
        product_name="Glowmint Herbal Face Wash",
        brand="Glowmint",
        category=CATEGORY_COSMETICS,
        supply_type=SupplyType.DOMESTIC,
        batch_lot="GM-7742",
        manufacturer_name="Aarav Consumer Products Pvt. Ltd.",
        inspection_location="Sector 58 Retail Hub, Noida",
        expected_overall_result="REVIEW_REQUIRED",
        images=[
            ImageSpec(
                image_type=EvidenceType.FRONT,
                slug="front",
                blurred=True,
                lines=[
                    LineSpec("GLOWMINT", 90),
                    LineSpec("Herbal Neem & Tulsi Face Wash", 84),
                    LineSpec("Net Qty: 100 ml", 68),
                    LineSpec("MRP: Rs. 185 (Incl. of all taxes)", 72),
                ],
            ),
            ImageSpec(
                image_type=EvidenceType.BACK,
                slug="back",
                blurred=True,
                lines=[
                    LineSpec("Mfd by: Aarav Consumer Products Pvt. Ltd.", 89),
                    LineSpec("B-22, Sector 58, Noida, Uttar Pradesh - 201301", 58),
                    LineSpec("Pkd On: 20/07/2026", 87),
                    LineSpec("BB: See seal on cap", 81),
                    LineSpec("Consumer Care: 1800-233-9090, help@glowmint.example", 91),
                ],
            ),
        ],
    ),
}


def get_scenario(key: str) -> DemoScenario:
    if key not in SCENARIOS:
        raise KeyError(f"Unknown demo scenario '{key}'. Valid: {list(SCENARIOS)}")
    return SCENARIOS[key]
