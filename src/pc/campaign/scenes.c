#include "scenes.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>

#define STORY_SCENES 1024
#define STORY_STACK 32
#define STORY_COMMANDS 16384
#define STORY_VARIABLES 256
struct StoryScene {
    char mod[64];
    const char *id;
    int retail, count;
    const JsonValue **commands;
    const JsonValue *assets, *dialogue;
};
typedef struct { int scene, pc; } Frame;
struct StoryRunner {
    StoryHost host;
    StoryScene scenes[STORY_SCENES];
    int count, depth, active, pending;
    Frame stack[STORY_STACK];
    struct { const char *id; long value; } variables[STORY_VARIABLES];
    int variable_count;
    unsigned char operands[6];
    int opcode, operand_count;
    const char *text;
    char error[256];
};
static const char *str(const JsonValue *v, const char *k) { return Json_String(Json_Member(v, k), ""); }
static int fail(StoryRunner *r, const char *why) {
    snprintf(r->error, sizeof r->error, "%s", why);
    r->active = 0;
    return -2;
}
const char *Story_Error(const StoryRunner *r) { return r->error; }
StoryRunner *Story_Create(StoryHost host) {
    StoryRunner *r = calloc(1, sizeof *r);
    if (r) r->host = host;
    return r;
}
void Story_Destroy(StoryRunner *r) {
    if (!r) return;
    for (int i = 0; i < r->count; ++i) free(r->scenes[i].commands);
    free(r);
}
static long number(const JsonValue *v, long fallback) {
    const char *s = Json_String(v, NULL);
    if (s && *s) {
        char *end;
        long n = strtol(s, &end, 0);
        if (!*end) return n;
    }
    return Json_TypeOf(v) == JSON_NUMBER ? Json_Number(v, fallback) : fallback;
}
static int operand_length(int op, const unsigned char *p, int n) {
    static const int sizes[] = {0,2,2,4,2,0,6,0,1,2,3,1,2,4,0,0,1,2,0,0,2,2,0};
    if (op < 0 || op > 22) return -1;
    if ((op == 1 || op == 4) && n >= 2) return p[1] & 128 ? 6 : 2;
    if (op == 3 && n >= 2) return p[1] & 64 ? 2 : 4;
    if (op == 10 && n >= 1) return !(p[0] & 63) || (p[0] & 2) ? 3 : 1;
    return sizes[op];
}
static int native_bytes(const JsonValue *c, int *op, unsigned char *p) {
    const JsonValue *a = Json_Member(c, "operands");
    int n = Json_Count(a);
    *op = (int)number(Json_Member(c, "opcode"), -1);
    if (*op < 0 || *op > 22 || n > 6 || Json_TypeOf(a) != JSON_ARRAY) return -1;
    for (int i = 0; i < n; ++i) {
        long value = number(Json_At(a, i), -1);
        if (value < 0 || value > 255) return -1;
        p[i] = (unsigned char)value;
    }
    return operand_length(*op, p, n) == n ? n : -1;
}
static int find_scene(StoryRunner *r, const char *mod, const char *id) {
    (void)mod;
    for (int i = r->count - 1; i >= 0; --i) {
        StoryScene *s = &r->scenes[i];
        if (!strcmp(s->id, id)) return i;
        char qualified[256];
        snprintf(qualified, sizeof qualified, "%s:%s", s->mod, s->id);
        if (!strcmp(qualified, id)) return i;
    }
    return -1;
}
static int label(StoryScene *s, const char *id) {
    for (int i = 0; i < s->count; ++i)
        if (!strcmp(str(s->commands[i], "command"), "label") &&
            !strcmp(str(s->commands[i], "id"), id)) return i;
    return -1;
}
static int offset(StoryScene *s, long at) {
    for (int i = 0; i < s->count; ++i)
        if (number(Json_Member(s->commands[i], "offset"), -1) == at) return i;
    return -1;
}
static int known(const char *k) {
    static const char *kinds[] = {"retail_command", "label", "jump", "call_scene", "return",
        "wait", "dialogue", "background", "music", "sound", "stop_music", "camera",
        "set_flag", "set_variable", "if", "teleport", "game_over", "credits", "main_menu"};
    for (size_t i = 0; i < sizeof kinds / sizeof *kinds; ++i) if (!strcmp(k, kinds[i])) return 1;
    return 0;
}
int Story_Add(StoryRunner *r, const char *mod, const JsonValue *scenes,
              const JsonValue *assets, const JsonValue *dialogue) {
    int before = r->count;
    if (Json_TypeOf(scenes) != JSON_ARRAY) return fail(r, "Scene document must be an array");
    for (const JsonValue *v = Json_At(scenes, 0); v; v = Json_Next(v)) {
        StoryScene s = {0};
        if (r->count == STORY_SCENES || !*str(v, "id")) goto invalid;
        s.id = str(v, "id");
        s.retail = (int)number(Json_Member(v, "scene_number"), -1);
        if (s.retail < -1 || s.retail > 255 || strlen(mod) >= sizeof s.mod) goto invalid;
        snprintf(s.mod, sizeof s.mod, "%s", mod);
        s.assets = assets; s.dialogue = dialogue;
        const char *phases[] = {"on_start", "commands", "on_end"};
        for (int p = 0; p < 3; ++p) {
            const JsonValue *a = Json_Member(v, phases[p]);
            if (a && Json_TypeOf(a) != JSON_ARRAY) goto invalid;
            s.count += Json_Count(a);
        }
        if (s.count > STORY_COMMANDS) goto invalid;
        s.commands = calloc((size_t)s.count + 1, sizeof *s.commands);
        if (!s.commands) goto invalid;
        int at = 0;
        for (int p = 0; p < 3; ++p)
            for (const JsonValue *c = Json_At(Json_Member(v, phases[p]), 0); c; c = Json_Next(c)) {
                if (!known(str(c, "command"))) { free(s.commands); goto invalid; }
                if (!strcmp(str(c, "command"), "retail_command")) {
                    unsigned char bytes[6] = {0}; int op;
                    if (native_bytes(c, &op, bytes) < 0) { free(s.commands); goto invalid; }
                }
                s.commands[at++] = c;
            }
        r->scenes[r->count++] = s;
    }
    return r->count - before;
invalid:
    while (r->count > before) free(r->scenes[--r->count].commands);
    return fail(r, "Invalid scene, unsupported command, or malformed native operands");
}
int Story_Start(StoryRunner *r, int retail) {
    r->active = r->pending = r->depth = r->variable_count = 0;
    r->error[0] = 0;
    for (int i = r->count - 1; i >= 0; --i) if (r->scenes[i].retail == retail) {
        r->stack[0] = (Frame){i, 0}; r->depth = r->active = 1; return 1;
    }
    return 0;
}
static long variable(StoryRunner *r, const char *id, long value, int write) {
    for (int i = 0; i < r->variable_count; ++i) if (!strcmp(r->variables[i].id, id)) {
        if (write) r->variables[i].value = value;
        return r->variables[i].value;
    }
    if (write && r->variable_count < STORY_VARIABLES) {
        r->variables[r->variable_count].id = id;
        r->variables[r->variable_count++].value = value;
    }
    return 0;
}
static int jump(StoryRunner *r, Frame *f, int to) {
    if (to < 0) return fail(r, "Unresolved scene label or retail branch offset");
    f->pc = to; return 1;
}
static void word(unsigned char *p, long value) { p[0] = (unsigned char)value; p[1] = (unsigned char)(value >> 8); }
static long asset(StoryScene *s, const JsonValue *c, const char *group) {
    const JsonValue *v = Json_Member(c, "id");
    long n = number(v, -1);
    if (n >= 0) return n;
    const JsonValue *a = Json_Member(Json_Member(s->assets, group), Json_String(v, ""));
    return number(Json_Member(a, "retail_id"),
                  number(Json_Member(a, "repaint"), number(a, -1)));
}
int Story_Tick(StoryRunner *r) {
    if (!r->active) return 0;
    for (int budget = 0; budget < 128; ++budget) {
        if (r->pending) {
            int result = r->host.native(r->host.context, r->opcode, r->operands,
                                        r->operand_count, r->text, 0);
            if (result == 0) return 1;
            r->pending = 0;
            if (result < 0) { r->active = 0; return result; }
        }
        if (!r->depth) { r->active = 0; return 0; }
        Frame *f = &r->stack[r->depth - 1];
        StoryScene *s = &r->scenes[f->scene];
        if (f->pc >= s->count) { --r->depth; continue; }
        const JsonValue *c = s->commands[f->pc++];
        const char *k = str(c, "command");
        if (!strcmp(k, "label")) continue;
        if (!strcmp(k, "return")) { --r->depth; continue; }
        if (!strcmp(k, "call_scene")) {
            int to = find_scene(r, s->mod, str(c, "scene"));
            if (to < 0 || r->depth == STORY_STACK) return fail(r, "Missing called scene or call stack limit");
            r->stack[r->depth++] = (Frame){to, 0}; continue;
        }
        if (!strcmp(k, "jump")) {
            if (jump(r, f, label(s, str(c, "to"))) < 0) return -2;
            continue;
        }
        if (!strcmp(k, "set_variable")) {
            variable(r, str(c, "id"), number(Json_Member(c, "value"), 0), 1); continue;
        }
        if (!strcmp(k, "if")) {
            const JsonValue *t = Json_Member(c, "test");
            const char *kind = str(t, "kind");
            int yes;
            if (!strcmp(kind, "always")) yes = 1;
            else if (!strcmp(kind, "flag")) yes = r->host.flag(r->host.context, (int)number(Json_Member(t, "id"), 0)) == Json_Bool(Json_Member(t, "value"), 1);
            else if (!strcmp(kind, "variable")) yes = variable(r, str(t, "id"), 0, 0) == number(Json_Member(t, "value"), 0);
            else return fail(r, "Unsupported condition kind");
            const char *to = str(c, yes ? "then" : "else");
            if (*to && jump(r, f, label(s, to)) < 0) return -2;
            continue;
        }
        int op = -1, n = 0;
        unsigned char *p = r->operands;
        memset(p, 0, 6); r->text = NULL;
        if (!strcmp(k, "retail_command")) {
            n = native_bytes(c, &op, p);
            if (n < 0) return fail(r, "Invalid native command");
            if (op == 0 || op == 14 || op == 15) { --f->pc; return 1; } /* retail halt */
            int branch = op == 12 || op == 21 || (op == 3 && !(p[1] & 64));
            if (branch) {
                int taken = op == 12 || (op == 21 ? !r->host.deck_complete(r->host.context) :
                    r->host.flag(r->host.context, p[0] | p[1] << 8));
                if (taken) {
                    int at = op == 3 ? 2 : 0;
                    const JsonValue *target = Json_At(Json_Member(c, "branch_targets"), 0);
                    int dest = *str(target, "label") ? label(s, str(target, "label")) : offset(s, p[at] | p[at + 1] << 8);
                    if (jump(r, f, dest) < 0) return -2;
                    continue;
                }
            }
            const JsonValue *next = Json_Member(c, "fallthrough_offset");
            if (next && jump(r, f, offset(s, number(next, -1))) < 0) return -2;
            if (branch) continue;
        } else if (!strcmp(k, "wait")) {
            long frames = number(Json_Member(c, "frames"), 30);
            if (frames < 0 || frames > 32767) return fail(r, "wait.frames must be 0..32767");
            if (!frames) continue;
            op = 20; n = 2; word(p, frames);
        } else if (!strcmp(k, "dialogue")) {
            long id = number(Json_Member(c, "dialogue_id"), -1);
            r->text = Json_String(Json_Member(c, "text"), NULL);
            if (!r->text) r->text = Json_String(Json_Member(s->dialogue, str(c, "text_id")), NULL);
            if (!r->text && (id < 0 || id > 4095)) return fail(r, "Dialogue needs text, a resolved text_id, or dialogue_id");
            op = 2; n = 2; word(p, r->text ? 0xFFF : id);
        } else if (!strcmp(k, "background") || !strcmp(k, "music") || !strcmp(k, "sound")) {
            long id = asset(s, c, !strcmp(k, "background") ? "backgrounds" : "audio");
            if (id < 0 || id > (!strcmp(k, "background") ? 4095 : 65535)) return fail(r, "Asset needs a valid retail_id binding");
            if (!strcmp(k, "background")) { op = 1; n = 2; word(p, id); }
            else { op = 10; n = 3; p[0] = !strcmp(k, "sound") ? 64 : 0; word(p + 1, id); }
        } else if (!strcmp(k, "stop_music")) { op = 11; n = 1; }
        else if (!strcmp(k, "camera")) {
            long frames = number(Json_Member(c, "frames"), 1);
            if (frames < 1 || frames > 32767) frames = 1;
            op = 6; n = 6; word(p, number(Json_Member(c, "x"), 0));
            word(p + 2, number(Json_Member(c, "y"), 0)); word(p + 4, frames);
        } else if (!strcmp(k, "set_flag")) {
            long id = number(Json_Member(c, "id"), -1);
            if (id < 0 || id > 2047) return fail(r, "Flag ID must be 0..2047");
            op = 3; n = 2; word(p, id | 0x4000 | (Json_Bool(Json_Member(c, "value"), 1) ? 0 : 0x8000));
        } else if (!strcmp(k, "teleport")) {
            long id = number(Json_Member(c, "place"), -1);
            if (id < 0 || id > 255) return fail(r, "place must be a retail location number");
            op = 8; n = 1; p[0] = (unsigned char)id;
        } else if (!strcmp(k, "game_over")) op = 18;
        else if (!strcmp(k, "credits")) op = 19;
        else if (!strcmp(k, "main_menu")) op = 22;
        if (op < 0 || !r->host.native) return fail(r, "Unsupported runtime command");
        r->opcode = op; r->operand_count = n;
        int result = r->host.native(r->host.context, op, p, n, r->text, 1);
        if (result < 0) { r->active = 0; return result; }
        if (!result) { r->pending = 1; return 1; }
    }
    return 1;
}
