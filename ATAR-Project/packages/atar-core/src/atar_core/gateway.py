"""ATAR Telegram gateway — bot process with allowlist security."""

from __future__ import annotations

import asyncio
import contextlib
import os

from atar_core.config import load_config


class TelegramGateway:
    """Long-running Telegram bot using python-telegram-bot."""

    def __init__(self, bot_token: str, agent_factory=None) -> None:
        self.token = bot_token
        self.agent_factory = agent_factory
        cfg = load_config()
        self.allowed_ids: set[int] = set(cfg.get("telegram", {}).get("allowed_user_ids", []))
        self._sessions: dict[int, list] = {}  # chat_id → messages

    async def start(self) -> None:
        """Start polling loop."""
        try:
            from telegram import Update
            from telegram.ext import Application, ContextTypes, MessageHandler, filters
        except ImportError as err:
            raise ImportError(
                "python-telegram-bot not installed. Run: pip install python-telegram-bot[job-queue]"
            ) from err

        async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            user_id = update.effective_user.id if update.effective_user else 0

            if user_id not in self.allowed_ids:
                return  # silently ignore

            text = update.message.text if update.message else ""
            if not text:
                return

            # Use same Agent as REPL
            if not self.agent_factory:
                await update.message.reply_text("Agent not available.")
                return

            agent = self.agent_factory()
            msg = await update.message.reply_text("● thinking...")

            # Stream response
            response_parts = []
            async def on_delta(t: str) -> None:
                response_parts.append(t)
                if len(response_parts) % 5 == 0:
                    with contextlib.suppress(Exception):
                        await msg.edit_text("".join(response_parts)[:4000])

            try:
                await agent.run(text, callbacks=None)  # Simple run, no streaming callback
                final = agent._messages[-1].content if agent._messages else "Done."
                await msg.edit_text(final[:4000])
            except Exception as e:
                await msg.edit_text(f"Error: {e}"[:1000])

        app = Application.builder().token(self.token).build()
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        print(f"Telegram gateway started. Allowed users: {self.allowed_ids}")
        await app.run_polling()


def start_gateway():
    """Entry point for 'atar gateway telegram' CLI."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("Set TELEGRAM_BOT_TOKEN environment variable.")
        return

    async def _run():
        gw = TelegramGateway(token)
        await gw.start()

    asyncio.run(_run())
