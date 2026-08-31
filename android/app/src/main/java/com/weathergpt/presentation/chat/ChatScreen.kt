package com.weathergpt.presentation.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.weathergpt.R
import com.weathergpt.core.result.ResultState
import com.weathergpt.domain.model.chat.ChatLanguage
import com.weathergpt.domain.model.chat.ChatResponse
import com.weathergpt.presentation.components.EmptyState
import com.weathergpt.presentation.components.getSeverityColor

@Composable
fun ChatScreen(
    viewModel: ChatViewModel,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val chatState by viewModel.chatState.collectAsStateWithLifecycle()
    val listState = rememberLazyListState()

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
                        text = "Brain: ${uiState.selectedBrain.value.uppercase()}",
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

        // Messages List
        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
        ) {
            if (uiState.messages.isEmpty()) {
                EmptyState(
                    title = stringResource(R.string.chat_empty_title),
                    message = stringResource(R.string.chat_empty_message),
                    icon = Icons.Default.Info
                )
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
                                AssistantMessageCard(response = message.response)
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

        Spacer(modifier = Modifier.height(8.dp))

        // Clean Text Query Input Row with Green Send Action Button (Seamless & Intentional Layout)
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color.White, RoundedCornerShape(24.dp))
                .border(1.dp, Color(0xFFE2E8F0), RoundedCornerShape(24.dp))
                .padding(horizontal = 12.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = uiState.inputText,
                onValueChange = { viewModel.setInputText(it) },
                placeholder = {
                    Text(
                        text = stringResource(R.string.chat_input_placeholder),
                        fontSize = 13.sp,
                        color = Color(0xFF94A3B8)
                    )
                },
                singleLine = true,
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Color.Transparent,
                    unfocusedBorderColor = Color.Transparent,
                    focusedContainerColor = Color.Transparent,
                    unfocusedContainerColor = Color.Transparent
                ),
                modifier = Modifier.weight(1f)
            )

            Spacer(modifier = Modifier.width(6.dp))

            // Send circular green button
            Box(
                modifier = Modifier
                    .size(38.dp)
                    .clip(CircleShape)
                    .background(if (uiState.inputText.isNotBlank() && !uiState.isSending) Color(0xFF1B5E20) else Color(0xFFCBD5E1))
                    .clickable(enabled = uiState.inputText.isNotBlank() && !uiState.isSending) {
                        viewModel.sendMessage()
                    },
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.Send,
                    contentDescription = "Send",
                    tint = Color.White,
                    modifier = Modifier.size(18.dp)
                )
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
            // Brain badge
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(text = "🌿", fontSize = 14.sp)
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = "Vayubodhak (${response.brain.value.uppercase()})",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF1B5E20)
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Main Text Answer
            Text(
                text = response.answer,
                fontSize = 14.sp,
                color = Color(0xFF0F172A),
                lineHeight = 20.sp
            )

            // Recommendation Card (if present)
            if (response.recommendation != null) {
                Spacer(modifier = Modifier.height(10.dp))
                Card(
                    shape = RoundedCornerShape(10.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFF0FDF4)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(10.dp)) {
                        Text(
                            text = "${stringResource(R.string.recommendation_label)}: ${response.recommendation.primaryAction}",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF166534)
                        )
                        if (response.recommendation.actions.isNotEmpty()) {
                            Spacer(modifier = Modifier.height(4.dp))
                            response.recommendation.actions.forEach { action ->
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
                                text = "${response.alert.level.uppercase()} ALERT: ${response.alert.hazardType}",
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

            // Evidence & Sources
            if (response.sources.isNotEmpty()) {
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = stringResource(R.string.sources_label) + ": " + response.sources.joinToString(", ") { "${it.authority} (${it.dataset})" },
                    fontSize = 10.sp,
                    color = Color(0xFF64748B)
                )
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
