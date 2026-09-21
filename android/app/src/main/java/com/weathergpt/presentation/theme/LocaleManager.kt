package com.weathergpt.presentation.theme

import android.content.res.Configuration
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import com.weathergpt.core.settings.AppLanguage
import java.util.Locale

/**
 * Provides a dynamic localized [android.content.Context] to Compose subtrees,
 * allowing instant runtime language switching between English and Hindi
 * without requiring Activity recreation or app restarts.
 */
@Composable
fun ProvideAppLanguage(
    language: AppLanguage,
    content: @Composable () -> Unit
) {
    val context = LocalContext.current
    val (localizedContext, localizedConfig) = remember(context, language) {
        val locale = Locale(language.code)
        Locale.setDefault(locale)
        val config = Configuration(context.resources.configuration).apply {
            setLocale(locale)
            setLayoutDirection(locale)
        }
        val ctx = context.createConfigurationContext(config)
        Pair(ctx, config)
    }

    val activityResultRegistryOwner = androidx.activity.compose.LocalActivityResultRegistryOwner.current
        ?: (context as? androidx.activity.result.ActivityResultRegistryOwner)

    val providers = mutableListOf<androidx.compose.runtime.ProvidedValue<*>>(
        LocalContext provides localizedContext,
        androidx.compose.ui.platform.LocalConfiguration provides localizedConfig
    )
    if (activityResultRegistryOwner != null) {
        providers.add(androidx.activity.compose.LocalActivityResultRegistryOwner provides activityResultRegistryOwner)
    }

    CompositionLocalProvider(
        *providers.toTypedArray(),
        content = content
    )
}
