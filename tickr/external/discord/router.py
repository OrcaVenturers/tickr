from loguru import logger


def getDiscordWebhookRoute(instrument: str):
    match instrument:
        case i if "NQ" in i:
            webhook = DISCORD_WEBHOOK_URL.NQ
        case i if "ES" in i:
            webhook = DISCORD_WEBHOOK_URL.ES
        case _:
            webhook = DISCORD_WEBHOOK_URL.ES  # Default case
    logger.debug(f"Webhook for instrument: {instrument} - webhook: {webhook}")
    return webhook