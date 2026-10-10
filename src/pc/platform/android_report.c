/* Android: the crash report, offered on the next launch (platform.h,
 * Android_OfferCrashReport; notes/pc-build.md, "Crash reports on Android").
 *
 * A crash writes crash-<pid>.txt (hang-<pid>.txt where a freeze watchdog
 * runs, which is not the Android default) into the
 * reports folder of the player's folder (crash.c), which on Android is
 * /sdcard/Android/data/<package>/files/reports: since Android 11 no file
 * manager the player has opens it. So the next launch shows a notice over
 * the picture (the game's own, as the quit question is) with
 *
 *   Share              the system's share sheet with the report attached,
 *                      through our ReportProvider (a content:// URI the
 *                      chosen app is granted to read): Discord, a chat,
 *                      e-mail;
 *   Save to Downloads  a copy in the phone's Downloads folder (MediaStore,
 *                      Android 10 and later; earlier, writing there needs
 *                      a storage permission the app does not ask for, so
 *                      the button is not offered);
 *   Not now            nothing; the report is offered again next launch.
 *
 * Share or Save marks the report handled (reports/handled.txt holds its
 * time), and with it every older one: only the newest report is offered.
 *
 * What goes out is the app's version and build, the device's maker and
 * model, the Android version, the memory free now, and the game's report
 * with the player's own paths taken out (redact): the folder the game
 * keeps its files in and any document the player picked (content:// URIs,
 * which name their folders and files); nothing of the save files, the
 * settings file or the disc. The Java calls run on the thread's own stack
 * (Memories_OnHostStack): ART refuses JNI from the game stack. Desktops
 * have none of this; crash reports stay where they are there. */
#ifdef __ANDROID__
#define _GNU_SOURCE /* memrchr */
#include "pc/compat/fs.h"
#include "platform.h"
#include "menu.h"
#include "paths.h"
#include "pc/debug/crash.h"
#include "pc/guest/state.h"
#include <SDL3/SDL.h>
#include <dirent.h>
#include <errno.h>
#include <jni.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysinfo.h>
#include <sys/system_properties.h>
#include <time.h>
#include <unistd.h>
#include "jni_guard.h" /* last: after SDL's own headers */

/* The release this build is ("" for a development build): build_game32.py. */
extern const char Memories_Version[];

#define AUTHORITY "org.yfmredecomp.game.reports" /* ReportProvider.AUTHORITY, the manifest's provider */
#define HANDLED "handled.txt"
#define REPORT_LIMIT (512 * 1024)            /* of the game's report read; one is a few KB */
#define DOWNLOADS_API 29                     /* MediaStore.Downloads */

static struct {
    char path[1024];           /* the report offered */
    char name[128];            /* its file name in the reports folder */
    long long sec, nsec;       /* its modification time */
    char file_name[96];        /* what the copy is called: yfm-redecomp-crash-<when>.txt */
    char *text;                /* the copy: built when offered */
    size_t size;
    int api;                   /* the device's API level */
} offer;

/* --- which report, if any -------------------------------------------- */

static int report_name(const char *name)
{
    size_t length = strlen(name);
    return (!strncmp(name, "crash-", 6) || !strncmp(name, "hang-", 5)) && length > 4 &&
           !strcmp(name + length - 4, ".txt");
}

static void handled_path(char *out, size_t size) { snprintf(out, size, "%s/" HANDLED, Crash_ReportDir); }

/* The time of the last report Share or Save took care of; 0 when none. */
static void read_handled(long long *sec, long long *nsec)
{
    char path[640];
    FILE *file;
    *sec = *nsec = 0;
    handled_path(path, sizeof(path));
    if ((file = fopen(path, "r")) != NULL) {
        if (fscanf(file, "%lld %lld", sec, nsec) != 2) *sec = *nsec = 0;
        fclose(file);
    }
}

static void mark_handled(void)
{
    char path[640], temporary[700];
    FILE *file;
    handled_path(path, sizeof(path));
    snprintf(temporary, sizeof(temporary), "%s.tmp", path);
    if (!(file = fopen(temporary, "w"))) {
        fprintf(stderr, "memories-pc: crash report: could not write %s: %s\n", temporary, strerror(errno));
        return;
    }
    fprintf(file, "%lld %lld %s\n", offer.sec, offer.nsec, offer.name);
    if (fclose(file) || rename(temporary, path)) {
        fprintf(stderr, "memories-pc: crash report: could not write %s: %s\n", path, strerror(errno));
        remove(temporary);
        return;
    }
    fprintf(stderr, "memories-pc: crash report %s handled\n", offer.name);
}

static int later(long long sec, long long nsec, long long than_sec, long long than_nsec)
{
    return sec > than_sec || (sec == than_sec && nsec > than_nsec);
}

/* The newest report not handled yet, into `offer`; 0 when there is none. */
static int find_report(void)
{
    DIR *folder = opendir(Crash_ReportDir);
    struct dirent *entry;
    struct stat info;
    char path[1024];
    long long handled_sec, handled_nsec;
    int found = 0;
    if (!folder) return 0;
    read_handled(&handled_sec, &handled_nsec);
    while ((entry = readdir(folder)) != NULL) {
        if (!report_name(entry->d_name) || strlen(entry->d_name) >= sizeof(offer.name)) continue;
        snprintf(path, sizeof(path), "%s/%s", Crash_ReportDir, entry->d_name);
        if (stat(path, &info) || !S_ISREG(info.st_mode) || info.st_size <= 0) continue;
        if (!later(info.st_mtim.tv_sec, info.st_mtim.tv_nsec, handled_sec, handled_nsec)) continue;
        if (found && !later(info.st_mtim.tv_sec, info.st_mtim.tv_nsec, offer.sec, offer.nsec)) continue;
        snprintf(offer.path, sizeof(offer.path), "%s", path);
        snprintf(offer.name, sizeof(offer.name), "%s", entry->d_name);
        offer.sec = info.st_mtim.tv_sec;
        offer.nsec = info.st_mtim.tv_nsec;
        found = 1;
    }
    closedir(folder);
    return found;
}

/* --- what goes out --------------------------------------------------- */

static void property(const char *name, char *out)
{
    out[0] = '\0';
    __system_property_get(name, out); /* PROP_VALUE_MAX (92) bytes */
    if (!out[0]) snprintf(out, PROP_VALUE_MAX, "?");
}

static void program_file(const char *name, char *out, size_t size)
{
    char path[1100];
    FILE *file;
    out[0] = '\0';
    if (Paths_Program(path, sizeof(path), name) || !(file = fopen(path, "r"))) return;
    if (fgets(out, (int)size, file)) out[strcspn(out, "\r\n")] = '\0';
    fclose(file);
}

/* MemAvailable, as /proc/meminfo says (what the system could hand out
 * without swapping), with the total. */
static void free_memory(char *out, size_t size)
{
    char line[128];
    long long total = -1, available = -1, value;
    FILE *file = fopen("/proc/meminfo", "r");
    while (file && fgets(line, sizeof(line), file)) {
        if (sscanf(line, "MemTotal: %lld kB", &value) == 1) total = value;
        else if (sscanf(line, "MemAvailable: %lld kB", &value) == 1) available = value;
    }
    if (file) fclose(file);
    if (total > 0 && available >= 0) snprintf(out, size, "%lld MB of %lld MB", available >> 10, total >> 10);
    else snprintf(out, size, "?");
}

static void append(char **text, size_t *used, size_t *room, const char *add, size_t length)
{
    if (!*text) return;
    if (*used + length + 1 > *room) {
        size_t wanted = (*used + length + 1) * 2;
        char *grown = realloc(*text, wanted);
        if (!grown) {
            free(*text);
            *text = NULL;
            return;
        }
        *text = grown;
        *room = wanted;
    }
    memcpy(*text + *used, add, length);
    *used += length;
    (*text)[*used] = '\0';
}

/* One line of the game's report as it goes out: the paths that are the
 * player's own taken out. The user folder (in the "user dir" fact, and
 * wherever a log line names a file in it) becomes <app folder>; a
 * content:// URI (the disc image the player picked, which names their
 * folders and file) becomes content://<removed>; the time zone of
 * "started" goes. */
static void redact(const char *line, char *out, size_t size)
{
    const char *user = Paths_UserDir();
    size_t user_length = user ? strlen(user) : 0, used = 0;
    const char *at = line;
    if (!strncmp(line, "started: ", 9)) {
        /* "started: 2026-10-09 21:10:02 -0300": the date and the time. */
        size_t length = strcspn(line, "\r\n");
        const char *zone = memrchr(line, ' ', length);
        if (zone && zone > line + 9 && (zone[1] == '+' || zone[1] == '-')) length = (size_t)(zone - line);
        snprintf(out, size, "%.*s\n", (int)length, line);
        return;
    }
    while (*at && used + 1 < size) {
        if (user_length > 1 && user[0] == '/' && !strncmp(at, user, user_length)) {
            used += (size_t)snprintf(out + used, size - used, "<app folder>");
            at += user_length;
        } else if (!strncmp(at, "content://", 10)) {
            used += (size_t)snprintf(out + used, size - used, "content://<removed>");
            at += 10;
            while (*at && *at != ' ' && *at != '\t' && *at != '\n' && *at != '"' && *at != '\'' && *at != ')')
                at++;
        } else {
            out[used++] = *at++;
            out[used] = '\0';
        }
        if (used >= size) used = size - 1;
    }
    out[used] = '\0';
}

/* The report the player shares or saves; NULL when the game's could not
 * be read. */
static char *build_report(size_t *size)
{
    char line[2048], clean[2600], value[PROP_VALUE_MAX], value2[PROP_VALUE_MAX], memory[64], build[64], commit[96];
    char *text = malloc(8192);
    size_t used = 0, room = 8192, read_bytes = 0;
    FILE *file;
    if (!text) return NULL;
    text[0] = '\0';
#define ADD(...)                                                                                   \
    do {                                                                                           \
        int length_ = snprintf(line, sizeof(line), __VA_ARGS__);                                   \
        if (length_ > 0) append(&text, &used, &room, line, (size_t)length_ < sizeof(line) ? (size_t)length_ : sizeof(line) - 1); \
    } while (0)
    program_file("buildid", build, sizeof(build));
    program_file("commit", commit, sizeof(commit));
    ADD("YFM Re-Decomp crash report (Android)\n");
    ADD("app version: %s\n", Memories_Version[0] ? Memories_Version : "development build");
    ADD("build: %s (commit %s)\n", build[0] ? build : "unknown", commit[0] ? commit : "unknown");
    property("ro.product.manufacturer", value);
    property("ro.product.model", value2);
    ADD("device: %s %s\n", value, value2);
    property("ro.build.version.release", value);
    property("ro.build.version.sdk", value2);
    ADD("Android: %s (API %s)\n", value, value2);
    free_memory(memory, sizeof(memory));
    ADD("free memory now: %s\n", memory);
    ADD("report: %s\n\n", offer.name);
#undef ADD
    if (!(file = fopen(offer.path, "r"))) {
        free(text);
        return NULL;
    }
    while (text && read_bytes < REPORT_LIMIT && fgets(line, sizeof(line), file)) {
        read_bytes += strlen(line);
        redact(line, clean, sizeof(clean));
        append(&text, &used, &room, clean, strlen(clean));
        /* A line cut short by redact keeps its end of line. */
        if (strchr(line, '\n') && !strchr(clean, '\n')) append(&text, &used, &room, "\n", 1);
    }
    fclose(file);
    if (text) *size = used;
    return text;
}

/* --- the Java side (JNI), on the thread's own stack ------------------ */

/* One Share or Save: the JNI environment and what went wrong, if anything.
 * Once a step has failed every later one is skipped, so no JNI call is made
 * with an exception pending or with a lookup that came back empty (CheckJNI,
 * on for a debuggable app, aborts on either). */
typedef struct Java {
    JNIEnv *env;
    int share; /* 1 Share, 0 Save to Downloads */
    int bad;
    char why[512];
} Java;

/* 1 when the step `what` failed: a Java exception pending (cleared; the
 * player is told its text) or `empty` (a lookup or call that returned
 * nothing). Also 1, quietly, once an earlier step has failed. */
static int failed(Java *java, const char *what, int empty)
{
    JNIEnv *env = java->env;
    jthrowable error;
    jclass type;
    jmethodID describe;
    jstring message = NULL;
    const char *chars = NULL;
    if (java->bad) return 1;
    if (!(*env)->ExceptionCheck(env)) {
        if (!empty) return 0;
        snprintf(java->why, sizeof(java->why), "%s failed.", what);
    } else {
        error = (*env)->ExceptionOccurred(env);
        (*env)->ExceptionClear(env);
        if (error && (type = (*env)->GetObjectClass(env, error)) != NULL) {
            describe = (*env)->GetMethodID(env, type, "toString", "()Ljava/lang/String;");
            if (describe && !(*env)->ExceptionCheck(env))
                message = (jstring)(*env)->CallObjectMethod(env, error, describe);
        }
        if ((*env)->ExceptionCheck(env)) {
            (*env)->ExceptionClear(env);
            message = NULL;
        }
        if (message && !(chars = (*env)->GetStringUTFChars(env, message, NULL)) && (*env)->ExceptionCheck(env))
            (*env)->ExceptionClear(env); /* out of memory for the text: the step still failed */
        snprintf(java->why, sizeof(java->why), "%s failed: %s", what, chars ? chars : "unknown error");
        if (chars) (*env)->ReleaseStringUTFChars(env, message, chars);
    }
    fprintf(stderr, "memories-pc: crash report: %s\n", java->why);
    java->bad = 1;
    return 1;
}

static jclass find_class(Java *java, const char *name)
{
    jclass type;
    if (java->bad) return NULL;
    type = (*java->env)->FindClass(java->env, name);
    return failed(java, name, !type) ? NULL : type;
}

static jmethodID method(Java *java, jclass type, const char *name, const char *signature)
{
    jmethodID id;
    if (java->bad) return NULL;
    id = (*java->env)->GetMethodID(java->env, type, name, signature);
    return failed(java, name, !id) ? NULL : id;
}

static jmethodID static_method(Java *java, jclass type, const char *name, const char *signature)
{
    jmethodID id;
    if (java->bad) return NULL;
    id = (*java->env)->GetStaticMethodID(java->env, type, name, signature);
    return failed(java, name, !id) ? NULL : id;
}

static jstring string(Java *java, const char *text)
{
    jstring made;
    if (java->bad) return NULL;
    made = (*java->env)->NewStringUTF(java->env, text);
    return failed(java, "A Java string", !made) ? NULL : made;
}

/* Downloads, through MediaStore (API 29+): the entry is added pending
 * (hidden from other apps), the bytes written, then it is published; a
 * failure after the entry exists removes it. */
static int save_to_downloads(Java *java, jobject activity)
{
    JNIEnv *env = java->env;
    jclass activity_type = (*env)->GetObjectClass(env, activity);
    jclass values_type = find_class(java, "android/content/ContentValues");
    jclass integer = find_class(java, "java/lang/Integer");
    jclass downloads = find_class(java, "android/provider/MediaStore$Downloads");
    jclass resolver_type = find_class(java, "android/content/ContentResolver");
    jclass stream_type = find_class(java, "java/io/OutputStream");
    jmethodID get_resolver = method(java, activity_type, "getContentResolver", "()Landroid/content/ContentResolver;");
    jmethodID values_new = method(java, values_type, "<init>", "()V");
    jmethodID put_string = method(java, values_type, "put", "(Ljava/lang/String;Ljava/lang/String;)V");
    jmethodID put_integer = method(java, values_type, "put", "(Ljava/lang/String;Ljava/lang/Integer;)V");
    jmethodID clear = method(java, values_type, "clear", "()V");
    jmethodID value_of = static_method(java, integer, "valueOf", "(I)Ljava/lang/Integer;");
    jmethodID insert = method(java, resolver_type, "insert",
                              "(Landroid/net/Uri;Landroid/content/ContentValues;)Landroid/net/Uri;");
    jmethodID open = method(java, resolver_type, "openOutputStream", "(Landroid/net/Uri;)Ljava/io/OutputStream;");
    jmethodID update = method(java, resolver_type, "update",
                              "(Landroid/net/Uri;Landroid/content/ContentValues;Ljava/lang/String;[Ljava/lang/String;)I");
    jmethodID erase = method(java, resolver_type, "delete", "(Landroid/net/Uri;Ljava/lang/String;[Ljava/lang/String;)I");
    jmethodID write = method(java, stream_type, "write", "([B)V");
    jmethodID close = method(java, stream_type, "close", "()V");
    jfieldID content_uri = NULL;
    jstring name_key = string(java, "_display_name"), name = string(java, offer.file_name);
    jstring type_key = string(java, "mime_type"), type = string(java, "text/plain");
    jstring folder_key = string(java, "relative_path"), folder = string(java, "Download");
    jstring pending_key = string(java, "is_pending");
    jobject resolver, collection, values, pending, published, uri, stream;
    jbyteArray bytes;
    jint updated;
    if (!java->bad) {
        content_uri = (*env)->GetStaticFieldID(env, downloads, "EXTERNAL_CONTENT_URI", "Landroid/net/Uri;");
        if (failed(java, "EXTERNAL_CONTENT_URI", !content_uri)) return 0;
    }
    if (java->bad) return 0;
    resolver = (*env)->CallObjectMethod(env, activity, get_resolver);
    if (failed(java, "Reaching the content resolver", !resolver)) return 0;
    collection = (*env)->GetStaticObjectField(env, downloads, content_uri);
    if (failed(java, "Finding Downloads", !collection)) return 0;
    values = (*env)->NewObject(env, values_type, values_new);
    if (failed(java, "Describing the file", !values)) return 0;
    pending = (*env)->CallStaticObjectMethod(env, integer, value_of, (jint)1);
    if (failed(java, "Describing the file", !pending)) return 0;
    published = (*env)->CallStaticObjectMethod(env, integer, value_of, (jint)0);
    if (failed(java, "Describing the file", !published)) return 0;
    (*env)->CallVoidMethod(env, values, put_string, name_key, name);
    if (failed(java, "Describing the file", 0)) return 0;
    (*env)->CallVoidMethod(env, values, put_string, type_key, type);
    if (failed(java, "Describing the file", 0)) return 0;
    (*env)->CallVoidMethod(env, values, put_string, folder_key, folder);
    if (failed(java, "Describing the file", 0)) return 0;
    (*env)->CallVoidMethod(env, values, put_integer, pending_key, pending);
    if (failed(java, "Describing the file", 0)) return 0;
    uri = (*env)->CallObjectMethod(env, resolver, insert, collection, values);
    if (failed(java, "Adding the file to Downloads", !uri)) return 0;

    /* The entry exists from here: on any failure it is removed. */
    stream = (*env)->CallObjectMethod(env, resolver, open, uri);
    if (!failed(java, "Opening the file in Downloads", !stream)) {
        bytes = (*env)->NewByteArray(env, (jsize)offer.size);
        if (!failed(java, "Copying the report", !bytes)) {
            (*env)->SetByteArrayRegion(env, bytes, 0, (jsize)offer.size, (const jbyte *)offer.text);
            if (!failed(java, "Copying the report", 0)) {
                (*env)->CallVoidMethod(env, stream, write, bytes);
                failed(java, "Writing the report", 0);
            }
        }
        /* Closed whatever happened (no exception is pending here). */
        (*env)->CallVoidMethod(env, stream, close);
        if (java->bad) {
            if ((*env)->ExceptionCheck(env)) (*env)->ExceptionClear(env);
        } else {
            failed(java, "Closing the report", 0);
        }
    }
    if (!java->bad) {
        (*env)->CallVoidMethod(env, values, clear);
        if (!failed(java, "Publishing the report", 0)) {
            (*env)->CallVoidMethod(env, values, put_integer, pending_key, published);
            if (!failed(java, "Publishing the report", 0)) {
                updated = (*env)->CallIntMethod(env, resolver, update, uri, values, NULL, NULL);
                if (!failed(java, "Publishing the report", updated < 1)) return 1;
            }
        }
    }
    (*env)->CallIntMethod(env, resolver, erase, uri, NULL, NULL);
    if ((*env)->ExceptionCheck(env)) (*env)->ExceptionClear(env);
    return 0;
}

/* The copy ReportProvider serves: the cache folder's shared/, holding only
 * this one. */
static int write_shared_copy(Java *java)
{
    const char *cache = SDL_GetAndroidCachePath();
    char folder[900], path[1100];
    DIR *directory;
    struct dirent *entry;
    FILE *file;
    int ok;
    if (!cache || !*cache) {
        snprintf(java->why, sizeof(java->why), "The app has no cache folder to share the report from (%s).",
                 SDL_GetError());
        java->bad = 1;
        return 0;
    }
    if (snprintf(folder, sizeof(folder), "%s/shared", cache) >= (int)sizeof(folder)) {
        snprintf(java->why, sizeof(java->why), "The app's cache folder's name is too long.");
        java->bad = 1;
        return 0;
    }
    if ((directory = opendir(folder)) != NULL) { /* an earlier share's copy */
        while ((entry = readdir(directory)) != NULL) {
            if (entry->d_name[0] == '.') continue;
            snprintf(path, sizeof(path), "%s/%s", folder, entry->d_name);
            remove(path);
        }
        closedir(directory);
    }
    Paths_MakeDirs(folder);
    snprintf(path, sizeof(path), "%s/%s", folder, offer.file_name);
    errno = 0;
    ok = (file = fopen(path, "wb")) != NULL && fwrite(offer.text, 1, offer.size, file) == offer.size;
    if (file && fclose(file)) ok = 0;
    if (!ok) {
        snprintf(java->why, sizeof(java->why), "Could not write the report to share (%s).",
                 errno ? strerror(errno) : "short write");
        java->bad = 1;
    }
    return ok;
}

/* ACTION_SEND with the report attached (EXTRA_STREAM and the ClipData,
 * read permission granted), in the system's chooser. */
static int share(Java *java, jobject activity)
{
    JNIEnv *env = java->env;
    char address[200];
    jclass activity_type, uri_type, intent_type, clip_type;
    jmethodID parse, intent_new, set_type, put_parcel, put_string, add_flags, set_clip, new_raw_uri, create_chooser,
        start;
    jstring text_address, action, mime, stream_key, subject_key, subject, label, title;
    jobject uri, intent, clip, chooser;
    if (!write_shared_copy(java)) return 0;
    snprintf(address, sizeof(address), "content://" AUTHORITY "/%s", offer.file_name);
    activity_type = (*env)->GetObjectClass(env, activity);
    uri_type = find_class(java, "android/net/Uri");
    intent_type = find_class(java, "android/content/Intent");
    clip_type = find_class(java, "android/content/ClipData");
    parse = static_method(java, uri_type, "parse", "(Ljava/lang/String;)Landroid/net/Uri;");
    intent_new = method(java, intent_type, "<init>", "(Ljava/lang/String;)V");
    set_type = method(java, intent_type, "setType", "(Ljava/lang/String;)Landroid/content/Intent;");
    put_parcel = method(java, intent_type, "putExtra", "(Ljava/lang/String;Landroid/os/Parcelable;)Landroid/content/Intent;");
    put_string = method(java, intent_type, "putExtra", "(Ljava/lang/String;Ljava/lang/String;)Landroid/content/Intent;");
    add_flags = method(java, intent_type, "addFlags", "(I)Landroid/content/Intent;");
    set_clip = method(java, intent_type, "setClipData", "(Landroid/content/ClipData;)V");
    new_raw_uri = static_method(java, clip_type, "newRawUri",
                                "(Ljava/lang/CharSequence;Landroid/net/Uri;)Landroid/content/ClipData;");
    create_chooser = static_method(java, intent_type, "createChooser",
                                   "(Landroid/content/Intent;Ljava/lang/CharSequence;)Landroid/content/Intent;");
    start = method(java, activity_type, "startActivity", "(Landroid/content/Intent;)V");
    text_address = string(java, address);
    action = string(java, "android.intent.action.SEND");
    mime = string(java, "text/plain");
    stream_key = string(java, "android.intent.extra.STREAM");
    subject_key = string(java, "android.intent.extra.SUBJECT");
    subject = string(java, "YFM Re-Decomp crash report");
    label = string(java, offer.file_name);
    title = string(java, "Share the crash report");
    if (java->bad) return 0;
    uri = (*env)->CallStaticObjectMethod(env, uri_type, parse, text_address);
    if (failed(java, "Naming the report", !uri)) return 0;
    intent = (*env)->NewObject(env, intent_type, intent_new, action);
    if (failed(java, "Making the share", !intent)) return 0;
    (*env)->CallObjectMethod(env, intent, set_type, mime);
    if (failed(java, "Making the share", 0)) return 0;
    (*env)->CallObjectMethod(env, intent, put_parcel, stream_key, uri);
    if (failed(java, "Attaching the report", 0)) return 0;
    (*env)->CallObjectMethod(env, intent, put_string, subject_key, subject);
    if (failed(java, "Making the share", 0)) return 0;
    clip = (*env)->CallStaticObjectMethod(env, clip_type, new_raw_uri, label, uri);
    if (failed(java, "Attaching the report", !clip)) return 0;
    (*env)->CallVoidMethod(env, intent, set_clip, clip);
    if (failed(java, "Attaching the report", 0)) return 0;
    (*env)->CallObjectMethod(env, intent, add_flags, (jint)1 /* FLAG_GRANT_READ_URI_PERMISSION */);
    if (failed(java, "Attaching the report", 0)) return 0;
    chooser = (*env)->CallStaticObjectMethod(env, intent_type, create_chooser, intent, title);
    if (failed(java, "Opening the share sheet", !chooser)) return 0;
    /* createChooser moves the grant and the ClipData onto the chooser
     * already; set again, in case a system does not. */
    (*env)->CallObjectMethod(env, chooser, add_flags, (jint)1);
    if (failed(java, "Opening the share sheet", 0)) return 0;
    (*env)->CallVoidMethod(env, activity, start, chooser);
    return !failed(java, "Opening the share sheet", 0);
}

static void java_call(void *argument)
{
    Java *java = argument;
    jobject activity;
#if defined(__aarch64__)
    Memories_JniGuard("the crash report's Java calls"); /* jni_guard.h: logs if this ran on the game stack */
#endif
    java->env = (JNIEnv *)SDL_GetAndroidJNIEnv();
    java->bad = 0;
    java->why[0] = '\0';
    if (!java->env) {
        snprintf(java->why, sizeof(java->why), "Java is not reachable from the game (%s).", SDL_GetError());
        java->bad = 1;
        return;
    }
    if ((*java->env)->PushLocalFrame(java->env, 64) < 0) {
        if ((*java->env)->ExceptionCheck(java->env)) (*java->env)->ExceptionClear(java->env);
        snprintf(java->why, sizeof(java->why), "Java has no room for the report's calls.");
        java->bad = 1;
        return;
    }
    if (!(activity = (jobject)SDL_GetAndroidActivity())) {
        if ((*java->env)->ExceptionCheck(java->env)) (*java->env)->ExceptionClear(java->env);
        snprintf(java->why, sizeof(java->why), "The game's activity is not reachable (%s).", SDL_GetError());
        java->bad = 1;
    } else if (java->share) {
        share(java, activity);
    } else {
        save_to_downloads(java, activity);
    }
    if ((*java->env)->ExceptionCheck(java->env)) (*java->env)->ExceptionClear(java->env);
    (*java->env)->PopLocalFrame(java->env, NULL);
}

/* --- the notice ------------------------------------------------------ */

static void chosen(int button, int *quit)
{
    static const char *const ok[] = {"OK"};
    Java call;
    char text[768];
    int save = offer.api >= DOWNLOADS_API;
    (void)quit;
    memset(&call, 0, sizeof(call));
    if (button == 0) {
        call.share = 1;
    } else if (button == 1 && save) {
        call.share = 0;
    } else {
        fprintf(stderr, "memories-pc: crash report %s: not now (offered again next launch)\n", offer.name);
        return;
    }
    Memories_OnHostStack(java_call, &call);
    if (!call.bad) {
        mark_handled();
        fprintf(stderr, "memories-pc: crash report %s: %s %s\n", offer.name,
                call.share ? "shared as" : "saved to Downloads as", offer.file_name);
        if (!call.share) {
            snprintf(text, sizeof(text), "It is in your Downloads folder as %s.", offer.file_name);
            Menu_ShowNotice("Report saved", text, ok, 1, 0, NULL);
        }
        return;
    }
    snprintf(text, sizeof(text), "%s\n\nIt is offered again the next time the game starts.",
             call.why[0] ? call.why : "Something went wrong.");
    Menu_ShowNotice(call.share ? "Report not shared" : "Report not saved", text, ok, 1, 0, NULL);
}

void Android_OfferCrashReport(void)
{
    static const char *const with_save[] = {"Share", "Save to Downloads", "Not now"};
    static const char *const share_only[] = {"Share", "Not now"};
    char value[PROP_VALUE_MAX];
    struct tm when;
    time_t seconds;
    /* Scripted and agent-driven runs are tests: nothing in their way (the
     * control channel's own notice would replace this one). */
    if (getenv("MEMORIES_INPUT") || getenv("MEMORIES_SDL_SCRIPT") || getenv("MEMORIES_HEADLESS") ||
        getenv("MEMORIES_CONTROL"))
        return;
    if (!find_report()) return;
    free(offer.text);
    if (!(offer.text = build_report(&offer.size))) {
        fprintf(stderr, "memories-pc: crash report %s could not be read\n", offer.path);
        return;
    }
    property("ro.build.version.sdk", value);
    offer.api = atoi(value);
    seconds = (time_t)offer.sec;
    localtime_r(&seconds, &when);
    strftime(offer.file_name, sizeof(offer.file_name), "yfm-redecomp-crash-%Y%m%d-%H%M%S.txt", &when);
    fprintf(stderr, "memories-pc: offering crash report %s (%zu bytes) as %s\n", offer.name, offer.size, offer.file_name);
    Menu_ShowNotice("The game stopped last time",
                    "A report of what happened helps fix it. It holds the game's version, your phone's model, "
                    "its Android version and free memory, and the game's crash log with its settings and mods: "
                    "no personal data and none of your saves.",
                    offer.api >= DOWNLOADS_API ? with_save : share_only, offer.api >= DOWNLOADS_API ? 3 : 2,
                    offer.api >= DOWNLOADS_API ? 2 : 1, chosen);
}
#endif
