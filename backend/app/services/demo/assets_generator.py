"""
Generates the package-label images used by the 3 hackathon demo scenarios.

No external font files or network access required -- uses Pillow's built-in
bitmap font. Images are simple but legible label mockups; the "review"
scenario's images are additionally blurred/contrast-reduced so the low OCR
confidence assigned to them in demo_scenarios.py is visually credible, not
just a number nobody can see the reason for.
"""
import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from ...config import settings
from ...seed_data.demo_scenarios import SCENARIOS, ImageSpec

logger = logging.getLogger(__name__)

CANVAS_WIDTH = 900
LINE_HEIGHT = 54
TOP_MARGIN = 70
SIDE_MARGIN = 60


def _load_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        # Older Pillow (<10.1) load_default() takes no size argument.
        return ImageFont.load_default()


def _render_image(spec: ImageSpec) -> Image.Image:
    height = TOP_MARGIN + LINE_HEIGHT * (len(spec.lines) + 2)
    img = Image.new("RGB", (CANVAS_WIDTH, height), color=(250, 249, 245))
    draw = ImageDraw.Draw(img)

    # Label border, evoking a printed sticker rather than a blank page.
    draw.rectangle(
        [8, 8, CANVAS_WIDTH - 9, height - 9],
        outline=(60, 60, 60),
        width=3,
    )

    title_font = _load_font(22)
    body_font = _load_font(20)

    draw.text(
        (SIDE_MARGIN, 28),
        f"MetraCheck demo evidence — {spec.image_type.value.title()} panel",
        fill=(120, 120, 120),
        font=title_font,
    )

    y = TOP_MARGIN + 20
    for line in spec.lines:
        draw.text((SIDE_MARGIN, y), line.text, fill=(20, 20, 20), font=body_font)
        y += LINE_HEIGHT

    if spec.blurred:
        img = img.filter(ImageFilter.GaussianBlur(radius=1.7))
        img = ImageEnhance.Contrast(img).enhance(0.55)
        img = ImageEnhance.Brightness(img).enhance(1.08)

    return img


def generate_all_demo_assets(force: bool = False) -> list[str]:
    """
    Writes one PNG per ImageSpec across all scenarios to
    settings.DEMO_ASSETS_ROOT/<scenario_key>/<slug>.png.

    Returns the list of relative paths written (relative to DEMO_ASSETS_ROOT).
    Idempotent: skips files that already exist unless force=True.
    """
    root = Path(settings.DEMO_ASSETS_ROOT)
    written: list[str] = []

    for scenario in SCENARIOS.values():
        scenario_dir = root / scenario.key
        scenario_dir.mkdir(parents=True, exist_ok=True)
        for spec in scenario.images:
            rel_path = f"{scenario.key}/{spec.slug}.png"
            full_path = root / rel_path
            if full_path.exists() and not force:
                continue
            img = _render_image(spec)
            img.save(full_path, format="PNG")
            written.append(rel_path)
            logger.info("Generated demo asset %s", rel_path)

    return written


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    paths = generate_all_demo_assets(force=True)
    print(f"Generated {len(paths)} demo asset(s) under {settings.DEMO_ASSETS_ROOT}")
