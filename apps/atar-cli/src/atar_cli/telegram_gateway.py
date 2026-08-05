"""ATAR Telegram Gateway — chat with ATAR from your phone.

Uses python-telegram-bot for real-time messaging.
Auto-detects bot token from environment or config.
"""

from __future__ import annotations

import os
import sys


async def start_telegram_gateway(
    bot_token: str = "",
    allowlist: list[int] | None = None,
    provider_id: str = "ollama",
    model: str = "",
) -> None:
    """Start the Telegram bot gateway for ATAR.

    Args:
        bot_token: Telegram bot token from @BotFather
        allowlist: List of allowed Telegram user IDs (empty = all allowed)
        provider_id: Provider to use (ollama, deepseek, openai, etc.)
        model: Model name override
    """
    token = bot_token or os.environ.get("ATAR_TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: No Telegram bot token found.")
        print("Set ATAR_TELEGRAM_TOKEN environment variable or pass --token")
        print("Get a token from @BotFather on Telegram")
        sys.exit(1)

    allowed = allowlist or []
    if not allowed:
        # Try from env
        env_list = os.environ.get("ATAR_TELEGRAM_ALLOWLIST", "")
        if env_list:
            allowed = [int(uid.strip()) for uid in env_list.split(",") if uid.strip().isdigit()]

    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
    except ImportError:
        print("python-telegram-bot not installed. Run: pip install python-telegram-bot")
        sys.exit(1)

    # Initialize agent
    agent = None
    provider = None

    print("🤖 ATAR Telegram Gateway starting...")
    print(f"   Token: {token[:8]}...")
    if allowed:
        print(f"   Allowlist: {len(allowed)} users")
    else:
        print("   Allowlist: ALL users (anyone can chat)")

    async def get_agent():
        nonlocal agent, provider
        if agent is None:
            from atar_core.agent import Agent
            prov = await _get_provider(provider_id, model)
            provider = prov
            agent = Agent(
                provider=prov,
                max_turns=8,
                interactive=False,
            )
        return agent

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        uid = update.effective_user.id if update.effective_user else 0
        if allowed and uid not in allowed:
            await update.message.reply_text("⛔ Access denied. You are not in the allowlist.")
            return
        await update.message.reply_text(
            "👋 Hello! I'm ATAR — your AI agent.\n"
            "Ask me anything, or give me tasks to complete.\n\n"
            "Commands:\n"
            "/help — Show this message\n"
            "/status — Show current status\n"
            "/model — Show current model\n"
            "/reset — Reset conversation"
        )

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        uid = update.effective_user.id if update.effective_user else 0
        if allowed and uid not in allowed:
            await update.message.reply_text("⛔ Access denied.")
            return

        text = update.message.text
        if not text:
            return

        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        try:
            ag = await get_agent()

            # Stream response
            from atar_core.agent import StreamCallbacks
            chunks: list[str] = []
            last_sent = ""

            async def on_delta(delta: str) -> None:
                nonlocal chunks, last_sent
                chunks.append(delta)
                # Send in batches of 500 chars to avoid Telegram message limits
                current = "".join(chunks)
                if len(current) - len(last_sent) > 500:
                    last_sent = current

            cb = StreamCallbacks(on_delta=on_delta)

            result = await ag.run(text, callbacks=cb)

            response = result.final_text or "".join(chunks) or "(no response)"
            # Split long responses
            if len(response) > 4000:
                for i in range(0, len(response), 4000):
                    await update.message.reply_text(response[i:i+4000])
            else:
                await update.message.reply_text(response)

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        ag = agent
        if ag:
            await update.message.reply_text(
                f"📊 Status\n"
                f"Turns: {ag._turn_count}\n"
                f"Messages: {len(ag._messages)}\n"
                f"Provider: {getattr(provider, 'display_name', 'unknown')}"
            )
        else:
            await update.message.reply_text("No active session.")

    async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        nonlocal agent
        agent = None
        await update.message.reply_text("🔄 Conversation reset.")

    async def model_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        prov = provider
        if prov:
            await update.message.reply_text(f"🤖 Model: {getattr(prov, 'display_name', prov.model)}")
        else:
            await update.message.reply_text("No active provider.")

    # Build app
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(CommandHandler("model", model_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Gateway ready. Listening for messages...")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)


async def _get_provider(provider_id: str, model: str = ""):
    """Get a provider instance, trying Ollama first (no API key needed)."""
    # Try Ollama first
    try:
        from atar_provider_ollama.client import get_ollama_provider
        ollama = get_ollama_provider()
        if ollama:
            print(f"✅ Using Ollama: {ollama.model}")
            return ollama
    except Exception:
        pass

    # Try config-based providers
    try:
        from atar_core.provider_router import create_router
        router = create_router()
        if router.providers:
            return router.providers[0]
    except Exception:
        pass

    # No providers available — guide user instead of fake fallback
    print()
    print("╔══════════════════════════════════════════╗")
    print("║  ⚠ No AI provider configured           ║")
    print("╠══════════════════════════════════════════╣")
    print("║                                        ║")
    print("║  Option 1 — Ollama (free, local):      ║")
    print("║    curl -fsSL https://ollama.com/...   ║")
    print("║    ollama pull llama3.2                ║")
    print("║                                        ║")
    print("║  Option 2 — DeepSeek (cheap, fast):    ║")
    print("║    export DEEPSEEK_API_KEY=***         ║")
    print("║                                        ║")
    print("║  Option 3 — Run setup wizard:         ║")
    print("║    atar setup                          ║")
    print("╚══════════════════════════════════════════╝")
    sys.exit(1)
