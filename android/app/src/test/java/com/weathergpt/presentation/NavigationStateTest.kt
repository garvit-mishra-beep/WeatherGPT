package com.weathergpt.presentation

import com.weathergpt.presentation.components.BottomNavTab
import com.weathergpt.presentation.navigation.NavigationState
import com.weathergpt.presentation.navigation.ScreenDestination
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class NavigationStateTest {

    @Test
    fun initialDestination_isHome() {
        val navState = NavigationState()
        assertEquals(ScreenDestination.Home, navState.currentDestination)
        assertEquals(BottomNavTab.HOME, navState.currentBottomTab)
        assertTrue(navState.backStack.isEmpty())
    }

    @Test
    fun navigateTo_updatesCurrentDestinationAndBackStack() {
        val navState = NavigationState()
        navState.navigateTo(ScreenDestination.BrainSelection)

        assertEquals(ScreenDestination.BrainSelection, navState.currentDestination)
        assertEquals(1, navState.backStack.size)
        assertEquals(ScreenDestination.Home, navState.backStack.first())
    }

    @Test
    fun navigateBack_restoresPreviousDestination() {
        val navState = NavigationState()
        navState.navigateTo(ScreenDestination.WeatherDetails)
        navState.navigateTo(ScreenDestination.FarmerProfile)

        assertEquals(ScreenDestination.FarmerProfile, navState.currentDestination)
        assertEquals(2, navState.backStack.size)

        val handled1 = navState.navigateBack()
        assertTrue(handled1)
        assertEquals(ScreenDestination.WeatherDetails, navState.currentDestination)

        val handled2 = navState.navigateBack()
        assertTrue(handled2)
        assertEquals(ScreenDestination.Home, navState.currentDestination)

        val handled3 = navState.navigateBack()
        assertFalse(handled3)
        assertEquals(ScreenDestination.Home, navState.currentDestination)
    }

    @Test
    fun navigateToBottomTab_clearsBackStackAndSetsTab() {
        val navState = NavigationState()
        navState.navigateTo(ScreenDestination.BrainSelection)
        navState.navigateTo(ScreenDestination.WeatherDetails)
        assertEquals(2, navState.backStack.size)

        navState.navigateToBottomTab(BottomNavTab.MAP)
        assertEquals(ScreenDestination.Map, navState.currentDestination)
        assertEquals(BottomNavTab.MAP, navState.currentBottomTab)
        assertTrue(navState.backStack.isEmpty())
    }
}
