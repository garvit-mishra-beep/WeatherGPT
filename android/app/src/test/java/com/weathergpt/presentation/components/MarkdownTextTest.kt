package com.weathergpt.presentation.components

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MarkdownTextTest {

    @Test
    fun testParseInlineMarkdown_boldRemovalAndSpan() {
        val input = "**Maximum Temperature:** 33.2 °C"
        val annotated = parseInlineMarkdown(input)

        // Raw ** must be stripped from the visible text
        assertEquals("Maximum Temperature: 33.2 °C", annotated.text)
        assertFalse(annotated.text.contains("**"))

        // Span styles must contain bold style for "Maximum Temperature:"
        val styles = annotated.spanStyles
        assertTrue(styles.isNotEmpty())
        assertEquals(0, styles[0].start)
        assertEquals(20, styles[0].end)
    }

    @Test
    fun testParseInlineMarkdown_italicAndCode() {
        val input = "Expect *light rain* and `calm winds`"
        val annotated = parseInlineMarkdown(input)

        assertEquals("Expect light rain and calm winds", annotated.text)
        assertFalse(annotated.text.contains("*"))
        assertFalse(annotated.text.contains("`"))
    }

    @Test
    fun testParseMarkdownBlocks_rawBulletListWithBold() {
        val input = """
            Forecast indicates:

            * **Maximum Temperature:** 33.2 °C
            * **Minimum Temperature:** 26.1 °C
            * **Rainfall Probability:** 75%
            * **Total Rainfall:** 24.5 mm
            * **Wind Speed:** 16.0 km/h

            Carry an umbrella.
        """.trimIndent()

        val blocks = parseMarkdownBlocks(input)

        assertEquals(7, blocks.size)
        assertTrue(blocks[0] is MarkdownBlock.Paragraph)
        assertEquals("Forecast indicates:", (blocks[0] as MarkdownBlock.Paragraph).text)

        assertTrue(blocks[1] is MarkdownBlock.BulletItem)
        assertEquals("**Maximum Temperature:** 33.2 °C", (blocks[1] as MarkdownBlock.BulletItem).text)

        assertTrue(blocks[2] is MarkdownBlock.BulletItem)
        assertEquals("**Minimum Temperature:** 26.1 °C", (blocks[2] as MarkdownBlock.BulletItem).text)

        assertTrue(blocks[3] is MarkdownBlock.BulletItem)
        assertEquals("**Rainfall Probability:** 75%", (blocks[3] as MarkdownBlock.BulletItem).text)

        assertTrue(blocks[4] is MarkdownBlock.BulletItem)
        assertEquals("**Total Rainfall:** 24.5 mm", (blocks[4] as MarkdownBlock.BulletItem).text)

        assertTrue(blocks[5] is MarkdownBlock.BulletItem)
        assertEquals("**Wind Speed:** 16.0 km/h", (blocks[5] as MarkdownBlock.BulletItem).text)

        assertTrue(blocks[6] is MarkdownBlock.Paragraph)
        assertEquals("Carry an umbrella.", (blocks[6] as MarkdownBlock.Paragraph).text)
    }

    @Test
    fun testParseMarkdownBlocks_headersAndNumberedLists() {
        val input = """
            # Weather Report
            1. First Step
            2. Second Step
        """.trimIndent()

        val blocks = parseMarkdownBlocks(input)
        assertEquals(3, blocks.size)

        assertTrue(blocks[0] is MarkdownBlock.Header)
        assertEquals(1, (blocks[0] as MarkdownBlock.Header).level)
        assertEquals("Weather Report", (blocks[0] as MarkdownBlock.Header).text)

        assertTrue(blocks[1] is MarkdownBlock.NumberedItem)
        assertEquals("1.", (blocks[1] as MarkdownBlock.NumberedItem).number)
        assertEquals("First Step", (blocks[1] as MarkdownBlock.NumberedItem).text)

        assertTrue(blocks[2] is MarkdownBlock.NumberedItem)
        assertEquals("2.", (blocks[2] as MarkdownBlock.NumberedItem).number)
        assertEquals("Second Step", (blocks[2] as MarkdownBlock.NumberedItem).text)
    }

    @Test
    fun testNormalizeLatex() {
        val input = "Crop water demand $\\text{ET}_0$ is 4.5 ${'$'}mm${'$'}, wind is 15 ${'$'}km/h${'$'}, temp is 32 ${'$'}°C${'$'}."
        val normalized = normalizeLatex(input)
        assertTrue(normalized.contains("ET₀"))
        assertTrue(normalized.contains("4.5 mm"))
        assertTrue(normalized.contains("15 km/h"))
        assertTrue(normalized.contains("32 °C"))
        assertFalse(normalized.contains("\\text{ET}"))
    }
}
