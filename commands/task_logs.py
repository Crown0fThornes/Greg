import asyncio
import logging
import tempfile
from pathlib import Path
import command_handler
from command_handler import Context

import discord
from LogReaderHelper.derby_ocr import extract_log


TASK_LOG_CHANNEL_ID = 1167152706230681670 

logger = logging.getLogger(__name__) 

@command_handler.Uncontested(type="MESSAGE")
async def read_derby_log(context: Context):
    # Only process human messages in the designated channel.
    message = context.message
    if message.author.bot:
        return

    if message.channel.id != TASK_LOG_CHANNEL_ID:
        return

    # Find supported image attachments.
    images = [
        attachment
        for attachment in message.attachments
        if Path(attachment.filename).suffix.lower()
        in {".png", ".jpg", ".jpeg", ".webp"}
    ]

    if not images:
        return

    if len(images) > 4:
        return

    try:
        # This directory is automatically deleted afterward.
        with tempfile.TemporaryDirectory() as directory:
            paths = []

            for index, attachment in enumerate(images):
                suffix = Path(attachment.filename).suffix.lower()
                path = Path(directory) / f"screenshot_{index}{suffix}"

                await attachment.save(path)
                paths.append(path)

            # OCR is synchronous, so run it outside Discord's event loop.
            async with message.channel.typing():
                result = await asyncio.to_thread(
                    extract_log,
                    paths,
                    expected_tasks=10,
                )

        # Turn the returned task dictionaries into readable lines.
        lines = []

        for number, task in enumerate(result["tasks"], start=1):
            symbol = {
                "completed": "✅",
                "failed": "❌",
                "unknown": "❔",
            }.get(task["completion_status"], "❔")

            label = discord.utils.escape_markdown(
                " ".join(task["task"].split())
            )
            label = label[:120]

            review = " 🔎" if task["needs_review"] else ""
            lines.append(f"{symbol} {number}. {label}{review}")

        # Keep the example comfortably within Discord's message limit.
        summary = "\n".join(lines[:10])

        if len(lines) > 10:
            summary += f"\n…and {len(lines) - 10} more detected tasks."

        reply = (
            f"🐎 **Your Derby Roundup**\n"
            f"Found **{result['task_count']} tasks**.\n\n"
            f"{summary}"
        )

        if result["status"] == "needs_review":
            reply += "\n\n🔎 Some details or screenshot overlaps need checking."

        reply += (
            "\n\n-# This feature is in preliminary testing. "
            "No need to report errors or correct me at this time."
        )

        await context.send(
            reply,
            reply=True
        )

    except Exception:
        logger.exception("Could not process derby log %s", message.id)

        # await message.reply(
        #     "🌾 I couldn’t read that log. Try sending clearer screenshots.",
        #     mention_author=False,
        # )