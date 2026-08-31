package com.weathergpt.presentation.components

import androidx.compose.foundation.border
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.outlined.Email
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.LocationOn
import androidx.compose.material.icons.outlined.Notifications
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

import androidx.annotation.StringRes
import androidx.compose.ui.res.stringResource
import com.weathergpt.R

enum class BottomNavTab(
    val route: String,
    @StringRes val titleResId: Int,
    val selectedIcon: ImageVector,
    val unselectedIcon: ImageVector
) {
    HOME("home", R.string.nav_chat, Icons.Filled.Email, Icons.Outlined.Email),
    MAP("map", R.string.nav_map, Icons.Filled.LocationOn, Icons.Outlined.LocationOn),
    ALERTS("alerts", R.string.nav_alerts, Icons.Filled.Notifications, Icons.Outlined.Notifications),
    DATA("data", R.string.nav_data, Icons.Filled.Info, Icons.Outlined.Info),
    PROFILE("profile", R.string.nav_profile, Icons.Filled.Person, Icons.Outlined.Person)
}

@Composable
fun BottomNavigationBar(
    currentTab: BottomNavTab,
    onTabSelected: (BottomNavTab) -> Unit,
    modifier: Modifier = Modifier
) {
    NavigationBar(
        containerColor = Color.White,
        contentColor = Color(0xFF0F172A),
        tonalElevation = 4.dp,
        modifier = modifier
            .height(64.dp)
            .border(width = 1.dp, color = Color(0xFFF1F5F9))
    ) {
        BottomNavTab.entries.forEach { tab ->
            val selected = currentTab == tab
            val tabTitle = stringResource(tab.titleResId)
            NavigationBarItem(
                selected = selected,
                onClick = { onTabSelected(tab) },
                icon = {
                    Icon(
                        imageVector = if (selected) tab.selectedIcon else tab.unselectedIcon,
                        contentDescription = tabTitle,
                        modifier = Modifier.size(22.dp)
                    )
                },
                label = {
                    Text(
                        text = tabTitle,
                        fontSize = 11.sp,
                        fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium
                    )
                },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = Color(0xFF1B5E20),
                    selectedTextColor = Color(0xFF1B5E20),
                    indicatorColor = Color(0xFFE8F5E9),
                    unselectedIconColor = Color(0xFF64748B),
                    unselectedTextColor = Color(0xFF64748B)
                )
            )
        }
    }
}