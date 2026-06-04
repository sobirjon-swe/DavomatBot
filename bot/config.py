import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
SUPERADMIN_ID: int = int(os.getenv("SUPERADMIN_ID", "0"))
CHANNEL_ID: int = int(os.getenv("CHANNEL_ID", "0"))

DISTRICTS = [
    (1, "Bo'stonliq tumani", "Бустонлыкский район"),
    (2, "Parkent tumani", "Паркентский район"),
    (3, "Chirchiq shahar", "г. Чирчик"),
    (4, "Qibray tumani", "Кибрайский район"),
    (5, "Toshkent tumani", "Ташкентский район"),
    (6, "Zangiota tumani", "Зангиатинский район"),
    (7, "Yangiyo'l shahar", "г. Янгиюль"),
    (8, "Chinoz tumani", "Чиназский район"),
    (9, "Nurafshon shahar", "г. Нурафшон"),
    (10, "O'rtachirchiq tumani", "Уртачирчикский район"),
    (11, "Quyichirchiq tumani", "Куйичирчикский район"),
    (12, "Yuqorichirchiq tumani", "Юкоричирчикский район"),
    (13, "Ohangaron tumani", "Ахангаранский район"),
    (14, "Ohangaron shahar", "г. Ахангаран"),
    (15, "Angren shahar", "г. Ангрен"),
    (16, "Olmaliq shahar", "г. Алмалык"),
    (17, "Bekobod tumani", "Бекабадский район"),
    (18, "Bekobod shahar", "г. Бекабад"),
    (19, "Bo'ka tumani", "Букинский район"),
    (20, "Oqqo'rg'on tumani", "Аккурганский район"),
    (21, "Piskent tumani", "Пискентский район"),
]
