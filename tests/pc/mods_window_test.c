/* Real loader/settings, fake font and restart: verify staged UI behavior. */
#define main original_mods_test
#include "pc/compat/fs.h"
#include "mods_test.c"
#undef main
#include "pc/platform/mods_window.h"
#include "pc/mods/overlap.h"
#include "zip_writer.h"
static int restarts;
int Menu_Scale(void) { return 1; }
static int test_touch; /* Menu_TouchTarget: 0 with a mouse */
int Menu_TouchTarget(void) { return test_touch; }
int Menu_TextWidthScaled(const char *s, int scale) { return (int)strlen(s) * 7 * scale; }
/* What a draw wrote, while `capture` is on: each string, its color and
 * the middle of its line (in the canvas it was drawn on). */
static int capture;
static char drawn[16384];
static int drawn_y(const char *part)
{
    const char *at = strstr(drawn, part), *line;
    if (!at) return -1;
    for (line = at; line > drawn && line[-1] != '\n'; line--) {
    }
    return atoi(line);
}
void Menu_DrawTextScaled(MenuCanvas *c, int x, int y, const char *s, uint32_t color, int scale)
{
    (void)c;
    (void)x;
    (void)scale;
    if (capture && strlen(drawn) + strlen(s) + 32 < sizeof(drawn))
        snprintf(drawn + strlen(drawn), sizeof(drawn) - strlen(drawn), "%d %06x %s\n", y, (unsigned)color, s);
}
static void draw(int w, int h)
{
    MenuCanvas canvas = {0};
    canvas.width = canvas.stride = w;
    canvas.height = h;
    canvas.pixels = calloc((size_t)w * h, 4);
    assert(canvas.pixels);
    drawn[0] = 0;
    capture = 1;
    ModsWindow_Draw(&canvas);
    capture = 0;
    free(canvas.pixels);
}
static char opened[1024];
int Platform_OpenFolder(const char *path)
{
    snprintf(opened, sizeof(opened), "%s", path);
    return 0;
}
int Platform_RestartGame(void)
{
    restarts++;
    return -1;
}
static int input(MenuEventType type, int x, int y, MenuKey key, const char *text)
{
    MenuEvent e = {0};
    e.type = type;
    e.x = x;
    e.y = y;
    e.button = 1;
    e.key = key;
    if (text)
        snprintf(e.text, sizeof(e.text), "%s", text);
    return ModsWindow_Event(&e);
}
static int click(int x, int y) { return input(MENU_EVENT_BUTTON_DOWN, x, y, MENU_KEY_OTHER, NULL); }
/* Import mod... with a file picker that answers at once with the .zip
 * the test wrote (ModsWindow_SetImport), and what the window then says. */
static char import_source[1024];
static int picks;
static int fake_pick(char *why, size_t size)
{
    (void)why;
    (void)size;
    picks++;
    return 0;
}
static int fake_picked(char *why, size_t size)
{
    (void)why;
    (void)size;
    return 1;
}
static int fake_fetch(char *path, size_t size, char *why, size_t why_size)
{
    (void)why;
    (void)why_size;
    snprintf(path, size, "%s", import_source);
    return 1;
}
static void tap_widget(int id)
{
    int x, y;
    assert(ModsWindow_Locate(id, &x, &y));
    click(x, y);
    input(MENU_EVENT_BUTTON_UP, x, y, MENU_KEY_OTHER, NULL);
}
/* Writes `items` as the picked .zip, taps Import mod... and runs the ticks
 * (the picker's answer, then the import); what the footer says. */
static const char *import_zip(const ZipItem *items, int n)
{
    static char said[4096];
    const char *line;
    write_zip(import_source, items, n);
    tap_widget(MODS_UI_FOLDER);
    while (ModsWindow_Tick()) {
    }
    draw(1600, 900);
    said[0] = 0;
    for (line = drawn; *line; line = strchr(line, '\n') + 1) {
        const char *text = strchr(strchr(line, ' ') + 1, ' ') + 1;
        size_t length = (size_t)(strchr(line, '\n') - text);
        if (strlen(said) + length + 2 < sizeof(said)) {
            strncat(said, text, length);
            strcat(said, " ");
        }
    }
    return said;
}
static int folder_has(const char *relative)
{
    char path[2048];
    struct stat info;
    snprintf(path, sizeof(path), "%s/%s", root, relative);
    return !stat(path, &info);
}
/* The panel on a phone or tablet (touch), as an Android app has it. */
static void test_import(void)
{
    static const ZipItem good[] = {{"Downloads/newmod/mod.json", "{\"id\": \"newmod\", \"name\": \"New mod\", "
                                                                "\"enabled\": true}", 1, 0, 0, 0, 0, 0},
                                   {"Downloads/newmod/name.txt", "hello", 1, 0, 0, 0, 0, 0}};
    static const ZipItem pc[] = {{"pcmod/mod.json", "{\"id\": \"pcmod\", \"name\": \"PC mod\", \"library\": "
                                                    "\"pcmod\"}", 0, 0, 0, 0, 0, 0},
                                 {"pcmod/pcmod.o", "ELF", 0, 0, 0, 0, 0, 0}};
    static const ZipItem arm[] = {{"armmod/mod.json", "{\"id\": \"armmod\", \"name\": \"Arm mod\", \"library\": "
                                                      "\"armmod\"}", 0, 0, 0, 0, 0, 0},
                                  {"armmod/armmod.o", "ELF", 0, 0, 0, 0, 0, 0},
                                  {"armmod/armmod.aarch64.o", "ELF", 0, 0, 0, 0, 0, 0}};
    static const ZipItem data[] = {{"datamod/mod.json", "{\"id\": \"datamod\", \"name\": \"Data mod\", "
                                                        "\"libraries\": {\"aarch64\": \"d.o\"}}", 0, 0, 0, 0, 0, 0}};
    static const ZipItem two[] = {{"m1/mod.json", "{\"name\": \"First\"}", 0, 0, 0, 0, 0, 0},
                                  {"m2/mod.json", "{\"name\": \"Second\"}", 0, 0, 0, 0, 0, 0}};
    static const ZipItem none[] = {{"readme.txt", "no mod here", 0, 0, 0, 0, 0, 0}};
    static const ZipItem slip[] = {{"newmod/../../escaped.txt", "x", 0, 0, 0, 0, 0, 0},
                                   {"newmod/mod.json", "{}", 0, 0, 0, 0, 0, 0}};
    int count = Mods_Count(), x, y, mod;
    const char *said;
    snprintf(import_source, sizeof(import_source), "%s/picked.zip", root);
    test_touch = 48;
    ModsWindow_SetImport(NULL, NULL, NULL);
    ModsWindow_Init();
    ModsWindow_Resize(1600, 900);
    assert(!ModsWindow_Locate(MODS_UI_FOLDER, &x, &y)); /* no picker: no button */
    ModsWindow_SetImport(fake_pick, fake_picked, fake_fetch);
    ModsWindow_Init();
    ModsWindow_Resize(1600, 900);
    said = import_zip(good, 2);
    assert(picks == 1 && strstr(said, "Imported New mod."));
    assert(Mods_Count() == count + 1 && (mod = find("newmod")) == count);
    assert(!Mods_Enabled(mod) && Settings_GetNamed("mod.newmod", 1) == 0); /* off, and off at the next launch */
    assert(folder_has("mods/newmod/name.txt") && !folder_has("picked.zip"));
    /* The same again: Replace or Cancel. */
    said = import_zip(good, 2);
    assert(strstr(said, "New mod is already installed. Replace it") && strstr(said, "Replace"));
    tap_widget(MODS_UI_CLOSE); /* Cancel */
    assert(Mods_Count() == count + 1 && folder_has("mods/newmod/name.txt") && !folder_has("picked.zip"));
    said = import_zip(good, 2);
    tap_widget(MODS_UI_APPLY); /* Replace */
    draw(1600, 900);
    assert(strstr(drawn, "Replaced New mod.") && Mods_Count() == count + 1);
    /* Code: imported, off; where the game has no code mod loader
     * (MEMORIES_NO_CODE_MODS, the arm64 Android game) said so whatever
     * objects it has, an arm64 one or not; with the loader, nothing to say.
     * "libraries" is no code to this loader: a data mod. */
    said = import_zip(pc, 2);
#ifdef MEMORIES_NO_CODE_MODS
    assert(strstr(said, "Imported PC mod. This mod has code, which the game cannot run in this build yet. "
                        "It stays off and changes nothing in the game."));
#else
    assert(strstr(said, "Imported PC mod.") && !strstr(said, "cannot run"));
#endif
    assert(!Mods_Enabled(find("pcmod")));
    said = import_zip(arm, 3);
#ifdef MEMORIES_NO_CODE_MODS
    assert(strstr(said, "Imported Arm mod. This mod has code, which the game cannot run in this build yet."));
#else
    assert(strstr(said, "Imported Arm mod.") && !strstr(said, "cannot run"));
#endif
    said = import_zip(data, 1);
    assert(strstr(said, "Imported Data mod.") && !strstr(said, "cannot run"));
    /* Several at once; none at all; a name that leaves the folder. */
    said = import_zip(two, 2);
    assert(strstr(said, "Imported 2 mods: First and Second.") && find("m1") >= 0 && find("m2") >= 0);
    /* One of them in place: its files are this launch's, so no Replace. */
    Mods_SetEnabled(find("m1"), 1);
    assert(Mods_Active(find("m1")));
    count = Mods_Count();
    said = import_zip(two, 2);
    assert(strstr(said, "First is in use, so its files cannot be replaced now.") && Mods_Count() == count);
    assert(folder_has("mods/m1/mod.json") && !folder_has("picked.zip"));
    /* A folder of that name with another mod in it: never replaced, the new
     * one gets a free name. */
    {
        static const ZipItem other[] = {{"mod05/mod.json", "{\"id\": \"other\", \"name\": \"Other\"}", 0, 0, 0, 0, 0, 0}};
        said = import_zip(other, 1);
        assert(strstr(said, "Imported Other.") && find("other") >= 0 && find("mod05") >= 0);
        assert(folder_has("mods/mod05-2/mod.json") && !strcmp(Mods_Id(find("mod05")), "mod05"));
        assert(strstr(Mods_Directory(find("other")), "mod05-2"));
    }
    {
        /* The free name is not another mod's of the same .zip: mod06 is
         * taken by another mod, and mod06-2 is the second mod's own. */
        static const ZipItem pair[] = {{"mod06/mod.json", "{\"id\": \"first6\", \"name\": \"First6\"}", 0, 0, 0, 0, 0, 0},
                                       {"Mod06-2/mod.json", "{\"id\": \"second6\", \"name\": \"Second6\"}", 0, 0, 0, 0, 0, 0}};
        said = import_zip(pair, 2);
        assert(strstr(said, "Imported 2 mods: ") && strstr(said, "First6") && strstr(said, "Second6"));
        assert(strstr(Mods_Directory(find("first6")), "mod06-3") && strstr(Mods_Directory(find("second6")), "Mod06-2"));
    }
    said = import_zip(none, 1);
    assert(strstr(said, "This .zip has no mod in it."));
    count = Mods_Count();
    said = import_zip(slip, 2);
    assert(strstr(said, "points outside its folder") && Mods_Count() == count);
    assert(!folder_has("escaped.txt") && !folder_has("mods/escaped.txt"));
    ModsWindow_SetImport(NULL, NULL, NULL);
    test_touch = 0;
}
/* menu.h's UTF-8 cuts: never inside a character. */
static void test_text_cuts(void)
{
    const char *word = "Portugu\xC3\xAAs"; /* "Português": ê is bytes 7-8 */
    char cut[16];
    assert(Menu_TextBack(word, 9) == 7);
    assert(Menu_TextBack(word, 7) == 6);
    assert(Menu_TextBack(word, 0) == 0);
    assert(Menu_TextFit(word, 8) == 7);
    assert(Menu_TextFit(word, 9) == 9);
    {
        /* Ends before `length`: a buffer that long, as a caller's is (gcc
         * reads the string literal's 11 bytes as out of bounds for 50). */
        static const char padded[64] = "Portugu\xC3\xAAs";
        assert(Menu_TextFit(padded, 50) == 10);
    }
    memcpy(cut, word, 8); /* "Portugu" and the first byte of ê */
    cut[8] = '\0';
    Menu_TextTrim(cut);
    assert(strcmp(cut, "Portugu") == 0);
    snprintf(cut, sizeof(cut), "%s", word);
    Menu_TextTrim(cut);
    assert(strcmp(cut, word) == 0);
    snprintf(cut, sizeof(cut), "a\xE2\x80");  /* a cut-short U+2014 */
    Menu_TextTrim(cut);
    assert(strcmp(cut, "a") == 0);
}
int main(void)
{
    char path[1024];
    int w, h;
    test_text_cuts();
    assert(scratch_dir(root, sizeof(root), "memories-mod-window"));
    make_dir("mods");
    for (int i = 0; i < 80; i++) {
        snprintf(path, sizeof(path), "mods/mod%02d", i);
        make_dir(path);
        snprintf(path, sizeof(path), "mods/mod%02d/mod.json", i);
        if (i == 2 || i == 3) { /* six fusion pairs both set: overlaps; mod03's first by its setting "on" */
            char json[2048] = "{\"settings\":[{\"key\":\"on\",\"type\":\"bool\",\"default\":1}],\"fusions\":[";
            for (int j = 0; j < 6; j++)
                snprintf(json + strlen(json), sizeof(json) - strlen(json), "%s{\"with\":[%d,%d],\"result\":%d%s}",
                         j ? "," : "", 100 + j, 200 + j, i, i == 3 && !j ? ",\"setting\":\"on\"" : "");
            strcat(json, "]}");
            write_text(path, json);
        } else if (i == 1) { /* more settings than the details show at once */
            char json[2048] = "{\"settings\":[";
            for (int j = 0; j < 12; j++)
                snprintf(json + strlen(json), sizeof(json) - strlen(json), "%s{\"key\":\"s%d\",\"type\":\"bool\"}",
                         j ? "," : "", j);
            strcat(json, "]}");
            write_text(path, json);
        } else if (i == 5) /* code, named only under "libraries" (an aarch64 entry) */
            write_text(path, "{\"libraries\":{\"aarch64\":\"other.aarch64.o\"}}");
        else
            write_text(path, i ? "{}"
                               : "{\"restart\":true,\"settings\":[{\"key\":\"speed\",\"label\":\"Speed\",\"default\":5,"
                                 "\"min\":0,\"max\":10}]}");
    }
    snprintf(path, sizeof(path), "%s/mods", root);
    setenv("MEMORIES_MODS_DIR", path, 1);
    snprintf(path, sizeof(path), "%s/settings.txt", root);
    setenv("MEMORIES_SETTINGS", path, 1);
    setenv("MEMORIES_USER_DIR", root, 1);
    Settings_Load();
    Mods_Load();
    assert(Mods_Count() == 80);
    assert(find("mod00") == 0);
    ModsWindow_Init();
    ModsWindow_Size(&w, &h);
    assert(w == 920 && h == 640);
    click(32, 160);
    assert(!Mods_Enabled(0)); /* staged */
    click(800, 610);
    assert(!restarts && !Mods_Enabled(0)); /* restart warning */
    click(680, 610);
    assert(!restarts); /* cancel warning */
    click(800, 610);
    click(800, 610);
    assert(restarts == 1 && Mods_Enabled(0));
    ModsWindow_Init();
    click(620, 238); /* settings tab */
    click(800, 357);
    input(MENU_EVENT_MOTION, 878, 357, MENU_KEY_OTHER, NULL);
    input(MENU_EVENT_BUTTON_UP, 878, 357, MENU_KEY_OTHER, NULL);
    assert(Mods_OptionValue(0, 0) == 5); /* slider edits are staged */
    click(800, 610);
    click(800, 610);
    assert(Mods_OptionValue(0, 0) == 10);
    click(790, 80); /* save Default profile */
    click(800, 165); /* disable */
    click(800, 610);
    click(800, 610);
    assert(!Mods_Enabled(0));
    click(860, 80);
    assert(!Mods_Enabled(0)); /* loading a profile is staged too */
    click(800, 610);
    click(800, 610);
    assert(Mods_Enabled(0) && Mods_OptionValue(0, 0) == 10);
    ModsWindow_Init();
    {
        /* Twelve settings scroll: by wheel, then by dragging the scrollbar. */
        int many = find("mod01");
        MenuEvent wheel = {0};
        wheel.type = MENU_EVENT_WHEEL;
        wheel.x = 600;
        wheel.y = 450;
        click(100, 142 + many * 58 + 20);
        click(620, 238);
        wheel.wheel = -1;
        for (int i = 0; i < 20; i++)
            ModsWindow_Event(&wheel);
        click(858, 505); /* the last setting's + */
        click(800, 610);
        assert(Mods_OptionValue(many, 11) == 1 && Mods_OptionValue(many, 0) == 0);
        wheel.wheel = 1;
        for (int i = 0; i < 20; i++)
            ModsWindow_Event(&wheel);
        click(889, 310);
        input(MENU_EVENT_MOTION, 889, 600, MENU_KEY_OTHER, NULL);
        input(MENU_EVENT_BUTTON_UP, 889, 600, MENU_KEY_OTHER, NULL);
        click(858, 505);
        click(800, 610);
        assert(Mods_OptionValue(many, 11) == 0 && Mods_OptionValue(many, 0) == 0);
    }
    ModsWindow_Init();
    click(50, 80);
    input(MENU_EVENT_TEXT, 0, 0, MENU_KEY_OTHER, "mod79");
    click(32, 160);
    click(800, 610);
    assert(Mods_Enabled(find("mod79"))); /* search actually filters */
    ModsWindow_Init();
    click(32, 160);
    assert(!input(MENU_EVENT_KEY_DOWN, 0, 0, MENU_KEY_ESCAPE, NULL));
    assert(input(MENU_EVENT_KEY_DOWN, 0, 0, MENU_KEY_ENTER, NULL)); /* explicit discard */
    assert(Mods_Enabled(0));
    ModsWindow_Init();
    click(50, 80); /* a focused search field does not hold the window open */
    assert(ModsWindow_RequestClose());
    ModsWindow_Init();
    click(32, 160);
    assert(!ModsWindow_RequestClose()); /* unsaved changes: asks first */
    assert(ModsWindow_RequestClose());  /* the second close discards */
    {
        MenuEvent motion = {0};
        motion.type = MENU_EVENT_MOTION;
        assert(!ModsWindow_Redraws(&motion)); /* plain pointer motion draws nothing */
    }
    ModsWindow_Init();
    click(550, 600); /* Open mods folder: the folder new mods are installed in */
    assert(!strcmp(opened, getenv("MEMORIES_MODS_DIR")));
    {
        /* What two enabled mods both change: in the header, and by kind in
         * the Compatibility tab, the first few lines, then the rest on a
         * press. The load order staged in the window decides who wins. */
        int more;
        ModsWindow_Init();
        click(32, 142 + 2 * 58 + 20); /* mod02 and mod03, staged */
        click(32, 142 + 3 * 58 + 20);
        click(800, 238); /* Compatibility */
        draw(920, 640);
        assert(strstr(drawn, "/  6 overlaps")); /* with the warnings when the line has room */
        assert(strstr(drawn, "Fusions: 6 (6 warnings)"));
        assert(strstr(drawn, "f4bd6a Fusion #100 + #200 (mod02, mod03): mod03 wins (later in load order)") ||
               strstr(drawn, "(mod02, mod03): mod03 wins (later in load order)"));
        assert(strstr(drawn, "...and 2 more: show them") && !strstr(drawn, "#105 + #205"));
        more = drawn_y("...and 2 more");
        click(600, 142 + 124 + more);
        draw(920, 640);
        assert(strstr(drawn, "#105 + #205") && strstr(drawn, "Show fewer"));
        click(100, 142 + 2 * 58 + 20); /* mod02 selected, and loaded after mod03 */
        click(856 + 14, 186 + 13);
        draw(920, 640);
        assert(strstr(drawn, "(mod03, mod02): mod02 wins (later in load order)"));
        click(32, 142 + 3 * 58 + 20); /* one of them off: nothing in common */
        draw(920, 640);
        assert(!strstr(drawn, "overlap") && strstr(drawn, "Enable this mod"));
        {
            /* A setting staged in the window, before Apply, switches mod03's
             * first fusion off: one overlap fewer. */
            int both[MODS_MAX] = {0}, off = 0, on = 1;
            const int *staged[MODS_MAX] = {0};
            both[2] = both[3] = 1;
            staged[3] = &on;
            assert(Mods_OverlapCount(Mods_Overlaps(both, NULL, staged)) == 6);
            staged[3] = &off;
            assert(Mods_OverlapCount(Mods_Overlaps(both, NULL, staged)) == 5);
            assert(Mods_OverlapCount(Mods_Overlaps(both, NULL, NULL)) == 6); /* saved: its default, on */
        }
    }
    {
        /* With a finger, every press ModsWindow_Grabs hands over as held
         * is the list scrollbar's: none beside it opens the row's page. */
        int x, y, grabbed = 0;
        test_touch = 48;
        ModsWindow_Init();
        ModsWindow_Resize(600, 400); /* a phone: two pages */
        draw(600, 400);
        assert(ModsWindow_Locate(MODS_UI_ROW_FIRST, &x, &y) && !ModsWindow_Locate(MODS_UI_BACK, &x, &x));
        for (x = 599; x >= 300; x--) {
            if (!ModsWindow_Grabs(x, y))
                continue;
            grabbed++;
            click(x, y);
            input(MENU_EVENT_BUTTON_UP, x, y, MENU_KEY_OTHER, NULL);
            assert(!ModsWindow_Locate(MODS_UI_BACK, &w, &h)); /* still the list */
        }
        assert(grabbed > 10);
        test_touch = 0;
    }
    test_import();
    ModsWindow_Init();
    {
        /* The Details tab calls a mod with only "libraries" a code mod, as
         * the loader does; one with neither key a content mod. */
        click(100, 142 + find("mod05") * 58 + 20);
        draw(920, 640);
        assert(strstr(drawn, "Native code mod") && !strstr(drawn, "Content mod"));
        click(100, 142 + find("mod04") * 58 + 20);
        draw(920, 640);
        assert(strstr(drawn, "Content mod") && !strstr(drawn, "Native code mod"));
    }
    ModsWindow_Init();
    ModsWindow_Resize(720, 480);
    ModsWindow_Size(&w, &h);
    assert(w == 720 && h == 480);
    MenuCanvas canvas = {0};
    canvas.width = w;
    canvas.height = h;
    canvas.stride = w;
    canvas.pixels = calloc((size_t)w * h, 4);
    assert(canvas.pixels);
    ModsWindow_Draw(&canvas);
    free(canvas.pixels);
    return 0;
}
