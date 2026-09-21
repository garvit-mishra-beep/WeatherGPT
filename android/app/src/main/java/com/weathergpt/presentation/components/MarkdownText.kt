package com.weathergpt.presentation.components

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

sealed class MarkdownBlock {
    data class Header(val level: Int, val text: String) : MarkdownBlock()
    data class BulletItem(val text: String) : MarkdownBlock()
    data class NumberedItem(val number: String, val text: String) : MarkdownBlock()
    data class Paragraph(val text: String) : MarkdownBlock()
}

/**
 * Parses inline markdown tokens (bold: ** or __, italic: * or _, code: `)
 * into an AnnotatedString without displaying raw markdown formatting markers.
 */
fun parseInlineMarkdown(text: String, defaultColor: Color = Color(0xFF0F172A)): AnnotatedString {
    return buildAnnotatedString {
        // Regex matches:
        // 1) **bold** or __bold__
        // 2) `code`
        // 3) *italic* or _italic_
        val regex = Regex("""(\*\*|__)(.*?)\1|(`)(.*?)\3|(\*|_)(.*?)\5""")
        var currentIndex = 0

        for (match in regex.findAll(text)) {
            val start = match.range.first
            val end = match.range.last + 1

            // Append prefix text before the match
            if (start > currentIndex) {
                append(text.substring(currentIndex, start))
            }

            val fullMatch = match.value
            when {
                // Bold: **text** or __text__
                (fullMatch.startsWith("**") && fullMatch.endsWith("**") && fullMatch.length >= 4) -> {
                    val inner = fullMatch.substring(2, fullMatch.length - 2)
                    withStyle(SpanStyle(fontWeight = FontWeight.Bold, color = defaultColor)) {
                        append(inner)
                    }
                }
                (fullMatch.startsWith("__") && fullMatch.endsWith("__") && fullMatch.length >= 4) -> {
                    val inner = fullMatch.substring(2, fullMatch.length - 2)
                    withStyle(SpanStyle(fontWeight = FontWeight.Bold, color = defaultColor)) {
                        append(inner)
                    }
                }
                // Inline Code: `code`
                (fullMatch.startsWith("`") && fullMatch.endsWith("`") && fullMatch.length >= 2) -> {
                    val inner = fullMatch.substring(1, fullMatch.length - 1)
                    withStyle(SpanStyle(fontFamily = FontFamily.Monospace, color = defaultColor)) {
                        append(inner)
                    }
                }
                // Italic: *text* or _text_
                ((fullMatch.startsWith("*") && fullMatch.endsWith("*") && fullMatch.length >= 2) ||
                 (fullMatch.startsWith("_") && fullMatch.endsWith("_") && fullMatch.length >= 2)) -> {
                    val inner = fullMatch.substring(1, fullMatch.length - 1)
                    withStyle(SpanStyle(fontStyle = FontStyle.Italic, color = defaultColor)) {
                        append(inner)
                    }
                }
                else -> {
                    append(fullMatch)
                }
            }
            currentIndex = end
        }

        if (currentIndex < text.length) {
            append(text.substring(currentIndex))
        }
    }
}

/**
 * Normalizes raw LaTeX and technical formulas (e.g. $\text{ET}_0$ -> ET₀) into plain readable text.
 */
fun normalizeLatex(text: String): String {
    var result = text
    result = result.replace(Regex("""[$]\s*\\text\{ET\}[_0-9oO]*\s*[$]|[$]ET[_0-9oO]*[$]|\\text\{ET[_0-9oO]*\}""", RegexOption.IGNORE_CASE), "ET₀")
    result = result.replace(Regex("""[$]\s*\\text\{([^}]+)\}\s*[$]""")) { it.groupValues[1] }
    result = result.replace(Regex("""\\text\{([^}]+)\}""")) { it.groupValues[1] }
    result = result.replace(Regex("""[$]\s*km/h\s*[$]"""), "km/h")
    result = result.replace(Regex("""[$]\s*mm\s*[$]"""), "mm")
    result = result.replace(Regex("""[$]\s*°C\s*[$]"""), "°C")
    result = result.replace(Regex("""[$]\s*([0-9.\-]+)\s*[$]""")) { it.groupValues[1] }
    return result
}

/**
 * Parses multiline markdown content into block-level elements.
 */
fun parseMarkdownBlocks(markdown: String): List<MarkdownBlock> {
    val clean = normalizeLatex(markdown)
    val lines = clean.lines()
    val blocks = mutableListOf<MarkdownBlock>()
    val currentParagraph = StringBuilder()

    fun flushParagraph() {
        if (currentParagraph.isNotBlank()) {
            blocks.add(MarkdownBlock.Paragraph(currentParagraph.toString().trim()))
            currentParagraph.setLength(0)
        }
    }

    for (rawLine in lines) {
        val line = rawLine.trim()
        if (line.isEmpty()) {
            flushParagraph()
            continue
        }

        // Header: #, ##, ###, ####
        val headerMatch = Regex("""^(#{1,6})\s+(.*)$""").matchEntire(line)
        if (headerMatch != null) {
            flushParagraph()
            val level = headerMatch.groupValues[1].length
            val text = headerMatch.groupValues[2].trim()
            blocks.add(MarkdownBlock.Header(level, text))
            continue
        }

        // Bullet list item: *, -, +, •, followed by space
        val bulletMatch = Regex("""^(\*|-|\+|•)\s+(.*)$""").matchEntire(line)
        if (bulletMatch != null) {
            flushParagraph()
            val text = bulletMatch.groupValues[2].trim()
            blocks.add(MarkdownBlock.BulletItem(text))
            continue
        }

        // Numbered list item: 1. or 1)
        val numberedMatch = Regex("""^(\d+[\.\)])\s+(.*)$""").matchEntire(line)
        if (numberedMatch != null) {
            flushParagraph()
            val num = numberedMatch.groupValues[1]
            val text = numberedMatch.groupValues[2].trim()
            blocks.add(MarkdownBlock.NumberedItem(num, text))
            continue
        }

        // Accumulate multiline paragraph text
        if (currentParagraph.isNotEmpty()) {
            currentParagraph.append(" ")
        }
        currentParagraph.append(line)
    }

    flushParagraph()
    return blocks
}

/**
 * Native Jetpack Compose Markdown Renderer.
 * Renders bold, italic, code, headings, lists, and paragraphs cleanly with compact spacing.
 */
@Composable
fun MarkdownText(
    markdown: String,
    modifier: Modifier = Modifier,
    color: Color = Color(0xFF0F172A),
    fontSize: TextUnit = 14.sp,
    lineHeight: TextUnit = 20.sp
) {
    val blocks = remember(markdown) { parseMarkdownBlocks(markdown) }

    Column(modifier = modifier) {
        blocks.forEachIndexed { index, block ->
            when (block) {
                is MarkdownBlock.Header -> {
                    val headerSize = when (block.level) {
                        1 -> 16.sp
                        2 -> 15.sp
                        else -> 14.sp
                    }
                    if (index > 0) {
                        Spacer(modifier = Modifier.height(4.dp))
                    }
                    Text(
                        text = parseInlineMarkdown(block.text, color),
                        fontSize = headerSize,
                        fontWeight = FontWeight.Bold,
                        color = color,
                        lineHeight = lineHeight
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                }
                is MarkdownBlock.BulletItem -> {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 1.5.dp),
                        verticalAlignment = Alignment.Top
                    ) {
                        Text(
                            text = "•",
                            fontSize = fontSize,
                            color = Color(0xFF2E7D32),
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(end = 6.dp)
                        )
                        Text(
                            text = parseInlineMarkdown(block.text, color),
                            fontSize = fontSize,
                            color = color,
                            lineHeight = lineHeight,
                            modifier = Modifier.weight(1f)
                        )
                    }
                }
                is MarkdownBlock.NumberedItem -> {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 1.5.dp),
                        verticalAlignment = Alignment.Top
                    ) {
                        Text(
                            text = block.number,
                            fontSize = fontSize,
                            color = color,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.padding(end = 6.dp)
                        )
                        Text(
                            text = parseInlineMarkdown(block.text, color),
                            fontSize = fontSize,
                            color = color,
                            lineHeight = lineHeight,
                            modifier = Modifier.weight(1f)
                        )
                    }
                }
                is MarkdownBlock.Paragraph -> {
                    Text(
                        text = parseInlineMarkdown(block.text, color),
                        fontSize = fontSize,
                        color = color,
                        lineHeight = lineHeight,
                        modifier = Modifier.padding(vertical = 2.dp)
                    )
                }
            }
        }
    }
}
