#include "pc/campaign/scenes.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static int ops[128], values[128], count, polls, flag_value;
static char last_text[128];
static int execute(void *ctx, int op, const unsigned char *p, int n, const char *text, int begin) {
    (void)ctx;
    if (!begin) { ++polls; return 1; }
    assert(count < 128);
    ops[count] = op; values[count++] = n >= 2 ? p[0] | p[1] << 8 : 0;
    if (text) snprintf(last_text, sizeof last_text, "%s", text);
    return op == 20 ? 0 : 1;
}
static int flag(void *ctx, int id) { (void)ctx; (void)id; return flag_value; }
static int deck(void *ctx) { (void)ctx; return 1; }
static JsonDocument *parse(const char *text) {
    char error[256]; JsonDocument *d = Json_Parse(text, error, sizeof error);
    if (!d) fprintf(stderr, "%s\n", error);
    assert(d); return d;
}
int main(void) {
    StoryRunner *r = Story_Create((StoryHost){execute, flag, deck, NULL});
    assert(r && !Story_Start(r, 48));
    JsonDocument *d = parse("["
        "{\"id\":\"intro\",\"scene_number\":48,\"on_start\":[{\"command\":\"wait\",\"frames\":2}],"
        "\"commands\":[{\"command\":\"call_scene\",\"scene\":\"shop\"},"
        "{\"command\":\"dialogue\",\"text\":\"Back\"}],\"on_end\":[{\"command\":\"wait\",\"frames\":3}]},"
        "{\"id\":\"shop\",\"commands\":[{\"command\":\"dialogue\",\"text\":\"Welcome\"},"
        "{\"command\":\"return\"},{\"command\":\"wait\",\"frames\":99}]}]");
    assert(Story_Add(r, "mod", Json_Root(d), NULL, NULL) == 2);
    assert(Story_Start(r, 48));
    assert(Story_Tick(r) == 1 && count == 1);
    assert(Story_Tick(r) == 1 && count == 4 && polls == 1);
    assert(!strcmp(last_text, "Back"));
    assert(Story_Tick(r) == 0 && polls == 2);
    assert(values[0] == 2 && values[3] == 3);

    JsonDocument *branch = parse("[{\"id\":\"branch\",\"scene_number\":48,\"commands\":["
        "{\"command\":\"retail_command\",\"opcode\":3,\"operands\":[1,0,32,0],\"offset\":\"0x10\",\"fallthrough_offset\":\"0x15\"},"
        "{\"command\":\"retail_command\",\"opcode\":20,\"operands\":[7,0],\"offset\":\"0x20\",\"fallthrough_offset\":\"0x30\"},"
        "{\"command\":\"retail_command\",\"opcode\":20,\"operands\":[4,0],\"offset\":\"0x15\",\"fallthrough_offset\":\"0x30\"},"
        "{\"command\":\"return\",\"offset\":\"0x30\"}]}]");
    assert(Story_Add(r, "later", Json_Root(branch), NULL, NULL) == 1);
    count = 0; flag_value = 1;
    assert(Story_Start(r, 48) && Story_Tick(r) == 1 && values[0] == 7);
    assert(Story_Tick(r) == 0);
    count = 0; flag_value = 0;
    assert(Story_Start(r, 48) && Story_Tick(r) == 1 && values[0] == 4);
    assert(Story_Tick(r) == 0);

    JsonDocument *cross = parse("[{\"id\":\"cross\",\"scene_number\":50,\"commands\":["
        "{\"command\":\"call_scene\",\"scene\":\"shop\"},{\"command\":\"return\"}]}]");
    assert(Story_Add(r, "other", Json_Root(cross), NULL, NULL) == 1);
    count = 0;
    assert(Story_Start(r, 50) && Story_Tick(r) == 0 && !strcmp(last_text, "Welcome"));

    JsonDocument *bad = parse("[{\"id\":\"bad\",\"scene_number\":48,\"commands\":["
        "{\"command\":\"retail_command\",\"opcode\":6,\"operands\":[0]}]}]");
    assert(Story_Add(r, "bad", Json_Root(bad), NULL, NULL) < 0);
    count = 0;
    assert(Story_Start(r, 48) && Story_Tick(r) == 1 && values[0] == 4);
    JsonDocument *loop = parse("[{\"id\":\"loop\",\"scene_number\":49,\"commands\":["
        "{\"command\":\"label\",\"id\":\"again\"},{\"command\":\"jump\",\"to\":\"again\"}]}]");
    assert(Story_Add(r, "mod", Json_Root(loop), NULL, NULL) == 1);
    assert(Story_Start(r, 49) && Story_Tick(r) == 1); /* bounded per frame */
    Story_Destroy(r);
    Json_Free(loop); Json_Free(bad); Json_Free(cross); Json_Free(branch); Json_Free(d);
    puts("campaign scenes: passed");
    return 0;
}
