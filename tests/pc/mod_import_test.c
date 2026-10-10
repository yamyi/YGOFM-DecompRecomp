/* The mod .zip import (src/pc/mods/import.h): .zip files written here, entry
 * by entry, then opened and installed into a scratch mods folder. Checks
 * the layouts a mod comes in, the arm64 object check, Replace, and that a
 * bad .zip (names leaving the folder, links, damage) writes nothing. */
#define _POSIX_C_SOURCE 200809L
#include "pc/compat/fs.h"
#include "pc/mods/import.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <zlib.h>
#ifndef _WIN32
#include <dirent.h>
#endif

static int failures;
#define CHECK(condition)                                                                                               \
    do {                                                                                                               \
        if (!(condition)) {                                                                                            \
            fprintf(stderr, "%s:%d: CHECK(%s) failed\n", __FILE__, __LINE__, #condition);                             \
            failures++;                                                                                                \
        }                                                                                                              \
    } while (0)

/* --- a small .zip writer -------------------------------------------- */

typedef struct {
    const char *name;
    const char *data;     /* NULL for a folder */
    int deflate;
    unsigned mode;        /* a Unix mode for the high half of the attributes; 0 none */
    unsigned flags;
    unsigned method;      /* 0: from `deflate` */
    int bad_crc;
    long lie_size;        /* nonzero: the size the directory gives instead */
} Item;

static void put16(FILE *f, unsigned v)
{
    fputc((int)(v & 0xFF), f);
    fputc((int)(v >> 8 & 0xFF), f);
}
static void put32(FILE *f, unsigned long v)
{
    put16(f, (unsigned)(v & 0xFFFF));
    put16(f, (unsigned)(v >> 16 & 0xFFFF));
}

static void write_zip(const char *path, const Item *items, int n)
{
    FILE *f = fopen(path, "wb");
    unsigned long offsets[64], packed[64], crcs[64], sizes[64], start, end;
    unsigned methods[64];
    unsigned char *bodies[64];
    if (!f) {
        perror(path);
        exit(2);
    }
    for (int i = 0; i < n; i++) {
        const Item *it = &items[i];
        size_t size = it->data ? strlen(it->data) : 0;
        unsigned char *body = malloc(size + 64 + size / 10);
        unsigned long length = (unsigned long)size;
        crcs[i] = crc32(0L, (const Bytef *)(it->data ? it->data : ""), (uInt)size) ^ (it->bad_crc ? 1u : 0u);
        sizes[i] = it->lie_size ? (unsigned long)it->lie_size : (unsigned long)size;
        methods[i] = it->method ? it->method : it->deflate ? 8 : 0;
        if (it->deflate) {
            z_stream s;
            memset(&s, 0, sizeof(s));
            deflateInit2(&s, 9, Z_DEFLATED, -MAX_WBITS, 8, Z_DEFAULT_STRATEGY);
            s.next_in = (Bytef *)(it->data ? it->data : "");
            s.avail_in = (uInt)size;
            s.next_out = body;
            s.avail_out = (uInt)(size + 64 + size / 10);
            deflate(&s, Z_FINISH);
            length = s.total_out;
            deflateEnd(&s);
        } else if (size)
            memcpy(body, it->data, size);
        bodies[i] = body;
        packed[i] = length;
        offsets[i] = (unsigned long)ftell(f);
        put32(f, 0x04034b50u);
        put16(f, 20);
        put16(f, it->flags);
        put16(f, methods[i]);
        put16(f, 0);
        put16(f, 0);
        put32(f, crcs[i]);
        put32(f, packed[i]);
        put32(f, sizes[i]);
        put16(f, (unsigned)strlen(it->name));
        put16(f, 0);
        fwrite(it->name, 1, strlen(it->name), f);
        fwrite(body, 1, length, f);
    }
    start = (unsigned long)ftell(f);
    for (int i = 0; i < n; i++) {
        const Item *it = &items[i];
        put32(f, 0x02014b50u);
        put16(f, it->mode ? 3u << 8 | 20 : 20);
        put16(f, 20);
        put16(f, it->flags);
        put16(f, methods[i]);
        put16(f, 0);
        put16(f, 0);
        put32(f, crcs[i]);
        put32(f, packed[i]);
        put32(f, sizes[i]);
        put16(f, (unsigned)strlen(it->name));
        put16(f, 0);
        put16(f, 0);
        put16(f, 0);
        put16(f, 0);
        put32(f, (unsigned long)it->mode << 16);
        put32(f, offsets[i]);
        fwrite(it->name, 1, strlen(it->name), f);
        free(bodies[i]);
    }
    end = (unsigned long)ftell(f);
    put32(f, 0x06054b50u);
    put16(f, 0);
    put16(f, 0);
    put16(f, (unsigned)n);
    put16(f, (unsigned)n);
    put32(f, end - start);
    put32(f, start);
    put16(f, 0);
    fclose(f);
}

/* --- the scratch folders ---------------------------------------------- */

static char root[1024], mods[1100], zip[1100];

static int exists(const char *relative)
{
    char path[2048];
    struct stat info;
    snprintf(path, sizeof(path), "%s/%s", root, relative);
    return !stat(path, &info);
}
static int file_is(const char *relative, const char *text)
{
    char path[2048], got[256];
    FILE *f;
    size_t n;
    snprintf(path, sizeof(path), "%s/%s", root, relative);
    if (!(f = fopen(path, "rb")))
        return 0;
    n = fread(got, 1, sizeof(got) - 1, f);
    fclose(f);
    got[n] = 0;
    return !strcmp(got, text);
}
/* What the mods folder holds, names joined by spaces, sorted. */
static const char *listing(const char *relative)
{
    static char out[1024];
    char path[2048], names[32][128];
    int n = 0;
    DIR *d;
    struct dirent *e;
    snprintf(path, sizeof(path), "%s/%s", root, relative);
    out[0] = 0;
    if (!(d = opendir(path)))
        return out;
    while ((e = readdir(d)) && n < 32)
        if (strcmp(e->d_name, ".") && strcmp(e->d_name, ".."))
            {
            size_t k = strlen(e->d_name) < sizeof(names[0]) ? strlen(e->d_name) : sizeof(names[0]) - 1;
            memcpy(names[n], e->d_name, k);
            names[n++][k] = 0;
        }
    closedir(d);
    for (int i = 1; i < n; i++)
        for (int j = i; j > 0 && strcmp(names[j - 1], names[j]) > 0; j--) {
            char t[128];
            memcpy(t, names[j], sizeof(t));
            memcpy(names[j], names[j - 1], sizeof(t));
            memcpy(names[j - 1], t, sizeof(t));
        }
    for (int i = 0; i < n; i++)
        snprintf(out + strlen(out), sizeof(out) - strlen(out), "%s%s", i ? " " : "", names[i]);
    return out;
}
static void reset(void)
{
    Mods_ImportRemoveTree(mods);
    mkdir(mods, 0777);
}
/* A folder below the scratch root (Paths_MakeDirs is not used: on Windows
 * it cannot start at a drive letter). */
static void make(const char *relative)
{
    char path[2048];
    snprintf(path, sizeof(path), "%s/%s", root, relative);
    for (char *c = path + strlen(root) + 1;; c++)
        if (*c == '/' || !*c) {
            char kept = *c;
            *c = 0;
            mkdir(path, 0777);
            if (!(*c = kept))
                break;
        }
}

/* Opens and installs `items`; 1 when both worked. `why` gets the reason. */
static int import(const Item *items, int n, int *count, char *why, size_t size)
{
    ModsImport *imp;
    int ok;
    write_zip(zip, items, n);
    why[0] = 0;
    imp = Mods_ImportOpen(zip, why, size);
    *count = imp ? Mods_ImportCount(imp) : -1;
    if (!imp)
        return 0;
    ok = Mods_ImportInstall(imp, mods, why, size);
    if (!ok && getenv("MOD_IMPORT_VERBOSE"))
        fprintf(stderr, "install: %s\n", why);
    Mods_ImportClose(imp);
    return ok;
}

static const char *const MANIFEST_A = "{\"id\": \"alpha\", \"name\": \"Alpha mod\"}";

int main(void)
{
    char why[512];
    int count;
    const char *base = getenv("TMPDIR");
#ifdef _WIN32
    if (!base)
        base = getenv("TEMP");
#endif
    snprintf(root, sizeof(root), "%s/mod-import-XXXXXX", base ? base : "/tmp");
    for (char *c = root; *c; c++)
        if (*c == '\\')
            *c = '/';
    if (!mkdtemp(root)) {
        perror(root);
        return 2;
    }
    snprintf(mods, sizeof(mods), "%s/mods", root);
    snprintf(zip, sizeof(zip), "%s/in.zip", root);

    /* A mod in a folder at the top: its files, its subfolders. */
    reset();
    {
        Item items[] = {{"alpha/", NULL, 0, 040755, 0, 0, 0, 0}, {"alpha/mod.json", MANIFEST_A, 1, 0100644, 0, 0, 0, 0},
                        {"alpha/text/name.txt", "hello", 0, 0, 0, 0, 0, 0}};
        CHECK(import(items, 3, &count, why, sizeof(why)));
        CHECK(count == 1);
        CHECK(file_is("mods/alpha/text/name.txt", "hello"));
        CHECK(file_is("mods/alpha/mod.json", MANIFEST_A));
        CHECK(!strcmp(listing("mods"), "alpha")); /* no .import- left */
    }
    /* The .zip's root is the mod: the folder is the manifest's id. */
    reset();
    {
        Item items[] = {{"mod.json", "{\"id\": \"rooted\", \"name\": \"At the root\"}", 1, 0, 0, 0, 0, 0},
                        {"name.txt", "root", 0, 0, 0, 0, 0, 0}};
        ModsImport *imp;
        write_zip(zip, items, 2);
        imp = Mods_ImportOpen(zip, why, sizeof(why));
        CHECK(imp && Mods_ImportCount(imp) == 1);
        if (imp) {
            CHECK(!strcmp(Mods_ImportMod(imp, 0)->folder, "rooted"));
            CHECK(!strcmp(Mods_ImportMod(imp, 0)->name, "At the root"));
            CHECK(!Mods_ImportMod(imp, 0)->code);
            CHECK(Mods_ImportInstall(imp, mods, why, sizeof(why)));
            Mods_ImportClose(imp);
        }
        CHECK(file_is("mods/rooted/name.txt", "root"));
    }
    /* One wrapper folder; what is beside the mod there stays out. */
    reset();
    {
        Item items[] = {{"Download/README.txt", "read me", 0, 0, 0, 0, 0, 0},
                        {"Download/alpha/mod.json", MANIFEST_A, 0, 0, 0, 0, 0, 0},
                        {"__MACOSX/Download/alpha/._mod.json", "x", 0, 0, 0, 0, 0, 0},
                        {"__MACOSX/beta/mod.json", "{}", 0, 0, 0, 0, 0, 0}};
        CHECK(import(items, 4, &count, why, sizeof(why)));
        CHECK(count == 1);
        CHECK(!strcmp(listing("mods"), "alpha"));
        CHECK(!strcmp(listing("mods/alpha"), "mod.json"));
    }
    /* Several mods, one with a mod.json of its own inside (its file). */
    reset();
    {
        Item items[] = {{"alpha/mod.json", MANIFEST_A, 1, 0, 0, 0, 0, 0},
                        {"alpha/extra/mod.json", "{\"id\": \"inner\"}", 0, 0, 0, 0, 0, 0},
                        {"beta/mod.json", "{\"id\": \"beta\"}", 1, 0, 0, 0, 0, 0},
                        {"gamma/mod.json", "not json", 0, 0, 0, 0, 0, 0}};
        CHECK(import(items, 4, &count, why, sizeof(why)));
        CHECK(count == 3);
        CHECK(!strcmp(listing("mods"), "alpha beta gamma"));
        CHECK(exists("mods/alpha/extra/mod.json"));
    }
    /* Too deep, or no mod.json: no mod. */
    reset();
    {
        Item items[] = {{"readme.txt", "nothing", 0, 0, 0, 0, 0, 0}, {"a/b/c/mod.json", "{}", 0, 0, 0, 0, 0, 0}};
        CHECK(!import(items, 2, &count, why, sizeof(why)));
        CHECK(count == 0);
        CHECK(strstr(why, "no mod") != NULL);
        CHECK(!strcmp(listing("mods"), ""));
    }
    /* Code: the arm64 object, by "library" or by "libraries". */
    reset();
    {
        static const struct {
            const char *manifest, *file;
            int code, android;
        } cases[] = {
            {"{\"id\": \"cm\", \"library\": \"cm\"}", "c/cm.o", 1, 0},
            {"{\"id\": \"cm\", \"library\": \"cm\"}", "c/cm.aarch64.o", 1, 1},
            {"{\"id\": \"cm\", \"library\": \"cm.o\"}", "c/cm.aarch64.o", 1, 1},
            {"{\"id\": \"cm\", \"libraries\": {\"aarch64\": \"arm/x.o\"}}", "c/arm/x.o", 1, 1},
            {"{\"id\": \"cm\", \"libraries\": {\"x86_64-windows\": \"w.o\"}}", "c/w.o", 1, 0},
            {"{\"id\": \"cm\", \"libraries\": {\"x86_64-windows\": \"w.o\"}}", "c/cm.aarch64.o", 1, 1},
            {"{\"id\": \"cm\"}", "c/cm.o", 0, 0},
        };
        for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
            Item items[] = {{"c/mod.json", cases[i].manifest, 0, 0, 0, 0, 0, 0},
                            {cases[i].file, "\x7f" "ELF", 0, 0, 0, 0, 0, 0}};
            ModsImport *imp;
            write_zip(zip, items, 2);
            imp = Mods_ImportOpen(zip, why, sizeof(why));
            CHECK(imp && Mods_ImportCount(imp) == 1);
            if (imp) {
                CHECK(Mods_ImportMod(imp, 0)->code == cases[i].code);
                CHECK(Mods_ImportMod(imp, 0)->android_code == cases[i].android);
                Mods_ImportClose(imp);
            }
        }
    }
    /* Replace: the old folder goes; without it the import is refused and
     * the old one stays as it was. */
    reset();
    {
        Item old_items[] = {{"alpha/mod.json", MANIFEST_A, 0, 0, 0, 0, 0, 0},
                            {"alpha/old.txt", "old", 0, 0, 0, 0, 0, 0}};
        Item new_items[] = {{"alpha/mod.json", MANIFEST_A, 1, 0, 0, 0, 0, 0},
                            {"alpha/new.txt", "new", 1, 0, 0, 0, 0, 0}};
        ModsImport *imp;
        CHECK(import(old_items, 2, &count, why, sizeof(why)));
        write_zip(zip, new_items, 2);
        imp = Mods_ImportOpen(zip, why, sizeof(why));
        CHECK(imp != NULL);
        if (imp) {
            CHECK(!Mods_ImportInstall(imp, mods, why, sizeof(why)));
            CHECK(strstr(why, "already") != NULL);
            CHECK(file_is("mods/alpha/old.txt", "old") && !exists("mods/alpha/new.txt"));
            strcat(strcpy(Mods_ImportMod(imp, 0)->replace, mods), "/alpha");
            CHECK(Mods_ImportInstall(imp, mods, why, sizeof(why)));
            Mods_ImportClose(imp);
        }
        CHECK(file_is("mods/alpha/new.txt", "new") && !exists("mods/alpha/old.txt"));
        CHECK(!strcmp(listing("mods"), "alpha"));
    }
    /* A second mod failing puts the first one's old folder back. */
    reset();
    {
        Item old_items[] = {{"alpha/mod.json", MANIFEST_A, 0, 0, 0, 0, 0, 0},
                            {"alpha/old.txt", "old", 0, 0, 0, 0, 0, 0}};
        Item new_items[] = {{"alpha/mod.json", MANIFEST_A, 1, 0, 0, 0, 0, 0},
                            {"beta/mod.json", "{\"id\": \"beta\"}", 0, 0, 0, 0, 0, 0}};
        ModsImport *imp;
        CHECK(import(old_items, 2, &count, why, sizeof(why)));
        make("mods/beta"); /* there, and not marked to be replaced */
        write_zip(zip, new_items, 2);
        imp = Mods_ImportOpen(zip, why, sizeof(why));
        CHECK(imp != NULL);
        if (imp) {
            strcat(strcpy(Mods_ImportMod(imp, 0)->replace, mods), "/alpha");
            CHECK(!Mods_ImportInstall(imp, mods, why, sizeof(why)));
            Mods_ImportClose(imp);
        }
        CHECK(file_is("mods/alpha/old.txt", "old"));
        CHECK(!strcmp(listing("mods"), "alpha beta"));
        CHECK(!strcmp(listing("mods/beta"), ""));
    }
    /* Refused before anything is written: names that leave the folder,
     * links, encryption, other compressions, two entries for one file. */
    {
        static const Item bad[][2] = {
            {{"../evil.txt", "x", 0, 0, 0, 0, 0, 0}, {"alpha/mod.json", "{}", 0, 0, 0, 0, 0, 0}},
            {{"alpha/../../evil.txt", "x", 0, 0, 0, 0, 0, 0}, {"alpha/mod.json", "{}", 0, 0, 0, 0, 0, 0}},
            {{"alpha\\..\\..\\evil.txt", "x", 0, 0, 0, 0, 0, 0}, {"alpha/mod.json", "{}", 0, 0, 0, 0, 0, 0}},
            {{"/evil.txt", "x", 0, 0, 0, 0, 0, 0}, {"alpha/mod.json", "{}", 0, 0, 0, 0, 0, 0}},
            {{"C:/evil.txt", "x", 0, 0, 0, 0, 0, 0}, {"alpha/mod.json", "{}", 0, 0, 0, 0, 0, 0}},
            {{"alpha/./x.txt", "x", 0, 0, 0, 0, 0, 0}, {"alpha/mod.json", "{}", 0, 0, 0, 0, 0, 0}},
            {{"alpha//x.txt", "x", 0, 0, 0, 0, 0, 0}, {"alpha/mod.json", "{}", 0, 0, 0, 0, 0, 0}},
            {{"alpha/\x01x.txt", "x", 0, 0, 0, 0, 0, 0}, {"alpha/mod.json", "{}", 0, 0, 0, 0, 0, 0}},
            {{"alpha/\xff.txt", "x", 0, 0, 0, 0, 0, 0}, {"alpha/mod.json", "{}", 0, 0, 0, 0, 0, 0}},
            {{"alpha/link", "../../evil", 0, 0120777, 0, 0, 0, 0}, {"alpha/mod.json", "{}", 0, 0, 0, 0, 0, 0}},
            {{"alpha/fifo", "", 0, 0010644, 0, 0, 0, 0}, {"alpha/mod.json", "{}", 0, 0, 0, 0, 0, 0}},
            {{"alpha/x.txt", "x", 0, 0, 1, 0, 0, 0}, {"alpha/mod.json", "{}", 0, 0, 0, 0, 0, 0}},
            {{"alpha/x.txt", "x", 0, 0, 0, 12, 0, 0}, {"alpha/mod.json", "{}", 0, 0, 0, 0, 0, 0}},
            {{"alpha/mod.json", "{}", 0, 0, 0, 0, 0, 0}, {"alpha/mod.json", "{}", 0, 0, 0, 0, 0, 0}},
            {{"alpha/Name.txt", "a", 0, 0, 0, 0, 0, 0}, {"alpha/name.TXT", "b", 0, 0, 0, 0, 0, 0}},
        };
        for (size_t i = 0; i < sizeof(bad) / sizeof(bad[0]); i++) {
            reset();
            write_zip(zip, bad[i], 2);
            CHECK(Mods_ImportOpen(zip, why, sizeof(why)) == NULL);
            CHECK(why[0] != 0);
            if (getenv("MOD_IMPORT_VERBOSE"))
                fprintf(stderr, "refused %u: %s\n", (unsigned)i, why);
            CHECK(!strcmp(listing("mods"), ""));
            CHECK(!exists("evil.txt") && !exists("mods/evil.txt"));
        }
        CHECK(!strcmp(listing(""), "in.zip mods"));
    }
    /* Damage found while unpacking: a wrong CRC, a size the data does not
     * keep to. Nothing is left in the mods folder. */
    {
        static const Item damaged[][2] = {
            {{"alpha/mod.json", MANIFEST_A, 0, 0, 0, 0, 0, 0}, {"alpha/x.txt", "data", 0, 0, 0, 0, 1, 0}},
            {{"alpha/mod.json", MANIFEST_A, 0, 0, 0, 0, 0, 0}, {"alpha/x.txt", "data", 1, 0, 0, 0, 1, 0}},
            {{"alpha/mod.json", MANIFEST_A, 0, 0, 0, 0, 0, 0},
             {"alpha/x.txt", "a long text that inflates past the size given", 1, 0, 0, 0, 0, 4}},
        };
        for (size_t i = 0; i < sizeof(damaged) / sizeof(damaged[0]); i++) {
            reset();
            CHECK(!import(damaged[i], 2, &count, why, sizeof(why)));
            CHECK(count == 1);
            CHECK(strstr(why, "damaged") != NULL);
            CHECK(!strcmp(listing("mods"), ""));
        }
    }
    /* Not a .zip at all. */
    {
        FILE *f = fopen(zip, "wb");
        fputs("This is a text file, long enough to be looked at as a .zip.", f);
        fclose(f);
        CHECK(Mods_ImportOpen(zip, why, sizeof(why)) == NULL);
        CHECK(strstr(why, "not a .zip") != NULL);
    }
    /* What an interrupted import leaves is cleared. */
    reset();
    {
        char path[2048];
        FILE *f;
        make("mods/.import-abc123/0/x");
        snprintf(path, sizeof(path), "%s/.incoming.zip", mods);
        f = fopen(path, "wb");
        fclose(f);
        make("mods/kept");
        Mods_ImportCleanup(mods);
        CHECK(!strcmp(listing("mods"), "kept"));
    }
    Mods_ImportRemoveTree(root);
    if (failures)
        fprintf(stderr, "%d checks failed\n", failures);
    else
        printf("mod import: all checks passed\n");
    return failures != 0;
}
