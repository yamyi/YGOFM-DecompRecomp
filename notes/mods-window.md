# Mod manager

**Game > Mods** opens a resizable library. Search names, IDs or authors; cycle
All / Enabled / Disabled / Issues to filter the list. The list and the detail
pane scroll independently. The window fits the desktop, and adapts its local
text scale when resized. SDL and X11 use the same drawing and input code.

Select a mod to see its description, author, version, source directory, current
runtime status and native-code/content classification. The Settings tab renders
the mod's declared integer sliders, toggles, choices and pad-button bindings,
one block each: the label beside `-` value `+`, the description wrapped under
them, then an integer's slider. The value box is sized for the widest value the
setting can take, so choices are never cut off; clicking it steps forward.
Restore defaults (above the list, which scrolls under it) resets the selected
mod's staged settings. Compatibility lists requirements, ordering constraints
and declared conflicts, then everything the mod changes that another enabled
mod changes too, by kind with counts: the first four lines of each, **and N
more** to show the rest (up to 200), a warning where only one mod's change is
used and a dim line where they add up, agree or follow an `after`; a line
about the mod alone (its starter pools that the game leaves out with these
mods enabled) is counted apart, as left out rather than changed by another
mod; the header counts the overlaps between all enabled mods ([When mods
overlap](modding.md#when-mods-overlap)). They follow the enabled set, the
order and the settings staged in the window; a setting that needs a restart
counts there as staged (or as saved), so after **Apply changes** the list
shows the next launch, not the session still running with the old value. Lower Order values load first, subject to
dependencies.

Changes are staged until **Apply changes**. Restart-only changes share one
confirmation; restarting discards unsaved game progress. Close/Escape asks before
discarding staged edits; the title-bar close button asks once, and a second
click discards. Only settings edited in the window are written; an untouched
mod's order keeps following its manifest `priority`. A failed restart keeps the saved preferences for the
next launch. Active, inactive, pending, warning and error states are distinct.
Changing a load-order value requires a restart. New directories are discovered
on the next launch; native objects stay resident until exit.
A live mod that requires a restart-only mod which is not in place yet waits for
the same restart, and Apply offers it. Game > Reload settings follows the same
rule: it records restart-only mods without putting them in place or taking them
out. A mod that failed to go in place (a missing replacement file, say) is
tried again after it is removed and applied again.

A warning is text beside a mod that is still applied: manifest keys the game
does not know (with the key it most likely meant), `enabled`/`restart` that are
not booleans, another folder with the same id, a replacement larger than the
file it replaces, and texture pack entries that were left out, counted, with
the first file named.
**Open mods folder** shows the folder new mods go in (`MEMORIES_MODS_DIR`, else
the user `mods` folder, created if missing) in the system file manager.

The profile field accepts a name (letters, digits, spaces, `_`, `-`). Save writes
the currently applied preferences to `mod-profiles/<name>.txt` in the user
directory. Load stages that profile for inspection; it does not change the
running game. Profiles include declared option values and load-order settings.
Apply edits before saving a profile. Profiles do not copy the mods themselves.

Keyboard: Up/Down select a mod; Left/Right disable/enable; Enter toggles; Tab
focuses search, then the profile name, then the list. Escape leaves text entry,
cancels a confirmation, or closes the window. The mouse wheel scrolls whichever
pane is under the pointer. Both panes show a scrollbar when their contents do
not fit: drag its thumb, or press the track to jump there. The details scroll by
pixels, so every tab (About, Settings, Compatibility) reaches its last line;
integer sliders support dragging.

**On a phone or tablet** (Android) the window is a panel inside the game's
window (`panel.h`; [Android](pc-build.md#mods-and-controls-as-panels-inside-the-window)):
the same code at the screen's density, every row and button at least 48 dp
tall, no title or keyboard hints (the counts take the message line while
there is no message), and, where the list and the details do not fit side
by side, two pages: the list, and a mod's page (Back, load order, Enabled,
the tabs) that a tap on its row opens; the [x] at a row's left switches the
mod without opening it. A drag scrolls the list or the details; a slider
follows the finger. Search and the profile name show the on-screen keyboard
(its Enter ends the typing); Back is Escape. There is no Open mods folder
(an app has no folder window to open; `Platform_OpenFolder` fails on
Android): the player's mods go in `mods/` in the app's files folder
(`Android/data/org.yfmredecomp.game/files`). Importing a mod's `.zip`
through the system's file picker is not there yet; its button is to go in
the footer left of Close (`layout_touch`'s `folder` slot, empty now, so the
message line runs up to Close). Apply & restart starts the app
again in a new process. The game is paused while the panel shows.

Implementation: `src/pc/platform/mods_window.c`, `src/pc/mods/manager.c`
(`src/pc/mods/overlap.c` for the overlaps), and
window ownership in `sdl.c` / `x11.c`. `pc_mods_window` exercises real settings
and manifests with a fake renderer/restart. `tools/pc/test_mods_context.sh`
checks actual SDL/OpenGL context ownership during secondary-window operations.
`tools/pc/preview_mods.sh` renders the window with the real font and the
repository's `mods/` to `tmp/pc/mods-*.ppm` for review (`PREVIEW_SCALE=2` for
the doubled UI); `tools/pc/preview_panels.sh` renders the window at both
scales and, with `PREVIEW_TOUCH=1`, the panel on six phones and tablets.
