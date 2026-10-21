#ifndef MEMORIES_PC_CAMPAIGN_SCENES_H
#define MEMORIES_PC_CAMPAIGN_SCENES_H
#include <stddef.h>
#include "../mods/json.h"

/* JSON scenes keep their identities; retail scene numbers are replacement
 * keys, not positions in the mod's list. Native commands retain their own
 * frame-spanning handlers, while this runner owns JSON control flow. */
typedef struct StoryScene StoryScene;
typedef struct StoryRunner StoryRunner;
typedef struct {
    /* Begin/poll a native command. Poll returns 1 when complete, 0 while
     * waiting, -1 on a mode transition, -2 on failure. */
    int (*native)(void *context, int opcode, const unsigned char *operands,
                  int count, const char *text, int begin);
    int (*flag)(void *context, int id);
    int (*deck_complete)(void *context);
    void *context;
} StoryHost;
StoryRunner *Story_Create(StoryHost host);
void Story_Destroy(StoryRunner *runner);
int Story_Add(StoryRunner *runner, const char *mod, const JsonValue *scenes,
              const JsonValue *assets, const JsonValue *dialogue);
int Story_Start(StoryRunner *runner, int retail_scene);
/* 1 while running, 0 after return/end, -1 after a native mode transition,
 * -2 on error. A tick executes at most 128 immediate commands. */
int Story_Tick(StoryRunner *runner);
const char *Story_Error(const StoryRunner *runner);

/* Game adapter, used only by the PC campaign loop and text lookup. */
void StoryGame_Start(int retail_scene);
int StoryGame_Tick(void);
const unsigned char *StoryGame_Text(int id);
#endif
