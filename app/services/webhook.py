import asyncio
import logging

import httpx

logger = logging.getLogger("webhook_sender")

MAX_RETRIES = 3


class WebhookSender:
    async def send(self, url: str, payload: dict) -> bool:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload)
                    logger.info(
                        "Webhook %s attempt=%d status=%d", url, attempt, resp.status_code
                    )
                    if resp.is_success:
                        return True
            except Exception as e:
                logger.warning("Webhook %s attempt=%d error=%s", url, attempt, e)

            if attempt < MAX_RETRIES:
                await asyncio.sleep(2**attempt)

        logger.error("Webhook %s failed after %d attempts", url, MAX_RETRIES)
        return False
