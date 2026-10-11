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
    from .. import model, gamedata

    # Later editor additions are supplied only to the PySide process, before
    # validation or manifest parsing imports their game-data names.
    for name, value in (("RITUAL_TRIBUTE_MAX", 5),
                        ("RITUAL_ORIGINS", ("field", "hand", "both")),
                        ("TAGS_MAX", 32), ("TAG_LENGTH_MAX", 31),
                        ("FRAME_COLOR_NAMES", ["Gold", "Green", "Pink", "Blue"]),
                        ("FRAME_COLOUR_NAMES", ("Gold", "Green", "Pink", "Blue", "Purple", "Orange"))):
        if not hasattr(gamedata, name):
            setattr(gamedata, name, value)
    if not hasattr(gamedata, "FRAME_NAME_ALIASES"):
        aliases = {name.lower(): index for index, name in enumerate(gamedata.FRAME_NAMES)}
        aliases.update({name.lower(): index for index, name in enumerate(gamedata.FRAME_COLOUR_NAMES)})
        gamedata.FRAME_NAME_ALIASES = aliases

    from . import duelist_data_compat
    for name in duelist_data_compat.__all__:
        if not hasattr(gamedata, name):
            setattr(gamedata, name, getattr(duelist_data_compat, name))

    # Newer validation supports ritual sources (field, hand, or both).  Keep
    # this modern-only state on Qt projects instead of extending master's
    # Project constructor.
    if not getattr(model.Project, "_qt_ritual_origin_compatible", False):
        original_project_init = model.Project.__init__

        def project_init(self, *args, **kwargs):
            original_project_init(self, *args, **kwargs)
            if not hasattr(self, "ritual_from"):
                self.ritual_from = {}

        model.Project.__init__ = project_init
        model.Project._qt_ritual_origin_compatible = True

    # The classic branch keeps ritual rules in the retail three-card form.
    # The native game and the newer editor schema allow one to five
    # requirements and a source, so offer that richer API only to PySide.
    # Keeping it here means updating master never changes the classic editor.
    if not hasattr(model.Project, "ritual_recipe"):
        def ritual_recipe(project, ritual):
            owner = ritual
            recipe = project.rituals.get(ritual)
            if recipe is None and ritual in project.added:
                owner = project.base_of(ritual)
                recipe = project.rituals.get(owner)
            if recipe is None:
                return None
            requirements = project.ritual_requirements.get(owner)
            tributes = ([dict(row) for row in requirements] if requirements else
                        [{"card": card} if card else {} for card in recipe[:-1]])
            return tributes, recipe[-1], project.ritual_from.get(owner, "field")

        def set_ritual(project, ritual, tributes, result, origin="field", objects=None):
            requirements = [dict(row) for row in tributes]
            project.rituals[ritual] = tuple(row.get("card", 0) for row in requirements) + (result,)
            if all(set(row) == {"card"} for row in requirements):
                project.ritual_requirements.pop(ritual, None)
            else:
                project.ritual_requirements[ritual] = requirements
            if origin == "field":
                project.ritual_from.pop(ritual, None)
            else:
                project.ritual_from[ritual] = origin

        def remove_ritual(project, ritual):
            project.ritual_requirements.pop(ritual, None)
            project.ritual_from.pop(ritual, None)
            project.rituals.pop(ritual, None)

        original_revert_ritual = model.Project.revert_ritual
        def revert_ritual(project, ritual):
            original_revert_ritual(project, ritual)
            project.ritual_from.pop(ritual, None)

        model.Project.ritual_recipe = ritual_recipe
        model.Project.set_ritual = set_ritual
        model.Project.remove_ritual = remove_ritual
        model.Project.revert_ritual = revert_ritual

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

    # Monster effects are modern-editor card metadata.  Master already keeps
    # arbitrary replacement fields in ``card_extra``/``AddedCard.extra``, so
    # expose the small model API the Qt Effects page needs without extending
    # the classic Project class itself.
    if not hasattr(model.Project, "monster_effects_of"):
        def monster_effects_of(project, cid):
            if cid not in project.cards:
                return [], False
            extra = (project.added[cid].extra if cid in project.added
                     else project.card_extra.get(cid, {}))
            if "monster_effects" in extra:
                rows = extra["monster_effects"]
                return (list(rows) if isinstance(rows, list) else []), True
            if cid in project.added:
                return monster_effects_of(project, project.base_of(cid))
            return [], False

        def set_monster_effects(project, cid, rows, keep_empty=False):
            if cid not in project.cards:
                return
            copied = [dict(row) for row in rows if isinstance(row, dict)]
            if cid in project.added:
                extra = project.added[cid].extra
            else:
                extra = project.card_extra.setdefault(cid, {})
            if copied or keep_empty:
                extra["monster_effects"] = copied
            else:
                extra.pop("monster_effects", None)
                if cid not in project.added and not extra:
                    project.card_extra.pop(cid, None)

        model.Project.monster_effects_of = monster_effects_of
        model.Project.set_monster_effects = set_monster_effects

    # A newer validator calls this optional roster check.  Master has no
    # added-duelist model, so the modern frontend has nothing additional to
    # validate until its roster compatibility layer supplies one.
    from .. import validate
    if not hasattr(validate, "_check_duelist_unlocks"):
        def _check_duelist_unlocks(_project, _out):
            return None
        validate._check_duelist_unlocks = _check_duelist_unlocks

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

    # Master encodes descriptions correctly but drops colour control codes.
    # Card View needs those tokens in order to render its coloured text.
    if not getattr(card_text.encode, "_qt_colours_compatible", False):
        original_encode = card_text.encode

        def encode(text, colours=False, colors=None):
            if colors is not None:
                colours = colors
            if not colours:
                return original_encode(text)
            out, column, index = [], 0, 0
            while index < len(text):
                char = text[index]
                if char == "\n":
                    out.append("\n")
                    column = 0
                    index += 1
                    continue
                if char == " ":
                    index += 1
                    continue
                word, end = [], index
                while end < len(text) and text[end] not in " \n":
                    code = card_text.code_at(text, end)
                    if code:
                        word.append(code)
                        end += len(code[0])
                    else:
                        word.append((text[end], 1))
                        end += 1
                letters = sum(width for _letter, width in word)
                if column and column + 1 + letters > card_text.LINE_LETTERS:
                    out.append("\n")
                    column = 0
                elif column:
                    out.append(" ")
                    column += 1
                for letter, width in word:
                    if width == 0:
                        out.append(letter)
                    elif letter >= " ":
                        out.append(letter)
                        column += 1
                index = end
            return out

        encode._qt_colours_compatible = True
        card_text.encode = encode

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

    # Recovery.Writer is a classic-editor worker API.  Install the Qt snapshot
    # adapter only for this frontend.
    from .recovery_compat import install as install_recovery_compat
    install_recovery_compat()
