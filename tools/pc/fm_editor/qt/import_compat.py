"""Always expose the modified-game importer in the Qt editor."""
from __future__ import annotations

from pathlib import Path
import inspect
import struct


def install() -> None:
    """Add the experimental BIN importer without changing the tracked menu code."""
    from PySide6.QtGui import QAction
    from .. import gamedata, importer, manifest, starter_pools
    from . import import_legacy_parts
    from .window import ModernEditor

    if getattr(ModernEditor, "_import_compat_installed", False):
        return
    ModernEditor._import_compat_installed = True
    # qt/window.py from the older editor revision supplies a progress callback;
    # the current importer deliberately has a four-argument API.  Keep the
    # existing progress dialog while safely discarding that obsolete callback.
    if not getattr(importer, "_qt_progress_compat", False):
        original_import_modded = importer.import_modded

        def minimal_text_changes(retail_slus, modded_slus, report, modded_wa=b"", card_fields=None):
            """Write only changed text items and their required local labels.

            The stock importer intentionally writes a whole bank when any
            changed item jumps to a label.  That is safe, but turns an
            otherwise tiny import into thousands of stock dialogue and card
            names.  The PC listing loader already falls back to retail for
            omitted items, so retain only changed roots and label owners they
            directly or transitively reference.
            """
            from ..gamedata import _tl
            import re

            card_fields = card_fields or {}
            before = importer._items(_tl.write_listing(gamedata._image(retail_slus)))
            after = importer._items(importer.modded_listing(modded_slus, modded_wa, report))
            label = re.compile(r"L[0-9A-Fa-f]{4}")
            controls = re.compile(r"\{[^}]*\}")

            def same_text(now, old):
                if now == old:
                    return True
                if label.sub("L", now) == label.sub("L", old):
                    return True
                return controls.sub("", now).strip() == controls.sub("", old).strip()

            def wanted(bank, key):
                if not importer._card_item(bank, key):
                    return True
                field = importer.CARD_BANKS.get(bank, (0, ""))[1]
                return any(cid in card_fields.get(field, ())
                           for cid in importer._card_ids(bank, key))

            parts, carried = [], {}
            for bank in ("dialog", "names", "descriptions"):
                old, new = before.get(bank, {}), after.get(bank, {})
                if not new:
                    continue
                selected = {
                    key for key, value in new.items()
                    if wanted(bank, key) and
                    (key not in old or not same_text(value, old[key]))
                }
                if not selected:
                    continue

                # Labels sit within listing items. Include their owner when
                # a selected item calls or jumps to it, then repeat for that
                # owner's own dependencies.
                owners = {}
                for key, value in new.items():
                    for target in re.findall(r"\{:\s*(L[0-9A-Fa-f]{4})\}", value):
                        owners[target.upper()] = key
                pending = list(selected)
                while pending:
                    key = pending.pop()
                    for target in label.findall(new[key]):
                        owner = owners.get(target.upper())
                        if owner and owner not in selected:
                            selected.add(owner)
                            pending.append(owner)

                keys = [key for key in new if key in selected]
                parts.append(f"@bank {bank}\n")
                parts.extend(new[key] + ("" if new[key].endswith("{cont}") else "\n")
                             for key in keys)
                for key in keys:
                    for cid in importer._card_ids(bank, key):
                        carried[(cid, importer.CARD_BANKS[bank][1])] = new[key]
                report.append(f"text: {len(keys)} changed {bank} entries imported")

            if not parts:
                return None, carried
            head = ("# Text entries imported from a modified game. Entries not listed here use retail text.\n"
                    "# Card names and descriptions without control codes are written in mod.json.\n\n")
            return head + "\n".join(parts), carried

        # import_modded resolves this global when it performs the text pass.
        importer.text_changes = minimal_text_changes

        def name_colour_changes(retail_files, modded_files):
            """Colour-only card-name edits represented by card_text_colors.

            A PS1 name may start with F8 0A NN.  The plain-name reader drops
            that code, so keeping it in text.txt is the wrong representation
            when the visible name itself is otherwise retail-identical.
            """
            current = gamedata._image(modded_files.slus)
            retail = gamedata._image(retail_files.slus)

            def raw(image, cid):
                return gamedata.text_bytes(
                    image, gamedata.NAME_BANK + image.u16(gamedata.NAME_TABLE + cid * 2), 128)

            def colour(data):
                for at in range(max(0, len(data) - 2)):
                    if data[at:at + 2] == b"\xF8\x0A" and data[at + 2] < 8:
                        return data[at + 2]
                return None

            def without_colours(data):
                out, at = bytearray(), 0
                while at < len(data):
                    if data[at:at + 2] == b"\xF8\x0A" and at + 2 < len(data):
                        at += 3
                    else:
                        out.append(data[at])
                        at += 1
                return bytes(out)

            found, colour_only = {}, set()
            for cid in range(1, gamedata.CARD_COUNT + 1):
                new, old = raw(current, cid), raw(retail, cid)
                value = colour(new)
                if value is None or value == colour(old):
                    continue
                found[cid] = value
                if without_colours(new) == without_colours(old):
                    colour_only.add(cid)
            return found, colour_only

        def import_starter_pool_weights(result, retail_files, modded_files):
            """Turn changed disc starter-pool weights into ``starter_pools``.

            The seven rows in WA_MRG.MRG are weighted pools, not written
            decks.  The base importer preserved changed rows as archive data
            (and rejected some low-total rows as counted decks), which left
            nothing editable on the Starter decks page.  The port has a
            direct representation for those rows, including every weight.
            """
            retail = starter_pools.retail(retail_files.wa)
            modified = starter_pools.retail(modded_files.wa)
            if not retail or not modified or len(retail) != len(modified):
                return 0
            changed = sum(
                1
                for old, new in zip(retail, modified)
                for cid in set(old.cards) | set(new.cards)
                if old.cards.get(cid, 0) != new.cards.get(cid, 0)
            )
            draws_changed = any(old.draws != new.draws for old, new in zip(retail, modified))
            if not changed and not draws_changed:
                return 0
            result.project.other["starter_pools"] = starter_pools.build(modified, result.project.ref)
            # Discard any old page cache so the imported rows appear as soon
            # as the editor refreshes its Starter decks workspace.
            result.project.starter_pool_state = None
            result.report.append(
                f"starter pools: imported {changed} changed card weight"
                + ("s" if changed != 1 else "")
                + (" and changed draw counts" if draws_changed else ""))
            return changed

        def import_guardian_star_names(result, retail_files, modded_files):
            """Read all fifteen global Guardian Star name slots.

            The game resolves star labels through the names-bank entries
            ``0x8317 + star_id``.  They are independent of the two packed
            four-bit star values on a card, so decoding card records alone
            preserves the number but loses a renamed retail star or a custom
            slot 11–15.  The classic importer retained these labels; write
            their direct ``guardian_stars`` representation here as well.
            """
            from .. import campaign_map

            changed, entries = 0, []
            try:
                retail_image = gamedata._image(retail_files.slus)
                modded_image = gamedata._image(modded_files.slus)
                retail_glyphs = gamedata._tl.glyph_characters(retail_image)
                modded_glyphs = gamedata._tl.glyph_characters(modded_image)
                used = {
                    star for card in result.project.cards.values()
                    for star in (card.star1, card.star2) if 1 <= star <= 15
                }
                for star in range(1, 16):
                    index = 0x8317 + star
                    old = campaign_map._plain_string(retail_image, retail_glyphs, index).strip()
                    new = campaign_map._plain_string(modded_image, modded_glyphs, index).strip()
                    # Declaring every non-retail ID in use is essential even
                    # when a mod's custom executable keeps its name outside
                    # the normal table.  It makes slots 11–15 visible as
                    # ``Star 11`` etc., instead of silently treating them as
                    # retail/unknown data.  A readable changed label then
                    # replaces that fallback.
                    if not new or new == old:
                        if star > 10 and star in used:
                            entries.append({"id": star})
                        continue
                    entries.append({"id": star, "name": new})
                    changed += 1
            except (IndexError, KeyError, ValueError, struct.error) as problem:
                # Some community executables replace the entire name bank;
                # their pointers cannot be safely read as retail text.
                result.report.append(
                    f"guardian stars: could not read global names ({type(problem).__name__}: {problem})")
                return 0
            if not entries:
                return 0
            section = result.project.other.setdefault("guardian_stars", {})
            old_entries = section.get("stars")
            existing = {
                item.get("id"): item for item in old_entries
                if isinstance(item, dict) and isinstance(item.get("id"), int)
            } if isinstance(old_entries, list) else {}
            for entry in entries:
                prior = existing.get(entry["id"])
                if prior is None:
                    existing[entry["id"]] = entry
                else:
                    prior["name"] = entry["name"]
            section["stars"] = [existing[star] for star in sorted(existing)]
            declared = len(entries)
            result.report.append(
                f"guardian stars: imported {changed} changed name slot"
                + ("s" if changed != 1 else "")
                + f" and declared {declared} slot" + ("s" if declared != 1 else "")
                + " (IDs 1–15)")
            return changed

        def trim_retail_text(result, retail_files):
            """Drop listing items that are equivalent to retail text.

            The loader resolves an omitted string or label to the retail bank,
            so a partial listing needs only the entries that actually differ.
            The base importer used to keep whole banks after a labelled jump.
            """
            raw = result.project.files.get("text.txt")
            if not raw:
                return 0
            try:
                text = raw.decode("utf-8")
                from ..gamedata import _tl
                retail_text = _tl.write_listing(gamedata._image(retail_files.slus))
                current = manifest.listing_items(text)
                retail = manifest.listing_items(retail_text)
            except Exception:
                return 0
            # Importing an otherwise stock BIN can relocate every label in a
            # text bank.  A literal listing comparison then treats every
            # entry as changed despite identical on-screen text.  Labels and
            # control sequences are implementation details; use them for the
            # exact fast path, then compare the rendered text as a fallback.
            import re

            label = re.compile(r"L[0-9A-Fa-f]{4}")
            controls = re.compile(r"\{[^}]*\}")

            def equivalent(current_value, retail_value):
                if current_value == retail_value:
                    return True
                if label.sub("L", current_value) == label.sub("L", retail_value):
                    return True
                # This intentionally ignores formatting codes when deciding
                # whether a stock line belongs in a partial text listing.
                # Non-stock visible dialogue and names remain intact.
                return controls.sub("", current_value).strip() == controls.sub("", retail_value).strip()

            kept, removed = {}, []
            for bank, items in current.items():
                for key, value in items.items():
                    retail_value = retail.get(bank, {}).get(key)
                    if retail_value is not None and equivalent(value, retail_value):
                        removed.append((bank, key))
                    else:
                        kept.setdefault(bank, {})[key] = value
            if not removed:
                return 0
            head = ("# Text of a modified game that differs from retail, written by the FM Editor's importer\n"
                    "# (notes/translation.md). Entries matching retail are intentionally omitted.\n\n")
            parts = []
            for bank in ("dialog", "names", "descriptions"):
                items = kept.get(bank, {})
                if not items:
                    continue
                parts.append(f"@bank {bank}\n")
                parts.extend(value + ("" if value.endswith("{cont}") else "\n")
                             for value in items.values())
            if parts:
                result.project.files["text.txt"] = (head + "\n".join(parts)).encode("utf-8")
            else:
                result.project.files.pop("text.txt", None)
                result.project.other.pop("text", None)
            # The editor tracks card strings a text listing owns.  Remove
            # ownership for entries restored to the retail fallback.
            for bank, key in removed:
                field = importer.CARD_BANKS.get(bank, (0, ""))[1]
                if not field:
                    continue
                for cid in importer._card_ids(bank, key):
                    fields = result.project.text_cards.get(cid)
                    if fields:
                        fields.pop(field, None)
                        if not fields:
                            result.project.text_cards.pop(cid, None)
            return len(removed)

        def import_modded(retail_files, modded_files, mod_id="imported-mod", name=None, *_progress):
            # qt/window.py supplies ``say`` to keep its modal progress dialog
            # alive.  The newer importer is also useful from the CLI, where
            # it intentionally has no UI callback, so provide the feedback
            # here rather than changing its public API.
            say = _progress[0] if _progress and callable(_progress[0]) else lambda _stage: None
            say("Checking card-name colours: 1/722")
            colours, colour_only = name_colour_changes(retail_files, modded_files)
            previous_coded = importer.coded_card_texts
            previous_text_changes = importer.text_changes
            previous_cards = gamedata.read_cards
            previous_pool = gamedata.decode_pool
            previous_wa_data = importer.wa_data
            card_pass = 0
            pool_pass = 0

            def cards_with_progress(slus, wa=b""):
                """The retail loader, with updates every 24 real cards."""
                nonlocal card_pass
                card_pass += 1
                source = "retail" if card_pass == 1 else "modified"
                image = gamedata._image(slus)
                glyphs = gamedata._tl.glyph_characters(image)
                names = gamedata.plain_names(image, glyphs)
                texts = gamedata.description_bytes(slus, wa)
                cards = {}
                for cid in range(1, gamedata.CARD_COUNT + 1):
                    stats = image.u32(gamedata.STATS_ADDRESS + (cid - 1) * 4)
                    level_attr = image.bytes(gamedata.LEVEL_ATTR_ADDRESS + cid, 1)[0]
                    cards[cid] = gamedata.Card(
                        id=cid, name=names.get(cid, ""),
                        description=gamedata.decode_text(gamedata._Bytes(texts[cid]), 0, glyphs, len(texts[cid])),
                        attack=(stats & 0x1FF) * 10, defense=((stats >> 9) & 0x1FF) * 10,
                        star2=(stats >> 18) & 0xF, star1=(stats >> 22) & 0xF,
                        type=(stats >> 26) & 0x1F, level=level_attr & 0xF, attribute=level_attr >> 4)
                    if cid == 1 or cid % 24 == 0 or cid == gamedata.CARD_COUNT:
                        say(f"Loading {source} cards: {cid}/{gamedata.CARD_COUNT}")
                return cards

            def pool_with_progress(block, offset):
                nonlocal pool_pass
                pool_pass += 1
                source = "retail" if pool_pass <= 160 else "modified"
                step = pool_pass if pool_pass <= 160 else pool_pass - 160
                if step == 1 or step % 20 == 0 or step == 160:
                    say(f"Loading {source} deck and drop tables: {step}/160")
                return previous_pool(block, offset)

            def wa_with_progress(*args, **kwargs):
                say("Scanning card art and thumbnails: 1/722")
                result = previous_wa_data(*args, **kwargs)
                say("Scanning card art and thumbnails: 722/722")
                return result

            def coded_without_name_colours(old_files, new_files):
                fields = previous_coded(old_files, new_files)
                fields["name"] = set(fields.get("name", ())) - colour_only
                return fields

            def text_with_progress(*args, **kwargs):
                say("Comparing dialogue, menus, and card text")
                return previous_text_changes(*args, **kwargs)

            importer.coded_card_texts = coded_without_name_colours
            importer.text_changes = text_with_progress
            gamedata.read_cards = cards_with_progress
            gamedata.decode_pool = pool_with_progress
            importer.wa_data = wa_with_progress
            try:
                say("Loading retail game tables")
                result = original_import_modded(retail_files, modded_files, mod_id, name)
            finally:
                importer.coded_card_texts = previous_coded
                importer.text_changes = previous_text_changes
                gamedata.read_cards = previous_cards
                gamedata.decode_pool = previous_pool
                importer.wa_data = previous_wa_data
            # Do not leave the base importer's whole-bank fallback in the
            # project.  Rebuild this output explicitly from the minimal
            # listing, even when another importer hook selected the legacy
            # text_changes function while the import was running.
            say("Writing only changed text entries")
            card_fields = coded_without_name_colours(retail_files, modded_files)
            minimal_text, carried = minimal_text_changes(
                retail_files.slus, modded_files.slus, result.report,
                modded_files.wa, card_fields)
            if minimal_text:
                result.project.files["text.txt"] = minimal_text.encode("utf-8")
                result.project.other["text"] = "text.txt"
            else:
                result.project.files.pop("text.txt", None)
                result.project.other.pop("text", None)
            # The original pass may have marked full-bank card entries as
            # text-owned. Replace that ownership with only the minimal set.
            for cid, fields in list(result.project.text_cards.items()):
                fields.pop("name", None)
                fields.pop("description", None)
                if not fields:
                    result.project.text_cards.pop(cid, None)
            for (cid, field), item in carried.items():
                value = manifest.plain_name(item) if field == "name" else manifest.listing_plain(item)
                setattr(result.project.cards[cid], field, value)
                result.project.text_cards.setdefault(cid, {})[field] = value
            say("Removing retail-equivalent text")
            trimmed = trim_retail_text(result, retail_files)
            if trimmed:
                result.report.append(f"text: omitted {trimmed} entries identical to retail")
            if colours:
                say("Importing card name colours")
                table = result.project.other.setdefault("card_text_colors", {})
                rules = table.setdefault("cards", [])
                for cid, colour in sorted(colours.items()):
                    rules.append({"card": result.project.ref(cid), "name": colour})
                result.report.append(
                    f"cards: {len(colours)} card name colour"
                    + ("s" if len(colours) != 1 else "")
                    + " imported into card_text_colors")
            say("Importing card art: 1/722")
            import_legacy_parts.import_card_art(
                result.project, retail_files.wa, modded_files.wa, result.report, say)
            say("Importing Guardian Stars and matchups")
            import_legacy_parts.import_guardian_stars(
                result.project, result.project.retail, gamedata.load_game(modded_files),
                retail_files.slus, modded_files.slus, modded_files.wa, result.report)
            say("Importing starter-deck pool weights")
            import_starter_pool_weights(result, retail_files, modded_files)
            # Save As deliberately preserves unrelated files already in its
            # destination.  Mark this fresh BIN import so its save wrapper
            # can remove an obsolete, unreferenced text.txt from a prior
            # import in that same folder.
            result.project._compat_imported_bin = True
            say("Finishing imported mod")
            return result

        importer.import_modded = import_modded
        importer._qt_progress_compat = True

    original_init = ModernEditor.__init__

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        menu = self.menus.get("File")
        if menu is None or any("Import a modified game" in action.text() for action in menu.actions()):
            return
        action = QAction("Import a modified game (.bin or SLUS_014.11, experimental)…", menu)
        action.triggered.connect(self.import_modded_game)
        anchor = next((item for item in menu.actions()
                       if "Convert an old recomp" in item.text()), None)
        if anchor is None:
            menu.addAction(action)
        else:
            menu.insertAction(anchor, action)

    ModernEditor.__init__ = init

    original_save_mod = ModernEditor.save_mod

    def save_mod(self, *args, **kwargs):
        original_save_mod(self, *args, **kwargs)
        if (getattr(self.project, "_compat_imported_bin", False) and not self.dirty
                and "text.txt" not in self.project.files
                and not self.project.other.get("text") and self.project.source_dir):
            stale = Path(self.project.source_dir) / "text.txt"
            if stale.is_file():
                stale.unlink()
                self.statusBar().showMessage(
                    "Saved imported mod and removed stale retail text.txt.")

    ModernEditor.save_mod = save_mod

    # The Art workspace already uses ``preview_wa`` after a BIN import, but
    # several card-facing workspaces predate that split and still pass
    # ``self.files.wa`` to their renderer.  Route those calls through the
    # imported archive only while they render.  The retail GameFiles object
    # remains intact for model diffs, saving, and a subsequent New/Open mod.
    def with_preview_archive(method):
        signature = inspect.signature(method)

        def wrapped(self, *args, **kwargs):
            # Qt signals often supply an extra ``checked``/index argument to
            # a slot that was intentionally declared without one.  Preserve
            # the arguments a method actually accepts, but discard that
            # surplus signal payload before calling the original slot.
            try:
                signature.bind(self, *args, **kwargs)
            except TypeError:
                signature.bind(self, **kwargs)
                args = ()
            files = getattr(self, "files", None)
            archive = getattr(self, "preview_wa", None)
            if files is None or archive is None or archive is files.wa:
                return method(self, *args, **kwargs)
            retail_archive = files.wa
            files.wa = archive
            try:
                return method(self, *args, **kwargs)
            finally:
                files.wa = retail_archive
        return wrapped

    from .cards import CardsMixin
    from .equips import EquipsMixin
    from .packs import PacksMixin
    from .rituals import RitualsMixin
    from .stars import StarsMixin

    for cls, name in (
        (CardsMixin, "_render_preview"),
        (EquipsMixin, "_fill_equip_monsters"),
        (RitualsMixin, "_refresh_ritual_detail"),
        (PacksMixin, "_pack_card_icon"),
        (StarsMixin, "_star_icon_pixmap"),
    ):
        original = getattr(cls, name)
        if not getattr(original, "_preview_archive_compat", False):
            replacement = with_preview_archive(original)
            replacement._preview_archive_compat = True
            setattr(cls, name, replacement)
