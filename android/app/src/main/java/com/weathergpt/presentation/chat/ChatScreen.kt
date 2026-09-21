package com.weathergpt.presentation.chat

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.ui.text.input.ImeAction
import android.widget.Toast
import com.weathergpt.core.config.AppConfig
import com.weathergpt.domain.brain.OfflineDemoIntelligenceEngine
import com.weathergpt.domain.model.chat.DomainBrain
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.automirrored.filled.VolumeUp
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.weathergpt.R
import com.weathergpt.presentation.components.MarkdownText
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.chat.ChatLanguage
import com.weathergpt.domain.model.chat.ChatResponse
import com.weathergpt.presentation.components.EmptyState
import com.weathergpt.presentation.components.NirnayCardComposable
import com.weathergpt.presentation.components.getSeverityColor
import java.util.Locale

@Composable
fun ChatScreen(
    viewModel: ChatViewModel,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val chatState by viewModel.chatState.collectAsStateWithLifecycle()
    val listState = rememberLazyListState()
    val context = LocalContext.current
    val activity = context as? Activity

    var hasMicPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.RECORD_AUDIO
            ) == PackageManager.PERMISSION_GRANTED
        )
    }

    var showPermissionRationaleDialog by remember { mutableStateOf(false) }
    var isPermanentlyDenied by remember { mutableStateOf(false) }
    var recordingDurationSeconds by remember { mutableStateOf(0) }

    LaunchedEffect(uiState.voiceState) {
        if (uiState.voiceState == VoiceState.RECORDING) {
            val startTime = System.currentTimeMillis()
            while (true) {
                recordingDurationSeconds = ((System.currentTimeMillis() - startTime) / 1000).toInt()
                kotlinx.coroutines.delay(500)
            }
        } else {
            recordingDurationSeconds = 0
        }
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission(),
        onResult = { granted ->
            hasMicPermission = granted
            if (granted) {
                viewModel.startVoiceRecording()
            } else {
                val showRationale = activity?.let {
                    ActivityCompat.shouldShowRequestPermissionRationale(it, Manifest.permission.RECORD_AUDIO)
                } ?: false
                isPermanentlyDenied = !showRationale
                showPermissionRationaleDialog = true
            }
        }
    )

    if (showPermissionRationaleDialog) {
        AlertDialog(
            onDismissRequest = { showPermissionRationaleDialog = false },
            title = {
                Text(
                    text = "Microphone Permission Required",
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp
                )
            },
            text = {
                Text(
                    text = if (isPermanentlyDenied) {
                        "Microphone permission is needed to record voice queries with Vayubodhak. Please enable it in App Settings."
                    } else {
                        "Microphone permission is required for voice input so Vayubodhak can hear and transcribe your weather questions."
                    },
                    fontSize = 14.sp
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        showPermissionRationaleDialog = false
                        if (isPermanentlyDenied) {
                            val intent = Intent(
                                Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                                Uri.fromParts("package", context.packageName, null)
                            )
                            context.startActivity(intent)
                        } else {
                            permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                        }
                    }
                ) {
                    Text(
                        text = if (isPermanentlyDenied) "Open Settings" else "Grant Permission",
                        color = Color(0xFF1B5E20),
                        fontWeight = FontWeight.Bold
                    )
                }
            },
            dismissButton = {
                TextButton(onClick = { showPermissionRationaleDialog = false }) {
                    Text("Cancel", color = Color(0xFF64748B))
                }
            }
        )
    }

    LaunchedEffect(uiState.messages.size) {
        if (uiState.messages.isNotEmpty()) {
            listState.animateScrollToItem(uiState.messages.size - 1)
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFFF8FAF8))
            .padding(horizontal = 16.dp, vertical = 8.dp)
    ) {
        // Offline Demo Mode Banner
        if (AppConfig.isDemoMode) {
            Surface(
                shape = RoundedCornerShape(10.dp),
                color = Color(0xFFF1F8E9),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0xFFA5D6A7), RoundedCornerShape(10.dp))
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(8.dp)
                                    .clip(CircleShape)
                                    .background(Color(0xFF2E7D32))
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "LOCAL INTELLIGENCE",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF1B5E20)
                            )
                        }
                        Text(
                            text = "Deterministic On-Device Assistant • Verified Cache (Gwalior)",
                            fontSize = 10.sp,
                            color = Color(0xFF33691E)
                        )
                    }
                    Text(
                        text = "Source: Open-Meteo",
                        fontSize = 10.sp,
                        color = Color(0xFF558B2F)
                    )
                }
            }
            Spacer(modifier = Modifier.height(6.dp))
        }

        // Active Brain & Language Selection Strip
        Surface(
            shape = RoundedCornerShape(14.dp),
            color = Color.White,
            shadowElevation = 1.dp,
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(14.dp))
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .clip(CircleShape)
                            .background(Color(0xFF2E7D32))
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = stringResource(R.string.chat_brain_label, uiState.selectedBrain.value.uppercase()),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF1B5E20)
                    )
                }

                // Language quick toggle
                Row(verticalAlignment = Alignment.CenterVertically) {
                    listOf(
                        ChatLanguage.HINDI to "हिन्दी",
                        ChatLanguage.ENGLISH to "EN"
                    ).forEach { (lang, label) ->
                        val isSelected = uiState.language == lang
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(8.dp))
                                .background(if (isSelected) Color(0xFFE8F5E9) else Color.Transparent)
                                .clickable { viewModel.setLanguage(lang) }
                                .padding(horizontal = 8.dp, vertical = 4.dp)
                        ) {
                            Text(
                                text = label,
                                fontSize = 11.sp,
                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                color = if (isSelected) Color(0xFF1B5E20) else Color(0xFF64748B)
                            )
                        }
                        Spacer(modifier = Modifier.width(4.dp))
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Independent LLM Resilience Notice (Section 10 & 18)
        val resilienceManager = androidx.compose.runtime.remember { com.weathergpt.core.resilience.SystemResilienceManager.getInstance() }
        val resilienceState by resilienceManager.uiState.collectAsStateWithLifecycle()
        if (resilienceState.llmStatus == com.weathergpt.domain.model.resilience.LlmStatus.LLM_UNAVAILABLE) {
            Surface(
                shape = RoundedCornerShape(10.dp),
                color = Color(0xFFFFFBEB),
                border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFFDE68A)),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 6.dp)
            ) {
                Row(modifier = Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(text = "ℹ️", fontSize = 14.sp)
                    Spacer(modifier = Modifier.width(8.dp))
                    Column {
                        Text(
                            text = "AI Assistant Explanation Unavailable",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFB45309)
                        )
                        Text(
                            text = "Deterministic disaster assessment and agricultural calculations remain 100% available.",
                            fontSize = 10.sp,
                            color = Color(0xFF78350F)
                        )
                    }
                }
            }
        }

        // Messages List
        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
        ) {
            if (uiState.messages.isEmpty()) {
                if (AppConfig.isDemoMode) {
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .verticalScroll(rememberScrollState()),
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        EmptyState(
                            title = "Local Intelligence Assistant",
                            message = "Vayubodhak is running offline with verified local intelligence. Tap any suggested query below or type your query.",
                            icon = Icons.Default.Info
                        )
                        DemoQuestionsSection(
                            onQuestionSelected = { brain, q ->
                                viewModel.selectBrain(brain)
                                viewModel.sendMessage(q)
                            },
                            defaultExpanded = true
                        )
                    }
                } else {
                    EmptyState(
                        title = stringResource(R.string.chat_empty_title),
                        message = stringResource(R.string.chat_empty_message),
                        icon = Icons.Default.Info
                    )
                }
            } else {
                LazyColumn(
                    state = listState,
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    modifier = Modifier.fillMaxSize()
                ) {
                    items(uiState.messages) { message ->
                        when (message) {
                            is ChatMessage.User -> {
                                UserMessageBubble(text = message.text)
                            }
                            is ChatMessage.Assistant -> {
                                AssistantMessageCard(
                                    response = message.response,
                                    messageId = message.id,
                                    nirnayCard = message.nirnayCard,
                                    isPlayingThis = uiState.isPlayingAudio && uiState.activeAudioMessageId == message.id,
                                    isLoadingThis = !uiState.isPlayingAudio && uiState.activeAudioMessageId == message.id && uiState.voiceState == VoiceState.THINKING,
                                    onPlayVoice = {
                                        val speechText = message.response.summary.ifBlank { message.response.answer }
                                        viewModel.playAssistantAudio(message.id, speechText)
                                    }
                                )
                            }
                        }
                    }

                    if (uiState.isSending) {
                        item {
                            AssistantLoadingBubble()
                        }
                    }
                }
            }
        }

        if (chatState is ResultState.Error && !uiState.isSending) {
            val error = (chatState as ResultState.Error).error
            Surface(
                shape = RoundedCornerShape(10.dp),
                color = Color(0xFFFEF2F2),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color(0xFFFCA5A5), RoundedCornerShape(10.dp))
                    .padding(vertical = 4.dp)
            ) {
                Row(
                    modifier = Modifier.padding(10.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = error.message,
                        fontSize = 12.sp,
                        color = Color(0xFFDC2626),
                        modifier = Modifier.weight(1f)
                    )
                    if (error.isRetryable) {
                        TextButton(onClick = { viewModel.retryLast() }) {
                            Text(stringResource(R.string.btn_retry), color = Color(0xFFDC2626), fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }

        // Voice Status Bar Indicator
        AnimatedVisibility(visible = uiState.voiceState != VoiceState.IDLE) {
            VoiceStatusBar(
                voiceState = uiState.voiceState,
                errorMessage = uiState.voiceErrorMessage,
                recordingDurationSeconds = recordingDurationSeconds,
                onStopRecording = { viewModel.stopVoiceRecordingAndSend() },
                onCancelRecording = { viewModel.cancelVoiceRecording() },
                onStopPlaying = { viewModel.stopAudioPlayback() },
                onDismissError = { viewModel.clearVoiceError() }
            )
        }

        // Demo Questions Bank or Quick Decision Prompt Suggestion Chip
        if (AppConfig.isDemoMode) {
            DemoQuestionsSection(
                onQuestionSelected = { brain, q ->
                    viewModel.selectBrain(brain)
                    viewModel.sendMessage(q)
                },
                modifier = Modifier.padding(vertical = 4.dp),
                defaultExpanded = false
            )
        } else {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 4.dp),
                horizontalArrangement = Arrangement.Start
            ) {
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = Color(0xFFE8F5E9),
                    modifier = Modifier
                        .border(1.dp, Color(0xFFA5D6A7), RoundedCornerShape(16.dp))
                        .clickable(enabled = !uiState.isSending) {
                            viewModel.sendMessage("Should I spray my cotton tonight?")
                        }
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(text = "⚡", fontSize = 12.sp)
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "Should I spray my cotton tonight?",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = Color(0xFF1B5E20)
                        )
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(4.dp))

        // Clean Text & Voice Query Input Row
        val isRecording = uiState.voiceState == VoiceState.RECORDING
        val isSpeaking = uiState.voiceState == VoiceState.SPEAKING
        val isBusy = uiState.voiceState in listOf(
            VoiceState.UPLOADING,
            VoiceState.TRANSCRIBING,
            VoiceState.THINKING
        )
        val canSend = uiState.inputText.isNotBlank() && !uiState.isSending && !isRecording && !isBusy

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color.White, RoundedCornerShape(24.dp))
                .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(24.dp))
                .padding(horizontal = 6.dp, vertical = 2.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = uiState.inputText,
                onValueChange = { viewModel.setInputText(it) },
                enabled = !isRecording && !uiState.isSending && !isBusy,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(
                    onSend = {
                        if (canSend) {
                            viewModel.sendMessage()
                        }
                    }
                ),
                placeholder = {
                    if (uiState.voiceState == VoiceState.RECORDING) {
                        val durationFormatted = String.format(
                            Locale.getDefault(),
                            "%02d:%02d",
                            recordingDurationSeconds / 60,
                            recordingDurationSeconds % 60
                        )
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(8.dp)
                                    .clip(CircleShape)
                                    .background(Color(0xFFDC2626))
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "Recording ($durationFormatted) • Tap stop when done",
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Medium,
                                color = Color(0xFFDC2626)
                            )
                        }
                    } else {
                        Text(
                            text = stringResource(R.string.chat_input_placeholder),
                            fontSize = 13.sp,
                            color = Color(0xFF94A3B8)
                        )
                    }
                },
                singleLine = true,
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Color.Transparent,
                    unfocusedBorderColor = Color.Transparent,
                    disabledBorderColor = Color.Transparent,
                    focusedContainerColor = Color.Transparent,
                    unfocusedContainerColor = Color.Transparent,
                    disabledContainerColor = Color.Transparent
                ),
                modifier = Modifier.weight(1f)
            )

            Spacer(modifier = Modifier.width(2.dp))

            // Microphone Voice Button (Accessible 48dp touch target)
            val infiniteTransition = rememberInfiniteTransition(label = "pulse")
            val pulseScale by infiniteTransition.animateFloat(
                initialValue = 1f,
                targetValue = if (isRecording) 1.2f else 1f,
                animationSpec = infiniteRepeatable(
                    animation = tween(600),
                    repeatMode = RepeatMode.Reverse
                ),
                label = "micPulse"
            )

            val onMicClick: () -> Unit = {
                if (AppConfig.isDemoMode) {
                    Toast.makeText(
                        context,
                        "Voice recording requires online streaming. Please tap any suggested query or type above.",
                        Toast.LENGTH_SHORT
                    ).show()
                } else {
                    when (uiState.voiceState) {
                        VoiceState.RECORDING -> {
                            viewModel.stopVoiceRecordingAndSend()
                        }
                        VoiceState.SPEAKING -> {
                            viewModel.stopAudioPlayback()
                        }
                        VoiceState.UPLOADING, VoiceState.TRANSCRIBING, VoiceState.THINKING -> {
                            // In flight; prevent duplicate click
                        }
                        VoiceState.IDLE, VoiceState.ERROR -> {
                            val hasPermission = ContextCompat.checkSelfPermission(
                                context,
                                Manifest.permission.RECORD_AUDIO
                            ) == PackageManager.PERMISSION_GRANTED
                            hasMicPermission = hasPermission

                            if (hasPermission) {
                                viewModel.startVoiceRecording()
                            } else {
                                permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                            }
                        }
                    }
                }
            }

            Box(
                modifier = Modifier
                    .size(48.dp)
                    .clickable(
                        enabled = !isBusy,
                        onClick = onMicClick
                    ),
                contentAlignment = Alignment.Center
            ) {
                Box(
                    modifier = Modifier
                        .size(38.dp)
                        .scale(if (isRecording) pulseScale else 1f)
                        .clip(CircleShape)
                        .background(
                            when {
                                isRecording -> Color(0xFFDC2626)
                                isSpeaking -> Color(0xFF2563EB)
                                uiState.voiceState == VoiceState.ERROR -> Color(0xFFFEF2F2)
                                isBusy -> Color(0xFFF1F5F9)
                                else -> Color(0xFFF1F5F9)
                            }
                        )
                        .border(
                            width = 1.dp,
                            color = when {
                                isRecording -> Color(0xFFB91C1C)
                                isSpeaking -> Color(0xFF1D4ED8)
                                uiState.voiceState == VoiceState.ERROR -> Color(0xFFFCA5A5)
                                else -> Color(0xFFE2E8F0)
                            },
                            shape = CircleShape
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    when {
                        isRecording -> {
                            Icon(
                                imageVector = Icons.Default.Stop,
                                contentDescription = "Stop recording",
                                tint = Color.White,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                        isSpeaking -> {
                            Icon(
                                imageVector = Icons.Default.Stop,
                                contentDescription = "Stop speaking",
                                tint = Color.White,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                        isBusy -> {
                            CircularProgressIndicator(
                                modifier = Modifier.size(18.dp),
                                strokeWidth = 2.dp,
                                color = Color(0xFF1B5E20)
                            )
                        }
                        uiState.voiceState == VoiceState.ERROR -> {
                            Icon(
                                imageVector = Icons.Default.Mic,
                                contentDescription = "Voice input",
                                tint = Color(0xFFDC2626),
                                modifier = Modifier.size(20.dp)
                            )
                        }
                        else -> {
                            Icon(
                                imageVector = Icons.Default.Mic,
                                contentDescription = "Voice input",
                                tint = Color(0xFF1B5E20),
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.width(2.dp))

            // Send circular green button (Accessible 48dp touch target)
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .clickable(
                        enabled = canSend,
                        onClick = { viewModel.sendMessage() }
                    ),
                contentAlignment = Alignment.Center
            ) {
                Box(
                    modifier = Modifier
                        .size(38.dp)
                        .clip(CircleShape)
                        .background(if (canSend) Color(0xFF1B5E20) else Color(0xFFCBD5E1)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.Send,
                        contentDescription = stringResource(R.string.cd_send),
                        tint = Color.White,
                        modifier = Modifier.size(18.dp)
                    )
                }
            }
        }
    }
}

@Composable
private fun VoiceStatusBar(
    voiceState: VoiceState,
    errorMessage: String?,
    recordingDurationSeconds: Int = 0,
    onStopRecording: () -> Unit,
    onCancelRecording: () -> Unit,
    onStopPlaying: () -> Unit,
    onDismissError: () -> Unit = {}
) {
    Surface(
        shape = RoundedCornerShape(12.dp),
        color = when (voiceState) {
            VoiceState.RECORDING -> Color(0xFFFEF2F2)
            VoiceState.UPLOADING, VoiceState.TRANSCRIBING, VoiceState.THINKING -> Color(0xFFF0FDF4)
            VoiceState.SPEAKING -> Color(0xFFEFF6FF)
            VoiceState.ERROR -> Color(0xFFFEF2F2)
            else -> Color.White
        },
        modifier = Modifier
            .fillMaxWidth()
            .border(
                1.dp,
                when (voiceState) {
                    VoiceState.RECORDING -> Color(0xFFFCA5A5)
                    VoiceState.SPEAKING -> Color(0xFFBFDBFE)
                    VoiceState.ERROR -> Color(0xFFFCA5A5)
                    else -> Color(0xFFBBF7D0)
                },
                RoundedCornerShape(12.dp)
            )
            .padding(vertical = 2.dp)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
                when (voiceState) {
                    VoiceState.RECORDING -> {
                        val durationFormatted = String.format(
                            Locale.getDefault(),
                            "%02d:%02d",
                            recordingDurationSeconds / 60,
                            recordingDurationSeconds % 60
                        )
                        Box(
                            modifier = Modifier
                                .size(10.dp)
                                .clip(CircleShape)
                                .background(Color(0xFFDC2626))
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Listening ($durationFormatted)... Tap mic or Done when finished",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium,
                            color = Color(0xFFB91C1C)
                        )
                    }
                    VoiceState.UPLOADING, VoiceState.TRANSCRIBING -> {
                        CircularProgressIndicator(
                            modifier = Modifier.size(14.dp),
                            strokeWidth = 2.dp,
                            color = Color(0xFF1B5E20)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Transcribing speech (Google STT V2)...",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium,
                            color = Color(0xFF15803D)
                        )
                    }
                    VoiceState.THINKING -> {
                        CircularProgressIndicator(
                            modifier = Modifier.size(14.dp),
                            strokeWidth = 2.dp,
                            color = Color(0xFF1B5E20)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Processing weather analysis...",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium,
                            color = Color(0xFF15803D)
                        )
                    }
                    VoiceState.SPEAKING -> {
                        Text(text = "🔊", fontSize = 13.sp)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Speaking response (Google TTS)...",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium,
                            color = Color(0xFF1D4ED8)
                        )
                    }
                    VoiceState.ERROR -> {
                        Text(text = "⚠️", fontSize = 13.sp)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = errorMessage ?: "Voice processing error",
                            fontSize = 12.sp,
                            color = Color(0xFFDC2626)
                        )
                    }
                    else -> {}
                }
            }

            // Quick actions
            when (voiceState) {
                VoiceState.RECORDING -> {
                    Row {
                        TextButton(onClick = onStopRecording) {
                            Text("Done", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color(0xFFDC2626))
                        }
                        TextButton(onClick = onCancelRecording) {
                            Text("Cancel", fontSize = 12.sp, color = Color(0xFF64748B))
                        }
                    }
                }
                VoiceState.SPEAKING -> {
                    TextButton(onClick = onStopPlaying) {
                        Text("Stop", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color(0xFF1D4ED8))
                    }
                }
                VoiceState.ERROR -> {
                    TextButton(onClick = onDismissError) {
                        Text("Dismiss", fontSize = 12.sp, color = Color(0xFFDC2626))
                    }
                }
                else -> {}
            }
        }
    }
}

@Composable
private fun UserMessageBubble(
    text: String,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.End
    ) {
        Card(
            shape = RoundedCornerShape(topStart = 16.dp, topEnd = 4.dp, bottomStart = 16.dp, bottomEnd = 16.dp),
            colors = CardDefaults.cardColors(
                containerColor = Color(0xFF1B5E20),
                contentColor = Color.White
            ),
            modifier = Modifier.fillMaxWidth(0.85f)
        ) {
            Text(
                text = text,
                fontSize = 14.sp,
                modifier = Modifier.padding(12.dp),
                lineHeight = 18.sp
            )
        }
    }
}

@Composable
private fun AssistantMessageCard(
    response: ChatResponse,
    messageId: String,
    nirnayCard: com.weathergpt.domain.model.decision.NirnayCard? = null,
    isPlayingThis: Boolean = false,
    isLoadingThis: Boolean = false,
    onPlayVoice: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    Card(
        shape = RoundedCornerShape(topStart = 4.dp, topEnd = 16.dp, bottomStart = 16.dp, bottomEnd = 16.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.5.dp),
        modifier = modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(topStart = 4.dp, topEnd = 16.dp, bottomStart = 16.dp, bottomEnd = 16.dp))
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            // Brain badge + Speaker Action
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = "🌿", fontSize = 14.sp)
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = stringResource(R.string.app_tagline),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF1B5E20)
                    )
                }

                IconButton(
                    onClick = onPlayVoice,
                    modifier = Modifier.size(36.dp)
                ) {
                    if (isLoadingThis) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(16.dp),
                            strokeWidth = 2.dp,
                            color = Color(0xFF2E7D32)
                        )
                    } else {
                        Icon(
                            imageVector = if (isPlayingThis) Icons.Default.Stop else Icons.AutoMirrored.Filled.VolumeUp,
                            contentDescription = if (isPlayingThis) "Stop speaking" else "Read aloud",
                            tint = if (isPlayingThis) Color(0xFFDC2626) else Color(0xFF2E7D32),
                            modifier = Modifier.size(18.dp)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(6.dp))

            // Main Text Answer (with native Markdown rendering)
            MarkdownText(
                markdown = response.answer,
                fontSize = 14.sp,
                color = Color(0xFF0F172A),
                lineHeight = 20.sp
            )

            // Vayubodhak Nirnay Card (USP Phase 2 Action Window & Decision)
            if (nirnayCard != null) {
                Spacer(modifier = Modifier.height(10.dp))
                NirnayCardComposable(card = nirnayCard)
            }

            // Recommendation Card (only rendered when meaningful actionable content exists)
            val rec = response.recommendation
            val invalidRecTokens = setOf("{}", "[]", "null", "undefined", ":", "-", "•", "", "none")
            val rawPrimary = rec?.primaryAction?.trim() ?: ""
            val validPrimary = if (rawPrimary.isNotBlank() && !invalidRecTokens.contains(rawPrimary.lowercase())) rawPrimary else null
            val validActions = rec?.actions?.map { it.trim() }?.filter {
                it.isNotBlank() && !invalidRecTokens.contains(it.lowercase()) && it != validPrimary
            } ?: emptyList()

            if (rec != null && (validPrimary != null || validActions.isNotEmpty())) {
                Spacer(modifier = Modifier.height(10.dp))
                Card(
                    shape = RoundedCornerShape(10.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFF0FDF4)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(10.dp)) {
                        if (validPrimary != null) {
                            Text(
                                text = validPrimary,
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF166534)
                            )
                        }
                        if (validActions.isNotEmpty()) {
                            if (validPrimary != null) {
                                Spacer(modifier = Modifier.height(4.dp))
                            }
                            validActions.forEach { action ->
                                Text(
                                    text = "• $action",
                                    fontSize = 12.sp,
                                    color = Color(0xFF15803D)
                                )
                            }
                        }
                    }
                }
            }

            // Severe Alert Warning Card (if present)
            if (response.alert != null) {
                Spacer(modifier = Modifier.height(10.dp))
                val severityColor = getSeverityColor(response.alert.level)
                Card(
                    shape = RoundedCornerShape(10.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFFEF2F2)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(10.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier
                                .size(10.dp)
                                .clip(CircleShape)
                                .background(severityColor)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Column {
                            Text(
                                text = " ALERT: ",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = severityColor
                            )
                            Text(
                                text = response.alert.description,
                                fontSize = 11.sp,
                                color = Color(0xFF991B1B)
                            )
                        }
                    }
                }
            }

            // Evidence & Sources (Clean, formatted list; never displays empty/invalid tokens)
            val invalidTokens = setOf("()", "[]", "null", "undefined", "(null)", "(undefined)", "none", "n/a")
            val validSources = response.sources.flatMap { source ->
                val auth = source.authority.trim()
                val dataset = source.dataset.trim()
                val list = mutableListOf<String>()
                if (auth.isNotBlank() && !invalidTokens.contains(auth.lowercase())) {
                    list.add(auth)
                }
                if (dataset.isNotBlank() && !invalidTokens.contains(dataset.lowercase()) && dataset != auth) {
                    list.add(dataset)
                }
                list
            }.filter { it.isNotBlank() }.distinct()

            if (validSources.isNotEmpty()) {
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = stringResource(R.string.sources_label),
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFF64748B)
                )
                Spacer(modifier = Modifier.height(2.dp))
                validSources.forEach { src ->
                    Row(
                        modifier = Modifier.padding(vertical = 1.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "•",
                            fontSize = 10.sp,
                            color = Color(0xFF64748B),
                            modifier = Modifier.padding(end = 4.dp)
                        )
                        Text(
                            text = src,
                            fontSize = 10.sp,
                            color = Color(0xFF64748B)
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun AssistantLoadingBubble() {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.Start
    ) {
        Surface(
            shape = RoundedCornerShape(12.dp),
            color = Color.White,
            modifier = Modifier
                .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(12.dp))
                .padding(4.dp)
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                CircularProgressIndicator(
                    modifier = Modifier.size(16.dp),
                    strokeWidth = 2.dp,
                    color = Color(0xFF1B5E20)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = stringResource(R.string.chat_analyzing_message),
                    fontSize = 12.sp,
                    color = Color(0xFF475569)
                )
            }
        }
    }
}

@Composable
fun DemoQuestionsSection(
    onQuestionSelected: (DomainBrain, String) -> Unit,
    modifier: Modifier = Modifier,
    defaultExpanded: Boolean = false
) {
    var selectedBrainTab by remember { mutableStateOf(DomainBrain.GENERAL) }
    var isExpanded by remember { mutableStateOf(defaultExpanded) }

    val brainTabs = listOf(
        DomainBrain.GENERAL to "🌐 General",
        DomainBrain.FARMER to "🌾 Farmer",
        DomainBrain.RESEARCHER to "🔬 Researcher",
        DomainBrain.ANALYST to "🛡️ Analyst"
    )

    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFF1F8E9)),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFFC5E1A5), RoundedCornerShape(14.dp))
    ) {
        Column(modifier = Modifier.padding(10.dp)) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { isExpanded = !isExpanded },
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = "💡", fontSize = 14.sp)
                    Spacer(modifier = Modifier.width(8.dp))
                    Column {
                        Text(
                            text = "SUGGESTED QUERIES",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF1B5E20)
                        )
                        Text(
                            text = "Domain Inquiry Bank • 4 Brains",
                            fontSize = 10.sp,
                            color = Color(0xFF558B2F)
                        )
                    }
                }
                Text(
                    text = if (isExpanded) "Hide ▲" else "Show (20) ▼",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF2E7D32)
                )
            }

            if (isExpanded) {
                Spacer(modifier = Modifier.height(8.dp))

                // Brain selector tabs
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    brainTabs.forEach { (brain, label) ->
                        val isSelected = selectedBrainTab == brain
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(8.dp))
                                .background(if (isSelected) Color(0xFF2E7D32) else Color.White)
                                .border(
                                    1.dp,
                                    if (isSelected) Color(0xFF1B5E20) else Color(0xFFA5D6A7),
                                    RoundedCornerShape(8.dp)
                                )
                                .clickable { selectedBrainTab = brain }
                                .padding(vertical = 6.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = label,
                                fontSize = 10.sp,
                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                                color = if (isSelected) Color.White else Color(0xFF1B5E20)
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                // Questions for selected brain
                val questions = OfflineDemoIntelligenceEngine.DEMO_QUESTION_BANK.filter { it.brain == selectedBrainTab }
                Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                    questions.forEachIndexed { index, item ->
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = Color.White,
                            modifier = Modifier
                                .fillMaxWidth()
                                .border(1.dp, Color(0xFFDCEDC8), RoundedCornerShape(8.dp))
                                .clickable {
                                    onQuestionSelected(item.brain, item.question)
                                }
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(horizontal = 8.dp, vertical = 6.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "${index + 1}.",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF2E7D32)
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(
                                    text = item.question,
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Medium,
                                    color = Color(0xFF1F2937),
                                    modifier = Modifier.weight(1f)
                                )
                                Text(
                                    text = "⚡",
                                    fontSize = 11.sp
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
