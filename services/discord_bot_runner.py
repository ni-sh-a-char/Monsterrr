from services.discord_bot import bot, settings

def run():
    bot.run(settings.DISCORD_BOT_TOKEN)
