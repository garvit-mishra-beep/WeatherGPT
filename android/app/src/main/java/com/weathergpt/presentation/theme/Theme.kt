package com.weathergpt.presentation.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val LightColorScheme = lightColorScheme(
    primary = WeatherPrimary,
    onPrimary = WeatherOnPrimary,
    primaryContainer = WeatherPrimaryContainer,
    onPrimaryContainer = WeatherPrimary,
    secondary = WeatherSecondary,
    onSecondary = WeatherOnSecondary,
    secondaryContainer = WeatherSecondaryContainer,
    onSecondaryContainer = WeatherSecondary,
    tertiary = WeatherTertiary,
    background = WeatherBackground,
    surface = WeatherSurface,
    surfaceVariant = WeatherSurfaceVariant,
    onSurface = WeatherOnSurface,
    onSurfaceVariant = WeatherOnSurfaceVariant,
    outline = WeatherOutline,
    outlineVariant = WeatherOutline
)

private val DarkColorScheme = darkColorScheme(
    primary = WeatherPrimaryDark,
    onPrimary = WeatherOnSurfaceDark,
    primaryContainer = WeatherSurfaceVariantDark,
    secondary = WeatherSecondary,
    background = WeatherSurfaceDark,
    surface = WeatherSurfaceDark,
    surfaceVariant = WeatherSurfaceVariantDark,
    onSurface = WeatherOnSurfaceDark,
    outline = WeatherOutline
)

@Composable
fun WeatherGPTTheme(
    darkTheme: Boolean = false, // Enforce Pragya's approved eco-light prototype design
    content: @Composable () -> Unit
) {
    val colorScheme = LightColorScheme

    MaterialTheme(
        colorScheme = colorScheme,
        typography = WeatherTypography,
        content = content
    )
}
