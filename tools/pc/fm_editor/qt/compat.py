"""Qt-only compatibility for shared classic-editor modules.

The Qt editor is an additive layer over the classic editor. Keep adapters
here so its startup does not require changes to files that ship on master.
"""
from __future__ import annotations

import struct


def install() -> None:
    """Supply the Fusions-row helper expected by the Qt card-use page.

    Older classic ``model.py`` versions keep this helper in ``tabs.py``.
    Installing it on the loaded model module lets ``card_uses`` import the
    same name without changing that shared file.
    """
    from .. import model

    if not hasattr(model, "fusion_pairs"):
        def fusion_pairs(project):
            named = {pair for pair in project.own_fusion_pairs()[0]
                     if pair[0] in project.cards and pair[1] in project.cards}
            removes = set(project.active_removes()) if named else set()
            own = {pair: project.own_fusion(pair, removes) for pair in named}
            pairs = (set(project.fusions) | set(project.retail.fusions) |
                     project.fusion_explicit |
                     {pair for pair, made in own.items() if made is not None})
            return own, pairs

        model.fusion_pairs = fusion_pairs

    # The stock Guardian Star module describes star names and matchups. The
    # Qt page also shows the symbols stored in the disc's boot UI sheet.
    from .. import guardian_stars

    icon_sheet = 0xB51840
    icon_stride = 128
    icon_clut = 0xB60500
    icon_side = 16
    retail_spots = ((0, 0), (16, 0), (32, 0), (48, 0), (64, 0), (80, 0),
                    (96, 0), (112, 0), (0, 16), (16, 16))

    def sheet_icon(wa, star, spots):
        if not 1 <= star <= len(spots) or wa is None:
            return None
        x, y = spots[star - 1]
        start = icon_sheet + y * icon_stride + x // 2
        if start + (icon_side - 1) * icon_stride + icon_side // 2 > len(wa) or icon_clut + 32 > len(wa):
            return None
        palette = struct.unpack_from("<16H", wa, icon_clut)
        rgba = bytearray()
        drawn = False
        for row in range(icon_side):
            line = wa[start + row * icon_stride:start + row * icon_stride + icon_side // 2]
            for pixel in range(icon_side):
                index = (line[pixel // 2] >> (4 * (pixel % 2))) & 0xF
                if not index:
                    rgba += bytes(4)
                    continue
                drawn = True
                colour = palette[index] & 0x7FFF
                rgba += bytes(((colour & 31) * 255 // 31,
                               ((colour >> 5) & 31) * 255 // 31,
                               ((colour >> 10) & 31) * 255 // 31, 255))
        return (icon_side, icon_side, bytes(rgba)) if drawn else None

    if not hasattr(guardian_stars, "disc_icon"):
        guardian_stars.disc_icon = lambda wa, star: sheet_icon(wa, star, retail_spots)
    if not hasattr(guardian_stars, "imported_icon"):
        guardian_stars.imported_icon = lambda wa, star: sheet_icon(
            wa, star, tuple((16 * (i % 8), 16 * (i // 8)) for i in range(guardian_stars.MAX_STARS)))

    # The newer description-side renderer is optional for the Qt editor.
    # The classic renderer remains a useful fallback on branches where
    # card_text has not yet grown render_description().
    from .. import card_text

    if not hasattr(card_text, "render_description"):
        def render_description(font, text, type_name, _type_icon, stars=(), scale=2, **_unused):
            header = [type_name]
            if stars:
                header.append("GUARDIAN STAR")
                header.extend(name for name, _picture in tuple(stars)[:2])
            picture, _layout = card_text.Renderer(font).render(
                "\n".join(header + [text]), max(1, int(scale)))
            return picture

        card_text.render_description = render_description
