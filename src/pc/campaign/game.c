/* PC adapter: reuse the game's asynchronous command handlers, without asking
 * Script_RunTick to fetch a byte after the JSON command's operand buffer. */
#define MAIN_MODE_STATE_NEXT_AS_SCALAR
#define MAIN_MODE_STATE_ACTIVE_AS_SCALAR
#define D_800EB12C_IN_DATA
#include "scenes.h"
#include "pc/mods/mods.h"
#include "pc/platform/paths.h"
#include "pc/text/glyphs.h"
#include "game/script_state.h"
#include "game/script_command_table.h"
#include "game/script_op_show_dialog.h"
#include "game/script_op_save_prompt.h"
#include "game/script_op_return_to_menu.h"
#include "game/campaign_flags.h"
#include "game/duel_effect.h"
#include "game/func_80039794.h"
#include "game/main_mode_state.h"
#include "pc/compat/fs.h"
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static StoryRunner *runner;
static int built, running;
static unsigned char operands[6];
static unsigned char *dialogue;
/* Parsed documents live as long as the registry's borrowed command pointers. */
static JsonDocument **documents;
static size_t document_count;

const unsigned char *StoryGame_Text(int id) {
    return running && id == 0xFFF ? dialogue : NULL;
}
static int encode(const char *text) {
    free(dialogue); dialogue = NULL;
    if (!text) return 1;
    size_t length = strlen(text), n = 0;
    if (length > 16384) return 0;
    dialogue = malloc(length * 2 + 3);
    if (!dialogue) return 0;
    while (*text) {
        uint32_t ch = Glyphs_NextCharacter(&text);
        if (ch == GLYPHS_NOT_UTF8) return 0;
        if (ch == '\n') { dialogue[n++] = 0xFE; continue; }
        int code = ch == ' ' ? 0 : Glyphs_Code(ch);
        if (code < 0) return 0;
        if (code >= 0xF0) dialogue[n++] = (unsigned char)(0xF0 + (code >> 8));
        dialogue[n++] = (unsigned char)code;
    }
    dialogue[n++] = 0xFA; /* page advance before closing */
    dialogue[n] = 0xFF;
    return 1;
}
static int native(void *ctx, int opcode, const unsigned char *p, int count,
                  const char *text, int begin) {
    (void)ctx;
    if (begin) {
        if (opcode < 0 || opcode > 22 || count < 0 || count > 6 || !encode(text)) return -2;
        memcpy(operands, p, (size_t)count);
        D_8009B290 = operands;
        D_8009B27C = (u16)opcode;
        D_8009B28C = 0;
    }
    if (D_8009B2A4 & DUEL_EVENT_SCRIPT_FLAG_DIALOG_ACTIVE) {
        func_80039794();
        if ((D_800EB12C & TEXT_BOX_COMPLETION_MASK) == TEXT_BOX_FLAG_DONE)
            D_8009B2A4 &= ~DUEL_EVENT_SCRIPT_FLAG_DIALOG_ACTIVE;
        return 0;
    }
    if (D_8009B28C) D_8009B27C = D_8009B28C;
    unsigned op = D_8009B27C & 31;
    if (op > 22) return -2;
    D_80090C50[op]();
    if (!(D_8009B26C & 0x40)) return -1;
    return D_8009B27C == 0;
}
static int flag(void *ctx, int id) { (void)ctx; return Campaign_TestStoryFlag(id) != 0; }
static int deck(void *ctx) { (void)ctx; return Duel_IsPlayerDeckComplete() != 0; }
static const JsonValue *read_json(const char *mod, const char *path, int optional) {
    char error[256];
    if (optional) { FILE *file = fopen(path, "rb"); if (!file) return NULL; fclose(file); }
    JsonDocument *doc = Json_ParseFile(path, error, sizeof error);
    if (!doc) { Mods_Note(mod, "story: %s: %s", path, error); return NULL; }
    JsonDocument **more = realloc(documents, (document_count + 1) * sizeof *more);
    if (!more) { Json_Free(doc); Mods_Note(mod, "story: out of memory"); return NULL; }
    documents = more; documents[document_count++] = doc;
    return Json_Root(doc);
}
static int compare(const void *a, const void *b) { return strcmp(*(char *const *)a, *(char *const *)b); }
static void load(void) {
    if (built) return;
    built = 1;
    runner = Story_Create((StoryHost){native, flag, deck, NULL});
    if (!runner) return;
    for (int i = 0; i < Mods_LoadedCount(); ++i) {
        int mod = Mods_Loaded(i);
        if (!Mods_Active(mod)) continue;
        const JsonValue *entry = Json_Member(Mods_Manifest(mod), "story");
        if (!entry) continue;
        const char *folder = Json_String(entry, NULL), *owner = Mods_Id(mod);
        char root[4096], path[4096];
        if (!folder || !Paths_Contained(folder) ||
            snprintf(root, sizeof root, "%s/%s", Mods_Directory(mod), folder) >= (int)sizeof root) {
            Mods_Note(owner, "story must name a folder inside the mod"); continue;
        }
        DIR *dir = opendir(root);
        if (!dir) { Mods_Note(owner, "story: cannot open %s", root); continue; }
        char **names = NULL; size_t count = 0;
        struct dirent *de;
        while ((de = readdir(dir))) {
            size_t n = strlen(de->d_name);
            if (n < 5 || strcmp(de->d_name + n - 5, ".json") || !strcmp(de->d_name, "assets.json")) continue;
            char **more = realloc(names, (count + 1) * sizeof *more);
            if (!more) break;
            names = more; names[count] = malloc(n + 1);
            if (!names[count]) break;
            memcpy(names[count++], de->d_name, n + 1);
        }
        closedir(dir);
        if (count > 1) qsort(names, count, sizeof *names, compare);
        const JsonValue *assets = NULL, *lines = NULL;
        if (snprintf(path, sizeof path, "%s/assets.json", root) < (int)sizeof path) assets = read_json(owner, path, 1);
        if (snprintf(path, sizeof path, "%s/dialogue/en.json", root) < (int)sizeof path) lines = read_json(owner, path, 1);
        for (size_t j = 0; j < count; ++j) {
            if (snprintf(path, sizeof path, "%s/%s", root, names[j]) < (int)sizeof path) {
                const JsonValue *v = read_json(owner, path, 0);
                if (v && Story_Add(runner, owner, v, assets, lines) < 0)
                    Mods_Note(owner, "story: %s: %s", names[j], Story_Error(runner));
            }
            free(names[j]);
        }
        free(names);
    }
}
void StoryGame_Start(int retail_scene) {
    load();
    running = runner && Story_Start(runner, retail_scene);
    if (running) {
        D_8009B2A4 = DUEL_EVENT_SCRIPT_FLAG_STARTED;
        D_8009B27C = D_8009B28C = 0;
    }
}
int StoryGame_Tick(void) {
    if (!running) return 0;
    int result = Story_Tick(runner);
    if (result <= 0) {
        if (result == -2) fprintf(stderr, "memories-pc: story: %s\n", Story_Error(runner));
        running = 0;
        D_8009B2A4 = D_8009B27C = D_8009B28C = 0;
        /* A scene with no explicit destination returns to the frontend. */
        if (result != -1) Script_OpReturnToMenu();
    }
    return 1;
}
