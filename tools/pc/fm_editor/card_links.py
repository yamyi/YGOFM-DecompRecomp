"""Links between the tabs by card.

* The card the window is on (app.current_card): the Cards and Art tabs show
  the same card, and Fusions and Equips follow it when it changes (each
  tab's follow()).
* A right-click on a card in any list: open it in Cards or Art, show its
  fusions or its equip targets, or list everything in the mod that uses it
  (Where it's used...), each line a link to its tab."""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

from .card_uses import plural, where_used      # noqa: F401 - the list this window shows
from .gamedata import TYPE_EQUIP
from .widgets import px, scrolled_tree


_open_menu = None     # the right-click menu up, if any


def close_menu(event=None):
    """Take the right-click menu down on another tab, a click elsewhere or
    Escape. Its grab is released once it is posted (else the window's own
    clicks would be lost), so Tk itself would leave it up."""
    global _open_menu
    menu, _open_menu = _open_menu, None
    if menu is None:
        return
    if event is not None and str(event.widget).startswith(str(menu)):
        _open_menu = menu       # a click on the menu itself, or one of its cascades
        return
    try:
        menu.unpost()
        menu.destroy()
    except tk.TclError:
        pass


def install(app, tab, tree, cards_of=None):
    """Give a list of cards the right-click menu. cards_of(iid) names the
    row's cards; by default the row's iid or its "#" column."""
    def default(iid):
        if iid.isdigit():
            return [int(iid)]
        value = str(tree.set(iid, "id")) if "id" in tree.cget("columns") else ""
        return [int(value)] if value.isdigit() else []

    cards_of = cards_of or default

    def popup(event):
        iid = tree.identify_row(event.y)
        if not iid or app.project is None:
            return
        if iid not in tree.selection():
            tree.selection_set(iid)
            tree.focus(iid)
            tree.update_idletasks()
            if iid not in tree.selection():     # the tab kept its card (a form that cannot be stored)
                return
        cids = [cid for cid in dict.fromkeys(cards_of(iid)) if cid in app.project.cards]
        if not cids:
            return
        global _open_menu
        close_menu()
        menu = tk.Menu(tree, tearoff=False)
        _open_menu = menu
        if len(cids) == 1:
            fill_menu(menu, app, tab, cids[0])
        else:
            for cid in cids:
                sub = tk.Menu(menu, tearoff=False)
                fill_menu(sub, app, tab, cid)
                menu.add_cascade(label=app.project.card_label(cid), menu=sub)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    tree.bind("<Button-3>", popup, add=True)
    if sys.platform == "darwin":
        tree.bind("<Button-2>", popup, add=True)


def fill_menu(menu, app, tab, cid):
    if tab is not app.cards:
        menu.add_command(label="Open in Cards", command=lambda: app.open_card(app.cards, cid))
    if tab is not app.art:
        menu.add_command(label="Open in Art", command=lambda: app.open_card(app.art, cid))
    menu.add_command(label="Show its fusions", command=lambda: app.open_card(app.fusions, cid))
    if app.project.cards[cid].type == TYPE_EQUIP:
        menu.add_command(label="Edit its equip targets", command=lambda: app.open_card(app.equips, cid))
    menu.add_separator()
    menu.add_command(label="Where it's used...", command=lambda: UsesWindow(app, cid))


def install_all(app):
    app.bind_all("<ButtonPress>", close_menu, add="+")
    app.bind_all("<Escape>", lambda e: close_menu(), add="+")
    p = lambda: app.project     # noqa: E731 -- the project changes when a mod is opened

    def fusion_cards(iid):
        a, b = (int(x) for x in iid.split(":"))
        return [a, b, p().fusions.get((a, b))]

    def ritual_cards(iid):
        ritual = int(iid)
        return [ritual] + [c for c in (p().rituals.get(ritual) or ()) if c]

    for tab, tree, cards_of in ((app.cards, app.cards.tree, None), (app.art, app.art.tree, None),
                                (app.fusions, app.fusions.tree, fusion_cards),
                                (app.equips, app.equips.equips, None), (app.equips, app.equips.monsters, None),
                                (app.rituals, app.rituals.tree, ritual_cards),
                                (app.duelists, app.duelists.tree, None), (app.duelists, app.duelists.fixed.tree, None),
                                (app.starter, app.starter.tree, None), (app.packs, app.packs.tree, None)):
        install(app, tab, tree, cards_of)


# --- Where it's used ------------------------------------------------------------

def open_target(app, target):
    """Where a line points, in the Tk window's tabs."""
    kind = target[0]
    if kind == "card":
        app.open_card(app.cards, target[1])
    elif kind == "fusions":
        app.open_card(app.fusions, target[1])
    elif kind == "equips":
        app.open_card(app.equips, target[1])
    elif kind == "rituals":
        app.open_card(app.rituals, target[1])
    elif kind == "pool":
        app.open_pool(target[1], target[2], target[3])
    elif kind == "starter":
        app.open_starter(target[1], target[2])
    elif kind == "pack":
        app.open_pack(target[1])


def uses(app, cid) -> list:
    """[(tab name, what, go)] of everything in the mod naming the card; go()
    shows it in its tab."""
    return [(where, what, None if target is None else (lambda t=target: open_target(app, t)))
            for where, what, target in where_used(app.project, cid)]


class UsesWindow(tk.Toplevel):
    """Where it's used: a window of its own beside the main one, listed again
    each time it comes to the front, so it follows the edits."""

    def __init__(self, app, cid):
        super().__init__(app)
        self.app, self.cid = app, cid
        self.transient(app)
        self.title(f"Where {app.project.card_label(cid)} is used")
        top = ttk.Frame(self, padding=(8, 8, 8, 0))
        top.pack(fill="x")
        self.summary = ttk.Label(top)
        self.summary.pack(side="left")
        ttk.Label(top, text="Double-click a line to go to it.", style="Hint.TLabel").pack(side="right")
        frame, self.tree = scrolled_tree(self, [("where", "Where"), ("what", "What")], [110, 440], 16)
        frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree.bind("<Double-1>", lambda e: self.go())
        self.tree.bind("<Return>", lambda e: self.go())
        ttk.Button(self, text="Close", command=self.destroy).pack(anchor="e", padx=8, pady=(0, 8))
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<FocusIn>", lambda e: self.fill() if e.widget is self else None)
        self.minsize(px(self, 420), px(self, 240))
        self.lines = []
        self.fill()
        self.tree.focus_set()

    def fill(self):
        if self.app.project is None or self.cid not in self.app.project.cards:
            self.destroy()
            return
        self.lines = uses(self.app, self.cid)
        self.tree.delete(*self.tree.get_children())
        for i, (where, what, _) in enumerate(self.lines):
            self.tree.insert("", "end", iid=str(i), values=(where, what))
        self.summary.configure(text=f"{len(self.lines)} uses" if self.lines else
                               "Nothing in the mod uses this card: no fusion, equip, ritual, deck, drop, pack or starter pool.")
        if self.lines:
            self.tree.selection_set("0")
            self.tree.focus("0")

    def go(self):
        selection = self.tree.selection()
        if selection and int(selection[0]) < len(self.lines) and self.lines[int(selection[0])][2]:
            self.lines[int(selection[0])][2]()
