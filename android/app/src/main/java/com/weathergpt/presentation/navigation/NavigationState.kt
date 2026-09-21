package com.weathergpt.presentation.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.Stable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import com.weathergpt.presentation.components.BottomNavTab

sealed class ScreenDestination(val route: String) {
    data object Home : ScreenDestination("home")
    data object Map : ScreenDestination("map")
    data object Alerts : ScreenDestination("alerts")
    data object Data : ScreenDestination("data")
    data object Profile : ScreenDestination("profile")
    data object BrainSelection : ScreenDestination("brain_selection")
    data object WeatherDetails : ScreenDestination("weather_details")
    data object FarmerProfile : ScreenDestination("farmer_profile")
    data object AnalystDashboard : ScreenDestination("analyst_dashboard")
    data object Settings : ScreenDestination("settings")
    data object Chat : ScreenDestination("chat")
    data object SystemStatus : ScreenDestination("system_status")
}

@Stable
class NavigationState(
    initialDestination: ScreenDestination = ScreenDestination.Home
) {
    var currentDestination by mutableStateOf(initialDestination)
        private set

    val backStack = mutableStateListOf<ScreenDestination>()

    val currentBottomTab: BottomNavTab
        get() = when (currentDestination) {
            is ScreenDestination.Home -> BottomNavTab.HOME
            is ScreenDestination.Map -> BottomNavTab.MAP
            is ScreenDestination.Alerts -> BottomNavTab.ALERTS
            is ScreenDestination.Data -> BottomNavTab.DATA
            is ScreenDestination.Profile -> BottomNavTab.PROFILE
            else -> BottomNavTab.HOME
        }

    fun navigateTo(destination: ScreenDestination) {
        if (currentDestination != destination) {
            backStack.add(currentDestination)
            currentDestination = destination
        }
    }

    fun navigateToBottomTab(tab: BottomNavTab) {
        val destination = when (tab) {
            BottomNavTab.HOME -> ScreenDestination.Home
            BottomNavTab.MAP -> ScreenDestination.Map
            BottomNavTab.ALERTS -> ScreenDestination.Alerts
            BottomNavTab.DATA -> ScreenDestination.Data
            BottomNavTab.PROFILE -> ScreenDestination.Profile
        }
        // When tapping bottom tabs, clear subscreen backstack to reset to root tab
        backStack.clear()
        currentDestination = destination
    }

    fun navigateBack(): Boolean {
        if (backStack.isNotEmpty()) {
            currentDestination = backStack.removeAt(backStack.size - 1)
            return true
        }
        return false
    }
}

@Composable
fun rememberNavigationState(
    initialDestination: ScreenDestination = ScreenDestination.Home
): NavigationState = remember {
    NavigationState(initialDestination = initialDestination)
}
