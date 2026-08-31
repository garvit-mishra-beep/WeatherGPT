package com.weathergpt.presentation.main

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.weathergpt.core.config.AppConfig
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.HealthStatus

import androidx.compose.foundation.layout.Row
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.TextButton
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import com.weathergpt.BuildConfig

/**
 * Technical Foundation Bootstrap Screen.
 *
 * IMPORTANT ARCHITECTURAL NOTICE:
 * This screen is strictly a technical shell to verify the Android build, architecture,
 * and backend connectivity.
 *
 * DO NOT treat this as the final UI design.
 * FINAL UI/UX, SCREEN LAYOUTS, AND VISUAL STYLING ARE OWNED AND DESIGNED BY PRAGYA.
 */
@Composable
fun MainShellScreen(
    viewModel: MainViewModel,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val healthState by viewModel.healthState.collectAsStateWithLifecycle()
    val currentBaseUrl by viewModel.currentBaseUrl.collectAsStateWithLifecycle()
    val validationError by viewModel.urlValidationError.collectAsStateWithLifecycle()

    var showUrlDialog by remember { mutableStateOf(false) }
    var inputUrlText by remember { mutableStateOf("") }

    if (showUrlDialog) {
        AlertDialog(
            onDismissRequest = {
                showUrlDialog = false
                viewModel.clearValidationError()
            },
            title = { Text("Configure Local Backend (Debug)") },
            text = {
                Column {
                    Text(
                        text = "Enter LAN URL (e.g. http://192.168.1.100:8000/) or paste scanned QR payload:",
                        style = MaterialTheme.typography.bodySmall
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = inputUrlText,
                        onValueChange = { inputUrlText = it },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        placeholder = { Text("http://192.168.x.x:8000/") },
                        isError = validationError != null
                    )
                    if (validationError != null) {
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = validationError ?: "",
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val success = viewModel.updateBackendUrl(inputUrlText, context)
                        if (success) {
                            showUrlDialog = false
                        }
                    }
                ) {
                    Text("Apply & Connect")
                }
            },
            dismissButton = {
                TextButton(
                    onClick = {
                        showUrlDialog = false
                        viewModel.clearValidationError()
                    }
                ) {
                    Text("Cancel")
                }
            }
        )
    }

    Scaffold(modifier = modifier.fillMaxSize()) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(24.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "WeatherGPT Android Foundation",
                style = MaterialTheme.typography.headlineMedium
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "Milestone P5.1 — Technical Shell (UI/UX Owned by Pragya)",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(24.dp))

            Card(
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    horizontalAlignment = Alignment.Start
                ) {
                    Text(
                        text = "Backend Configuration",
                        style = MaterialTheme.typography.titleMedium
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Base URL: $currentBaseUrl",
                        style = MaterialTheme.typography.bodySmall
                    )
                    Text(
                        text = "Environment: ${AppConfig.environment}",
                        style = MaterialTheme.typography.bodySmall
                    )

                    if (BuildConfig.DEBUG) {
                        Spacer(modifier = Modifier.height(12.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            OutlinedButton(
                                onClick = {
                                    inputUrlText = currentBaseUrl
                                    showUrlDialog = true
                                },
                                modifier = Modifier.weight(1f)
                            ) {
                                Text("Enter / Scan URL")
                            }

                            OutlinedButton(
                                onClick = { viewModel.resetBackendUrl(context) },
                                modifier = Modifier.weight(1f)
                            ) {
                                Text("Reset to USB")
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Card(
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "Backend Connectivity Status",
                        style = MaterialTheme.typography.titleMedium
                    )
                    Spacer(modifier = Modifier.height(12.dp))

                    when (val state = healthState) {
                        is ResultState.Idle -> {
                            Text("Status: Idle", style = MaterialTheme.typography.bodyMedium)
                        }
                        is ResultState.Loading -> {
                            CircularProgressIndicator()
                            Spacer(modifier = Modifier.height(8.dp))
                            Text("Probing /api/v1/health...", style = MaterialTheme.typography.bodySmall)
                        }
                        is ResultState.Success<HealthStatus> -> {
                            val health = state.data
                            Text(
                                text = "Connected: ${health.status.uppercase()} (${health.environment})",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.primary
                            )
                            Text(
                                text = "API Version: ${health.apiVersion}",
                                style = MaterialTheme.typography.bodySmall
                            )
                            Text(
                                text = "Server Time: ${health.timestamp}",
                                style = MaterialTheme.typography.bodySmall
                            )
                        }
                        is ResultState.Error -> {
                            Text(
                                text = "Connection Failed: ${state.error.message}",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.error
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            Button(
                onClick = { viewModel.verifyBackendConnectivity() }
            ) {
                Text("Test Connection")
            }
        }
    }
}

