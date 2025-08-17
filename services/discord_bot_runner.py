from services.discord_bot import bot, settings

if __name__ == "__main__":
    print("Starting Discord bot runner...")
    if not settings.DISCORD_BOT_TOKEN:
        print("DISCORD_BOT_TOKEN not set! Exiting.")
    else:
        bot.run(settings.DISCORD_BOT_TOKEN)
