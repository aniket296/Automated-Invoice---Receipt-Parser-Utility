"""Programmatic multi-resolution application icon generator.

Generates a crisp Forest-Green (#065F46) & Slate (#0F172A) receipt-checkmark
badge icon at 16x16, 32x32, 48x48, and 256x256 resolutions and writes it to
assets/app_icon.ico.
"""

from pathlib import Path
from PIL import Image, ImageDraw


def draw_icon_canvas(size: int = 256) -> Image.Image:
    """Draws the high-resolution master receipt-checkmark badge icon."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer Slate rounded badge (#0F172A)
    margin = int(size * 0.05)
    radius = int(size * 0.22)
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=(15, 23, 42, 255),
        outline=(6, 95, 70, 255),
        width=max(2, int(size * 0.03)),
    )

    # Inner Forest-Green accent panel (#065F46)
    inner_m = int(size * 0.12)
    draw.rounded_rectangle(
        [inner_m, inner_m, size - inner_m, size - inner_m],
        radius=int(size * 0.16),
        fill=(6, 95, 70, 255),
    )

    # White receipt document sheet
    rx1, ry1 = int(size * 0.24), int(size * 0.18)
    rx2, ry2 = int(size * 0.74), int(size * 0.80)
    draw.rounded_rectangle(
        [rx1, ry1, rx2, ry2],
        radius=max(2, int(size * 0.04)),
        fill=(248, 250, 252, 255),
    )

    # Receipt text lines (Slate horizontal bars)
    line_x1 = int(size * 0.31)
    line_x2 = int(size * 0.67)
    line_h = max(2, int(size * 0.035))
    for idx, y_frac in enumerate([0.28, 0.38, 0.48, 0.58]):
        y = int(size * y_frac)
        end_x = line_x2 if idx % 2 == 0 else int(size * 0.56)
        draw.rounded_rectangle(
            [line_x1, y, end_x, y + line_h],
            radius=max(1, line_h // 2),
            fill=(51, 65, 85, 255),
        )

    # Emerald verification badge circle at bottom-right (#10B981)
    cx, cy = int(size * 0.70), int(size * 0.70)
    cr = int(size * 0.18)
    draw.ellipse(
        [cx - cr, cy - cr, cx + cr, cy + cr],
        fill=(16, 185, 129, 255),
        outline=(15, 23, 42, 255),
        width=max(2, int(size * 0.025)),
    )

    # Crisp white checkmark inside the emerald badge
    p1 = (int(cx - cr * 0.45), int(cy + cr * 0.02))
    p2 = (int(cx - cr * 0.10), int(cy + cr * 0.38))
    p3 = (int(cx + cr * 0.50), int(cy - cr * 0.35))
    stroke_w = max(2, int(size * 0.045))
    draw.line([p1, p2, p3], fill=(255, 255, 255, 255), width=stroke_w, joint="curve")

    return img


def generate_app_icon(output_path: Path | None = None) -> Path:
    """Generates multi-resolution ICO file at assets/app_icon.ico."""
    project_root = Path(__file__).resolve().parent.parent
    target = output_path or (project_root / "assets" / "app_icon.ico")
    target.parent.mkdir(parents=True, exist_ok=True)

    master = draw_icon_canvas(256)
    resolutions = [(16, 16), (32, 32), (48, 48), (256, 256)]
    master.save(target, format="ICO", sizes=resolutions)
    return target


if __name__ == "__main__":
    icon_file = generate_app_icon()
    print(f"Generated application icon: {icon_file} ({icon_file.stat().st_size} bytes)")
