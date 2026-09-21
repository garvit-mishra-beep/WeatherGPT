package com.weathergpt.presentation

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.runtime.getValue
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.weathergpt.core.push.WeatherGPTFirebaseMessagingService
import com.weathergpt.presentation.main.MainViewModel
import com.weathergpt.presentation.navigation.MainAppScaffold
import com.weathergpt.presentation.navigation.ScreenDestination
import com.weathergpt.presentation.theme.ProvideAppLanguage
import com.weathergpt.presentation.theme.WeatherGPTTheme

/**
 * WeatherGPT MainActivity.
 *
 * Hosts the complete frontend screen hierarchy, bottom navigation, and domain destinations
 * wrapped in dynamic runtime localization (English + Hindi).
 * Handles Android 13+ POST_NOTIFICATIONS permission and proactive notification deep-linking.
 */
class MainActivity : ComponentActivity() {

    private val viewModel: MainViewModel by viewModels { MainViewModel.Factory }

    private val requestNotificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        if (isGranted) {
            Log.i("MainActivity", "POST_NOTIFICATIONS permission granted by user")
        } else {
            Log.w("MainActivity", "POST_NOTIFICATIONS permission denied by user (push notifications will be muted)")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        checkNotificationPermission()
        handleNotificationDeepLink(intent)

        setContent {
            val appLanguage by viewModel.appLanguage.collectAsStateWithLifecycle()
            androidx.compose.runtime.CompositionLocalProvider(
                androidx.activity.compose.LocalActivityResultRegistryOwner provides this
            ) {
                ProvideAppLanguage(language = appLanguage) {
                    WeatherGPTTheme {
                        MainAppScaffold(mainViewModel = viewModel)
                    }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleNotificationDeepLink(intent)
    }

    private fun checkNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            val currentPermission = ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.POST_NOTIFICATIONS
            )
            if (currentPermission != PackageManager.PERMISSION_GRANTED) {
                requestNotificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }

    private fun handleNotificationDeepLink(intent: Intent?) {
        val eventId = intent?.getStringExtra(WeatherGPTFirebaseMessagingService.EXTRA_EVENT_ID)
        val targetScreen = intent?.getStringExtra(WeatherGPTFirebaseMessagingService.EXTRA_TARGET_SCREEN)
        if (!eventId.isNullOrBlank()) {
            Log.i("MainActivity", "Notification deep link received for eventId=$eventId, targetScreen=$targetScreen")
            when (targetScreen?.lowercase()) {
                "alerts" -> viewModel.navigateTo(ScreenDestination.Alerts)
                "farmer" -> viewModel.navigateTo(ScreenDestination.FarmerProfile)
                else -> viewModel.navigateTo(ScreenDestination.Home)
            }
        }
    }
}
