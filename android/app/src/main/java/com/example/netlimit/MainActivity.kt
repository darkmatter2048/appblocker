package com.example.netlimit

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.net.VpnService
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import java.util.UUID

class MainActivity : AppCompatActivity() {

    private lateinit var etServerUrl: EditText
    private lateinit var etDeviceId: EditText
    private lateinit var btnStart: Button
    private lateinit var btnStop: Button
    private lateinit var tvStatus: TextView
    private lateinit var prefs: SharedPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        prefs = getSharedPreferences("config", Context.MODE_PRIVATE)

        etServerUrl = findViewById(R.id.etServerUrl)
        etDeviceId = findViewById(R.id.etDeviceId)
        btnStart = findViewById(R.id.btnStart)
        btnStop = findViewById(R.id.btnStop)
        tvStatus = findViewById(R.id.tvStatus)

        // Load saved values
        etServerUrl.setText(prefs.getString("server_url", "https://your-worker.workers.dev"))
        var deviceId = prefs.getString("device_id", "")
        if (deviceId.isNullOrEmpty()) {
            deviceId = UUID.randomUUID().toString().substring(0, 8)
            prefs.edit().putString("device_id", deviceId).apply()
        }
        etDeviceId.setText(deviceId)

        btnStart.setOnClickListener {
            val url = etServerUrl.text.toString()
            val id = etDeviceId.text.toString()
            
            if (url.isEmpty() || id.isEmpty()) {
                Toast.makeText(this, "Please enter Server URL and Device ID", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            prefs.edit().putString("server_url", url).putString("device_id", id).apply()

            val intent = VpnService.prepare(this)
            if (intent != null) {
                startActivityForResult(intent, 0)
            } else {
                onActivityResult(0, Activity.RESULT_OK, null)
            }
        }

        btnStop.setOnClickListener {
            val intent = Intent(this, NetworkControlService::class.java)
            intent.action = "STOP"
            startService(intent)
            tvStatus.text = "Status: Stopped"
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (resultCode == Activity.RESULT_OK) {
            val intent = Intent(this, NetworkControlService::class.java)
            intent.action = "START"
            intent.putExtra("server_url", etServerUrl.text.toString())
            intent.putExtra("device_id", etDeviceId.text.toString())
            startForegroundService(intent)
            tvStatus.text = "Status: Running (Check Notification)"
        }
    }
}
