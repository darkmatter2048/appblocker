package com.example.netlimit

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.net.VpnService
import android.os.Build
import android.os.ParcelFileDescriptor
import android.util.Log
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.FileInputStream
import java.util.concurrent.TimeUnit

class NetworkControlService : VpnService() {

    private var isRunning = false
    private var vpnInterface: ParcelFileDescriptor? = null
    private var serverUrl: String = ""
    private var deviceId: String = ""
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .build()

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "STOP") {
            stopVpn()
            stopSelf()
            return START_NOT_STICKY
        }

        if (intent?.action == "START") {
            serverUrl = intent.getStringExtra("server_url") ?: ""
            deviceId = intent.getStringExtra("device_id") ?: ""
        }

        createNotificationChannel()
        val notificationIntent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, notificationIntent, PendingIntent.FLAG_IMMUTABLE
        )

        val notification = Notification.Builder(this, "NET_LIMIT_CHANNEL")
            .setContentTitle("Network Controller")
            .setContentText("Monitoring network policy...")
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentIntent(pendingIntent)
            .build()

        startForeground(1, notification)

        if (!isRunning) {
            isRunning = true
            Thread { monitorLoop() }.start()
        }

        return START_STICKY
    }

    private fun monitorLoop() {
        while (isRunning) {
            try {
                if (serverUrl.isNotEmpty()) {
                    checkPolicy()
                }
                Thread.sleep(3000) // Poll every 3 seconds
            } catch (e: Exception) {
                Log.e("NetLimit", "Loop error", e)
            }
        }
    }

    private fun checkPolicy() {
        try {
            val url = "$serverUrl/status?id=$deviceId"
            val request = Request.Builder().url(url).build()
            val response = client.newCall(request).execute()
            
            if (response.isSuccessful) {
                val json = JSONObject(response.body?.string() ?: "{}")
                val shouldBlock = json.optBoolean("blocked", false)
                
                if (shouldBlock && vpnInterface == null) {
                    startBlocking()
                } else if (!shouldBlock && vpnInterface != null) {
                    stopBlocking()
                }
            }
            response.close()
        } catch (e: Exception) {
            Log.e("NetLimit", "Network error", e)
        }
    }

    private fun startBlocking() {
        Log.i("NetLimit", "Starting Block (VPN)")
        try {
            val builder = Builder()
            
            // Add a route that covers everything to hijack all traffic
            builder.addAddress("10.0.0.2", 24)
            builder.addRoute("0.0.0.0", 0)
            
            // Setting session name
            builder.setSession("Internet Blocked by Admin")
            
            // Critical: Exclude our own app so we can still poll the server to unblock!
            try {
                builder.addDisallowedApplication(packageName)
            } catch (e: Exception) {
                Log.e("NetLimit", "Could not exclude app", e)
            }

            builder.setBlocking(true)

            vpnInterface = builder.establish()
            
            // We need to read from the interface to keep it active (and prevent buffer full issues),
            // but we simply discard the data to create a "Blackhole".
            Thread {
                try {
                    val inputStream = FileInputStream(vpnInterface?.fileDescriptor)
                    val buffer = ByteArray(32767)
                    while (vpnInterface != null) {
                        // Read and drop (packet loss = 100%)
                        val len = inputStream.read(buffer)
                        if (len == -1) break
                    }
                } catch (e: Exception) {
                    Log.e("NetLimit", "VPN Read Error", e)
                }
            }.start()
            
        } catch (e: Exception) {
            Log.e("NetLimit", "Failed to start VPN", e)
        }
    }

    private fun stopBlocking() {
        Log.i("NetLimit", "Stopping Block (VPN)")
        try {
            vpnInterface?.close()
            vpnInterface = null
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun stopVpn() {
        isRunning = false
        stopBlocking()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val serviceChannel = NotificationChannel(
                "NET_LIMIT_CHANNEL",
                "Network Limit Service",
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(serviceChannel)
        }
    }
}
