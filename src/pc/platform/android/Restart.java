package org.yfmredecomp.game;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.Process;
import java.io.File;

/**
 * Starts the game again in a new process: Platform_RestartGame on Android
 * (src/pc/platform/android.c), where a restart cannot re-execute the
 * program as it does on a desktop.
 *
 * The game's process maps its guest memory at fixed addresses and keeps the
 * game library loaded, so the new game needs a new process: this activity
 * runs in a process of its own (":restart", tools/pc/package_android.py),
 * started by the game while it is in the foreground. It ends the game's
 * process (the "pid" extra), waits for it to be gone (SDLActivity is
 * singleInstance: a live one would only be brought back), launches the
 * game as the launcher does, and ends its own process. Nothing is shown.
 */
public class Restart extends Activity {
    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        int pid = getIntent().getIntExtra("pid", 0);
        if (pid > 0 && pid != Process.myPid()) {
            Process.killProcess(pid);
            File proc = new File("/proc/" + pid + "/cmdline");
            for (int i = 0; i < 150 && proc.exists(); i++) {
                try {
                    Thread.sleep(20);
                } catch (InterruptedException e) {
                    break;
                }
            }
        }
        Intent launch = getPackageManager().getLaunchIntentForPackage(getPackageName());
        if (launch != null) {
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            startActivity(launch);
        }
        finish();
        Runtime.getRuntime().exit(0);
    }
}
