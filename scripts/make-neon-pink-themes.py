#!/usr/bin/env python3
"""Generate the Neon Pink VS Code themes by recolouring the Neon Green ones.

Unlike make-pi-themes.py and make-opencode-theme.py, which assign a palette
slot by slot, this generator keeps every colour of the source theme except
the greens: each hex whose hue sits in the green band (75°–150°) is rotated
into the pink band around 320°, keeping its saturation and alpha and lifting
its lightness a little so the pink glows as brightly as the green did.
Everything else — backgrounds, blues, purples, reds, the syntax colours that
were never green — is copied unchanged, so the result reads as the same theme
in pink.

The remap itself goes through the shared hex_remap engine: the generator
builds a green-hex → pink-hex table from the greens it finds in the base
theme, walks the theme with it, and then verifies that no green hue survives
in the output.
"""
import colorsys
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))  # sibling import when loaded by path (tests)

from hex_remap import HEX_RE, walk  # noqa: E402

THEMES = HERE.parent / "themes"

# (source theme, generated theme, generated theme's name)
VARIANTS = [
    ("neon-green-color-theme.json",
     "neon-pink-color-theme.json", "Neon Pink — Dark Terminal"),
    ("neon-green-liquid-glass-color-theme.json",
     "neon-pink-liquid-glass-color-theme.json", "Neon Pink — Liquid Glass"),
]

GREEN_LO, GREEN_HI = 75, 150  # the hue band treated as green, in degrees
SOURCE_CENTRE = 111           # the hue of the accent #39ff14
PINK_CENTRE = 320             # where that accent lands
SPREAD = 0.3                  # how much of the green band's width the pinks keep
MIN_SATURATION = 0.05         # greys are not green

# Any 6-digit hex inside serialized theme text (also the base of an 8-digit one).
_HEX_IN_TEXT_RE = re.compile(r"#[0-9a-fA-F]{6}")


def _hls(hex6):
    r, g, b = (int(hex6[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)


def is_green(value):
    """Whether a #rrggbb or #rrggbbaa value has a green hue."""
    if not isinstance(value, str) or not HEX_RE.match(value):
        return False
    hue, _, sat = _hls(value[:7])
    return sat > MIN_SATURATION and GREEN_LO <= hue * 360 <= GREEN_HI


def pink(hex6):
    """The pink that stands in for a green #rrggbb (no alpha)."""
    hue, light, sat = _hls(hex6)
    new_hue = (PINK_CENTRE + (hue * 360 - SOURCE_CENTRE) * SPREAD) % 360
    new_light = min(light + 0.05 * sat, 0.95)
    r, g, b = colorsys.hls_to_rgb(new_hue / 360, new_light, sat)
    return "#%02x%02x%02x" % tuple(round(c * 255) for c in (r, g, b))


def green_hexes(text):
    """Sorted base hexes with a green hue present in *text*."""
    return sorted({m.group(0).lower() for m in _HEX_IN_TEXT_RE.finditer(text)
                   if is_green(m.group(0))})


def build_map(text):
    """green hex -> pink hex, for every green the theme text uses."""
    return OrderedDict((green, pink(green)) for green in green_hexes(text))


def main():
    failures = []
    for src_name, dst_name, name in VARIANTS:
        text = (THEMES / src_name).read_text(encoding="utf-8")
        table = build_map(text)
        out = walk(json.loads(text, object_pairs_hook=OrderedDict), table)
        out["name"] = name

        dst = THEMES / dst_name
        dst.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Wrote %s (%d greens turned pink)" % (dst.name, len(table)))

        # ---- verification: no green hue should survive ---------------------
        leftover = green_hexes(dst.read_text(encoding="utf-8"))
        if leftover:
            print("  ERROR leftover green hexes in %s: %s" % (dst.name, leftover))
            failures.append(name)
        else:
            print("  OK: no green hue left.")

    if failures:
        raise SystemExit("leftover green hexes in: " + ", ".join(failures))


if __name__ == "__main__":
    main()
