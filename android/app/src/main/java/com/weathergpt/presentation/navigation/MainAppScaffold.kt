package com.weathergpt.presentation.navigation

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.weathergpt.domain.model.chat.DomainBrain
import com.weathergpt.presentation.alerts.AlertsScreen
import com.weathergpt.presentation.alerts.AlertsViewModel
import com.weathergpt.presentation.analyst.AnalystDashboardScreen
import com.weathergpt.presentation.analyst.AnalystDashboardViewModel
import com.weathergpt.presentation.brain.BrainSelectionScreen
import com.weathergpt.presentation.brain.BrainSelectionViewModel
import com.weathergpt.presentation.chat.ChatScreen
import com.weathergpt.presentation.chat.ChatViewModel
import com.weathergpt.presentation.components.AppTopBar
import com.weathergpt.presentation.components.BottomNavigationBar
import com.weathergpt.presentation.components.IntelligenceBrain
import com.weathergpt.presentation.data.DataScreen
import com.weathergpt.presentation.data.DataViewModel
import com.weathergpt.presentation.farmer.FarmerProfileScreen
import com.weathergpt.presentation.farmer.FarmerProfileViewModel
import com.weathergpt.presentation.home.HomeScreen
import com.weathergpt.presentation.home.HomeViewModel
import com.weathergpt.presentation.main.MainViewModel
import com.weathergpt.presentation.map.MapScreen
import com.weathergpt.presentation.map.MapViewModel
import com.weathergpt.presentation.profile.ProfileScreen
import com.weathergpt.presentation.profile.ProfileViewModel
import com.weathergpt.presentation.settings.SettingsScreen
import com.weathergpt.presentation.settings.SettingsViewModel
import com.weathergpt.presentation.weather.WeatherScreen
import com.weathergpt.presentation.weather.WeatherViewModel

@Composable
fun MainAppScaffold(
    mainViewModel: MainViewModel,
    navigationState: NavigationState = rememberNavigationState(),
    modifier: Modifier = Modifier
) {
    // ViewModel instances with scoped lifecycle preservation
    val homeViewModel: HomeViewModel = viewModel(factory = HomeViewModel.Factory)
    val brainSelectionViewModel: BrainSelectionViewModel = viewModel(factory = BrainSelectionViewModel.Factory)
    val weatherViewModel: WeatherViewModel = viewModel(factory = WeatherViewModel.Factory)
    val mapViewModel: MapViewModel = viewModel(factory = MapViewModel.Factory)
    val alertsViewModel: AlertsViewModel = viewModel(factory = AlertsViewModel.Factory)
    val dataViewModel: DataViewModel = viewModel(factory = DataViewModel.Factory)
    val farmerProfileViewModel: FarmerProfileViewModel = viewModel(factory = FarmerProfileViewModel.Factory)
    val analystDashboardViewModel: AnalystDashboardViewModel = viewModel(factory = AnalystDashboardViewModel.Factory)
    val settingsViewModel: SettingsViewModel = viewModel(factory = SettingsViewModel.Factory)
    val profileViewModel: ProfileViewModel = viewModel(factory = ProfileViewModel.Factory)
    val chatViewModel: ChatViewModel = viewModel(factory = ChatViewModel.Factory)

    // Handle deep-link pending navigation from push notifications
    val pendingDest by mainViewModel.pendingDestination.collectAsStateWithLifecycle()
    LaunchedEffect(pendingDest) {
        pendingDest?.let {
            navigationState.navigateTo(it)
            mainViewModel.clearPendingDestination()
        }
    }

    // Handle system back navigation
    val canGoBack = navigationState.backStack.isNotEmpty()
    BackHandler(enabled = canGoBack) {
        navigationState.navigateBack()
    }

    val currentDestination = navigationState.currentDestination

    val isRootDestination = currentDestination in listOf(
        ScreenDestination.Home,
        ScreenDestination.Map,
        ScreenDestination.Alerts,
        ScreenDestination.Data,
        ScreenDestination.Profile
    )

    val showTopBar = currentDestination !is ScreenDestination.Home && currentDestination !is ScreenDestination.Profile

    val topBarTitle = when (currentDestination) {
        is ScreenDestination.Home -> androidx.compose.ui.res.stringResource(com.weathergpt.R.string.app_name)
        is ScreenDestination.Map -> androidx.compose.ui.res.stringResource(com.weathergpt.R.string.map_title)
        is ScreenDestination.Alerts -> androidx.compose.ui.res.stringResource(com.weathergpt.R.string.alerts_title)
        is ScreenDestination.Data -> androidx.compose.ui.res.stringResource(com.weathergpt.R.string.data_title)
        is ScreenDestination.Profile -> androidx.compose.ui.res.stringResource(com.weathergpt.R.string.profile_title)
        is ScreenDestination.BrainSelection -> androidx.compose.ui.res.stringResource(com.weathergpt.R.string.brain_selection_title)
        is ScreenDestination.WeatherDetails -> androidx.compose.ui.res.stringResource(com.weathergpt.R.string.weather_title)
        is ScreenDestination.FarmerProfile -> androidx.compose.ui.res.stringResource(com.weathergpt.R.string.farmer_title)
        is ScreenDestination.AnalystDashboard -> androidx.compose.ui.res.stringResource(com.weathergpt.R.string.analyst_title)
        is ScreenDestination.Settings -> androidx.compose.ui.res.stringResource(com.weathergpt.R.string.settings_title)
        is ScreenDestination.Chat -> androidx.compose.ui.res.stringResource(com.weathergpt.R.string.chat_title)
        is ScreenDestination.SystemStatus -> "System & Data Status"
    }

    val topBarSubtitle = when (currentDestination) {
        is ScreenDestination.BrainSelection -> androidx.compose.ui.res.stringResource(com.weathergpt.R.string.brain_selection_subtitle)
        else -> null
    }

    Scaffold(
        topBar = {
            if (showTopBar) {
                AppTopBar(
                    title = topBarTitle,
                    subtitle = topBarSubtitle,
                    showBackButton = true,
                    onNavigationClick = {
                        navigationState.navigateBack()
                    },
                    actions = {
                        when (currentDestination) {
                            is ScreenDestination.WeatherDetails -> {
                                IconButton(onClick = {}) {
                                    Text(text = "⭐", fontSize = 16.sp)
                                }
                            }

                            is ScreenDestination.Data, is ScreenDestination.AnalystDashboard -> {
                                IconButton(onClick = {}) {
                                    Text(text = "🎛️", fontSize = 16.sp)
                                }
                            }
                            else -> {}
                        }
                    }
                )
            }
        },
        bottomBar = {
            // Show bottom navigation bar on all primary tabs and detail screens
            if (currentDestination !is ScreenDestination.BrainSelection && currentDestination !is ScreenDestination.FarmerProfile) {
                BottomNavigationBar(
                    currentTab = navigationState.currentBottomTab,
                    onTabSelected = { tab -> navigationState.navigateToBottomTab(tab) }
                )
            }
        },
        modifier = modifier.fillMaxSize()
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            when (currentDestination) {
                is ScreenDestination.Home -> {
                    HomeScreen(
                        viewModel = homeViewModel,
                        onNavigateToBrainSelection = { navigationState.navigateTo(ScreenDestination.BrainSelection) },
                        onNavigateToWeather = { navigationState.navigateTo(ScreenDestination.WeatherDetails) },
                        onNavigateToMap = { navigationState.navigateTo(ScreenDestination.Map) },
                        onNavigateToAlerts = { navigationState.navigateTo(ScreenDestination.Alerts) },
                        onNavigateToFarmer = { navigationState.navigateTo(ScreenDestination.FarmerProfile) },
                        onNavigateToData = { navigationState.navigateTo(ScreenDestination.Data) },
                        onNavigateToChat = { query ->
                            if (!query.isNullOrBlank()) {
                                chatViewModel.sendMessage(query)
                            }
                            navigationState.navigateTo(ScreenDestination.Chat)
                        },
                        onNavigateToSystemStatus = { navigationState.navigateTo(ScreenDestination.SystemStatus) }
                    )
                }
                is ScreenDestination.BrainSelection -> {
                    BrainSelectionScreen(
                        viewModel = brainSelectionViewModel,
                        onBrainSelectedAndConfirmed = { brain ->
                            homeViewModel.selectBrain(brain)
                            val domainBrain = when (brain) {
                                IntelligenceBrain.AUTO -> DomainBrain.AUTO
                                IntelligenceBrain.GENERAL -> DomainBrain.GENERAL
                                IntelligenceBrain.FARMER -> DomainBrain.FARMER
                                IntelligenceBrain.RESEARCHER -> DomainBrain.RESEARCHER
                                IntelligenceBrain.ANALYST -> DomainBrain.ANALYST
                            }
                            chatViewModel.selectBrain(domainBrain)
                            navigationState.navigateBack()
                        }
                    )
                }
                is ScreenDestination.WeatherDetails -> {
                    WeatherScreen(viewModel = weatherViewModel)
                }
                is ScreenDestination.Map -> {
                    MapScreen(viewModel = mapViewModel)
                }
                is ScreenDestination.Alerts -> {
                    AlertsScreen(
                        viewModel = alertsViewModel,
                        onAssessImpact = { query ->
                            chatViewModel.sendMessage(query)
                            navigationState.navigateTo(ScreenDestination.Chat)
                        }
                    )
                }
                is ScreenDestination.Data -> {
                    DataScreen(
                        viewModel = dataViewModel,
                        onNavigateToAnalyst = { navigationState.navigateTo(ScreenDestination.AnalystDashboard) }
                    )
                }
                is ScreenDestination.FarmerProfile -> {
                    FarmerProfileScreen(
                        viewModel = farmerProfileViewModel,
                        onSavedSuccessfully = { navigationState.navigateBack() }
                    )
                }
                is ScreenDestination.AnalystDashboard -> {
                    AnalystDashboardScreen(viewModel = analystDashboardViewModel)
                }
                is ScreenDestination.Settings -> {
                    SettingsScreen(
                        viewModel = settingsViewModel,
                        onNavigateToFarmerProfile = { navigationState.navigateTo(ScreenDestination.FarmerProfile) },
                        onNavigateToFieldDetails = { navigationState.navigateTo(ScreenDestination.FarmerProfile) }
                    )
                }
                is ScreenDestination.Profile -> {
                    ProfileScreen(
                        viewModel = profileViewModel,
                        onNavigateToFarmerProfile = { navigationState.navigateTo(ScreenDestination.FarmerProfile) },
                        onNavigateToSettings = { navigationState.navigateTo(ScreenDestination.Settings) }
                    )
                }
                is ScreenDestination.Chat -> {
                    ChatScreen(viewModel = chatViewModel)
                }
                is ScreenDestination.SystemStatus -> {
                    com.weathergpt.presentation.status.SystemStatusScreen(
                        onNavigateBack = { navigationState.navigateBack() }
                    )
                }
            }
        }
    }
}
