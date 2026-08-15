"""Mini App API serverini ishga tushirish.

    python api_server.py

Bot bilan alohida jarayonda ishlaydi — biri qulasa ikkinchisi ishlab
turaveradi. Prodda oldiga nginx qo'yiladi (Telegram Mini App uchun HTTPS
majburiy).
"""
import uvicorn

import config

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host=config.API_HOST,
        port=config.API_PORT,
        log_level=config.LOG_LEVEL.lower(),
    )
