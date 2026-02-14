package com.example.netlimiter

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

class LimitVpnService : VpnService() {

    private var interfaceParams: ParcelFileDescriptor? = null
    private var isRunning = false
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .build()

    // TODO: 部署完Worker后，请务必修改这里的URL！
    private val CONTROL_URL = "https://REPLACE_WITH_YOUR_WORKER_URL/api/check"

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(1, createNotification("System Network Service"))
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!isRunning) {
            isRunning = true
            startControlLoop()
        }
        return START_STICKY
    }

    override fun onDestroy() {
        isRunning = false
        stopVpn()
        super.onDestroy()
    }

    private fun startControlLoop() {
        thread {
            while (isRunning) {
                try {
                    if (CONTROL_URL.contains("REPLACE")) {
                        Log.e("VPN", "URL not set! Please modify source code.")
                        Thread.sleep(5000)
                        continue
                    }
                    
                    val request = Request.Builder().url(CONTROL_URL).build()
                    val response = client.newCall(request).execute()
                    val body = response.body?.string()
                    val shouldLimit = body?.contains("\"limited\":true") == true

                    if (shouldLimit && interfaceParams == null) {
                        startVpnBlock()
                    } else if (!shouldLimit && interfaceParams != null) {
                        stopVpn()
                    }
                    Thread.sleep(10000) 
                } catch (e: Exception) {
                    e.printStackTrace()
                    Thread.sleep(20000)
                }
            }
        }
    }

    private fun startVpnBlock() {
        try {
            val builder = Builder()
            builder.setSession("NetLimiter")
            builder.addAddress("10.0.0.2", 24)
            builder.addRoute("0.0.0.0", 0)
            builder.addDisallowedApplication(packageName)
            interfaceParams = builder.establish()
        } catch (e: Exception) { e.printStackTrace() }
    }

    private fun stopVpn() {
        try {
            interfaceParams?.close()
            interfaceParams = null
        } catch (e: Exception) { e.printStackTrace() }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel("srv", "System", NotificationManager.IMPORTANCE_LOW)
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    private fun createNotification(text: String): Notification {
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(this, "srv") else Notification.Builder(this)
        return builder.setContentTitle("System").setContentText(text).setSmallIcon(android.R.drawable.stat_sys_download).build()
    }
}