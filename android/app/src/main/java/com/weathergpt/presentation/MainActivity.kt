package com.weathergpt.presentation

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.weathergpt.presentation.main.MainViewModel
import com.weathergpt.presentation.navigation.MainAppScaffold
import com.weathergpt.presentation.theme.ProvideAppLanguage
import com.weathergpt.presentation.theme.WeatherGPTTheme

/**
 * WeatherGPT MainActivity.
 *
 * Hosts the complete frontend screen hierarchy, bottom navigation, and domain destinations
 * wrapped in dynamic runtime localization (English + Hindi).
 */
class MainActivity : ComponentActivity() {

    private val viewModel: MainViewModel by viewModels { MainViewModel.Factory }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val appLanguage by viewModel.appLanguage.collectAsStateWithLifecycle()
            ProvideAppLanguage(language = appLanguage) {
                WeatherGPTTheme {
                    MainAppScaffold(mainViewModel = viewModel)
                }
            }
        }
    }
}
