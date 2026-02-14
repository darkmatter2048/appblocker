package com.example.netlimiter

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

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val layout = LinearLayout(this)
        layout.gravity = Gravity.CENTER
        val btn = Button(this)
        btn.text = "Activate & Hide Icon"
        btn.setOnClickListener { checkAndStart() }
        layout.addView(btn)
        setContentView(layout)
    }

    private fun checkAndStart() {
        val intent = VpnService.prepare(this)
        if (intent != null) {
            startActivityForResult(intent, 0)
        } else {
            onActivityResult(0, RESULT_OK, null)
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        if (resultCode == RESULT_OK) {
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
        }
    }
}