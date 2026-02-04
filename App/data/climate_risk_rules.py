"""
Phase 1: Data-driven climate risk rules by (crop, stage).
Each rule: condition (temp/humidity/rain/wind) + thresholds → level + message + actions.
"""

from typing import Any

# Rule condition types
COND_TEMP_HIGH = "temp_high"       # temp_c >= temp_min
COND_TEMP_LOW = "temp_low"        # temp_c <= temp_max
COND_HUMIDITY_HIGH = "humidity_high"  # humidity >= humidity_min
COND_CHANCE_RAIN_HIGH = "chance_of_rain_high"  # chance_of_rain >= chance_min
COND_WIND_HIGH = "wind_high"      # wind_kph >= wind_min

# (crop, stage) -> list of rules. Each rule can trigger independently.
CLIMATE_RISK_RULES: dict[tuple[str, str], list[dict[str, Any]]] = {
    # Wheat
    ("Wheat", "Sowing"): [
        {"condition": COND_TEMP_LOW, "temp_max": 5, "level": "HIGH",
         "message_en": "Frost risk. Low temperature can damage seedlings.",
         "message_ur": "پالا کا خطرہ۔ کم درجہ حرارت بیجوں کو نقصان پہنچا سکتا ہے۔",
         "actions_en": ["Delay sowing if possible.", "Monitor soil temperature."],
         "actions_ur": ["اگر ممکن ہو تو بوائی مؤخر کریں۔", "مٹی کے درجہ حرارت پر نظر رکھیں۔"]},
        {"condition": COND_HUMIDITY_HIGH, "humidity_min": 85, "level": "MEDIUM",
         "message_en": "High humidity at sowing increases fungal risk. Use treated seed.",
         "message_ur": "بوائی کے وقت زیادہ نمی پھپھوندی کے خطرے کو بڑھاتی ہے۔ علاج شدہ بیج استعمال کریں۔",
         "actions_en": ["Use treated seed.", "Ensure good drainage."],
         "actions_ur": ["علاج شدہ بیج استعمال کریں۔", "اچھی نکاسی یقینی بنائیں۔"]},
    ],
    ("Wheat", "Vegetative"): [
        {"condition": COND_TEMP_HIGH, "temp_min": 38, "level": "HIGH",
         "message_en": "Heat stress during vegetative stage can stunt growth.",
         "message_ur": "نباتاتی مرحلے میں گرمی کا دباؤ نشوونما روک سکتا ہے۔",
         "actions_en": ["Irrigate in early morning or evening.", "Monitor for heat stress."],
         "actions_ur": ["صبح سویرے یا شام کو آبپاشی کریں۔", "گرمی کے دباؤ پر نظر رکھیں۔"]},
        {"condition": COND_HUMIDITY_HIGH, "humidity_min": 80, "level": "MEDIUM",
         "message_en": "High humidity favors foliar diseases. Scout for early symptoms.",
         "message_ur": "زیادہ نمی پتوں کی بیماریوں کو پسند کرتی ہے۔ ابتدائی علامات دیکھیں۔",
         "actions_en": ["Scout for disease symptoms.", "Avoid overhead irrigation at night."],
         "actions_ur": ["بیماری کی علامات دیکھیں۔", "رات کو اوپر سے آبپاشی سے گریز کریں۔"]},
    ],
    ("Wheat", "Flowering"): [
        {"condition": COND_TEMP_HIGH, "temp_min": 35, "level": "HIGH",
         "message_en": "Heat stress during flowering reduces grain set and yield.",
         "message_ur": "پھول لگتے وقت گرمی کا دباؤ دانے اور پیداوار کم کر سکتا ہے۔",
         "actions_en": ["Irrigate in early morning.", "Monitor for blight and rust."],
         "actions_ur": ["صبح سویرے آبپاشی کریں۔", "جھلساؤ اور زنگ پر نظر رکھیں۔"]},
        {"condition": COND_HUMIDITY_HIGH, "humidity_min": 80, "level": "HIGH",
         "message_en": "High humidity favors Yellow Rust and other fungal diseases. Preventative fungicide recommended.",
         "message_ur": "زیادہ نمی زرد زنگ اور دیگر پھپھوندی بیماریوں کو پسند کرتی ہے۔ حفاظتی فنگسائڈ تجویز ہے۔",
         "actions_en": ["Apply preventative fungicide if not done.", "Monitor lower leaves daily."],
         "actions_ur": ["اگر نہیں کیا تو حفاظتی فنگسائڈ استعمال کریں۔", "نچلے پتوں پر روزانہ نظر رکھیں۔"]},
    ],
    ("Wheat", "Harvest"): [
        {"condition": COND_CHANCE_RAIN_HIGH, "chance_min": 60, "level": "HIGH",
         "message_en": "Rain forecast during harvest increases lodging and grain damage risk.",
         "message_ur": "کٹائی کے دوران بارش کی پیشگوئی گرنے اور دانے کے نقصان کا خطرہ بڑھاتی ہے۔",
         "actions_en": ["Harvest as soon as grain is ready.", "Avoid harvesting when wet."],
         "actions_ur": ["جیسے ہی دانہ تیار ہو کٹائی کریں۔", "گیلے وقت کٹائی سے گریز کریں۔"]},
    ],

    # Rice
    ("Rice", "Sowing"): [
        {"condition": COND_TEMP_LOW, "temp_max": 18, "level": "HIGH",
         "message_en": "Low temperature delays germination and increases seedling disease.",
         "message_ur": "کم درجہ حرارت اگانے میں تاخیر اور پودوں کی بیماری بڑھاتا ہے۔",
         "actions_en": ["Use pre-germinated seed in cold periods.", "Maintain nursery water level."],
         "actions_ur": ["سردی میں پہلے سے اگے ہوئے بیج استعمال کریں۔", "نرسری میں پانی کا لیول برقرار رکھیں۔"]},
    ],
    ("Rice", "Vegetative"): [
        {"condition": COND_TEMP_HIGH, "temp_min": 38, "level": "HIGH",
         "message_en": "High temperature during vegetative stage increases water demand and stress.",
         "message_ur": "نباتاتی مرحلے میں زیادہ درجہ حرارت پانی کی ضرورت اور دباؤ بڑھاتا ہے۔",
         "actions_en": ["Maintain adequate flood depth.", "Irrigate in cooler hours."],
         "actions_ur": ["پانی کی مناسب گہرائی برقرار رکھیں۔", "ٹھنڈے اوقات میں آبپاشی کریں۔"]},
    ],
    ("Rice", "Flowering"): [
        {"condition": COND_TEMP_HIGH, "temp_min": 35, "level": "HIGH",
         "message_en": "Heat during flowering causes spikelet sterility and yield loss.",
         "message_ur": "پھول لگتے وقت گرمی سے بالیوں میں بانجھ پن اور پیداوار کم ہوتی ہے۔",
         "actions_en": ["Keep field flooded during flowering.", "Avoid water stress."],
         "actions_ur": ["پھول لگتے وقت کھیت میں پانی رکھیں۔", "پانی کے دباؤ سے گریز کریں۔"]},
        {"condition": COND_HUMIDITY_HIGH, "humidity_min": 85, "level": "MEDIUM",
         "message_en": "High humidity favors blast and bacterial blight. Monitor regularly.",
         "message_ur": "زیادہ نمی بلاسٹ اور بیکٹیریل بلائٹ کو پسند کرتی ہے۔ باقاعدہ نگرانی کریں۔",
         "actions_en": ["Scout for blast and blight.", "Apply recommended fungicide if needed."],
         "actions_ur": ["بلاسٹ اور بلائٹ دیکھیں۔", "ضرورت ہو تو تجویز کردہ فنگسائڈ استعمال کریں۔"]},
    ],
    ("Rice", "Harvest"): [
        {"condition": COND_CHANCE_RAIN_HIGH, "chance_min": 50, "level": "MEDIUM",
         "message_en": "Rain at harvest can cause lodging and grain sprouting.",
         "message_ur": "کٹائی کے وقت بارش گرنے اور دانے اگانے کا سبب بن سکتی ہے۔",
         "actions_en": ["Plan harvest before rain.", "Dry grain promptly after harvest."],
         "actions_ur": ["بارش سے پہلے کٹائی کی منصوبہ بندی کریں۔", "کٹائی کے فوراً بعد دانہ خشک کریں۔"]},
    ],

    # Cotton
    ("Cotton", "Sowing"): [
        {"condition": COND_TEMP_LOW, "temp_max": 18, "level": "MEDIUM",
         "message_en": "Cool soil delays cotton emergence. Consider delaying sowing.",
         "message_ur": "ٹھنڈی مٹی روئی کے اگانے میں تاخیر کرتی ہے۔ بوائی مؤخر کرنے پر غور کریں۔",
         "actions_en": ["Wait for soil warming.", "Use quality seed."],
         "actions_ur": ["مٹی کے گرم ہونے کا انتظار کریں۔", "معیاری بیج استعمال کریں۔"]},
    ],
    ("Cotton", "Vegetative"): [
        {"condition": COND_TEMP_HIGH, "temp_min": 40, "level": "HIGH",
         "message_en": "Extreme heat stresses cotton. Boll shed may increase.",
         "message_ur": "انتہائی گرمی روئی پر دباؤ ڈالتی ہے۔ ٹینڈے گرنے میں اضافہ ہو سکتا ہے۔",
         "actions_en": ["Ensure adequate irrigation.", "Monitor for pest buildup."],
         "actions_ur": ["کافی آبپاشی یقینی بنائیں۔", "کیڑوں کی تعداد پر نظر رکھیں۔"]},
    ],
    ("Cotton", "Flowering"): [
        {"condition": COND_HUMIDITY_HIGH, "humidity_min": 75, "level": "MEDIUM",
         "message_en": "High humidity favors boll rot and foliar diseases.",
         "message_ur": "زیادہ نمی ٹینڈے سڑنے اور پتوں کی بیماریوں کو پسند کرتی ہے۔",
         "actions_en": ["Avoid excessive nitrogen.", "Scout for boll rot."],
         "actions_ur": ["ضرورت سے زیادہ نائٹروجن سے گریز کریں۔", "ٹینڈے سڑن پر نظر رکھیں۔"]},
    ],
    ("Cotton", "Harvest"): [
        {"condition": COND_CHANCE_RAIN_HIGH, "chance_min": 50, "level": "MEDIUM",
         "message_en": "Rain during picking reduces lint quality and favors staining.",
         "message_ur": "چنائی کے دوران بارش روئی کے معیار کو کم اور داغ لگنے کو بڑھاتی ہے۔",
         "actions_en": ["Pick when weather is dry.", "Avoid storing wet cotton."],
         "actions_ur": ["خشک موسم میں چنائی کریں۔", "گیلی روئی ذخیرہ نہ کریں۔"]},
    ],

    # Sugarcane
    ("Sugarcane", "Sowing"): [],
    ("Sugarcane", "Vegetative"): [
        {"condition": COND_TEMP_HIGH, "temp_min": 40, "level": "MEDIUM",
         "message_en": "Very high temperature increases water demand. Maintain irrigation.",
         "message_ur": "بہت زیادہ درجہ حرارت پانی کی ضرورت بڑھاتا ہے۔ آبپاشی برقرار رکھیں۔",
         "actions_en": ["Irrigate regularly.", "Monitor for borers."],
         "actions_ur": ["باقاعدہ آبپاشی کریں۔", "سرکنڈے کھانے والے کیڑوں پر نظر رکھیں۔"]},
    ],
    ("Sugarcane", "Flowering"): [],
    ("Sugarcane", "Harvest"): [
        {"condition": COND_CHANCE_RAIN_HIGH, "chance_min": 60, "level": "LOW",
         "message_en": "Heavy rain can delay harvest and damage standing crop.",
         "message_ur": "زیادہ بارش کٹائی مؤخر اور کھڑی فصل کو نقصان پہنچا سکتی ہے۔",
         "actions_en": ["Plan crushing schedule around weather.", "Harvest when dry."],
         "actions_ur": ["موسم کے مطابق کرشنگ کا شیڈول بنائیں۔", "خشک موسم میں کٹائی کریں۔"]},
    ],

    # Maize
    ("Maize", "Sowing"): [
        {"condition": COND_TEMP_LOW, "temp_max": 10, "level": "HIGH",
         "message_en": "Cold soil delays maize emergence and increases seedling disease.",
         "message_ur": "سرد مٹی مکئی کے اگانے میں تاخیر اور پودوں کی بیماری بڑھاتی ہے۔",
         "actions_en": ["Delay sowing until soil warms.", "Use treated seed."],
         "actions_ur": ["مٹی گرم ہونے تک بوائی مؤخر کریں۔", "علاج شدہ بیج استعمال کریں۔"]},
    ],
    ("Maize", "Vegetative"): [
        {"condition": COND_TEMP_HIGH, "temp_min": 38, "level": "HIGH",
         "message_en": "Heat stress during vegetative stage reduces growth and yield potential.",
         "message_ur": "نباتاتی مرحلے میں گرمی کا دباؤ نشوونما اور پیداواری صلاحیت کم کرتا ہے۔",
         "actions_en": ["Irrigate adequately.", "Monitor for fall armyworm."],
         "actions_ur": ["کافی آبپاشی کریں۔", "فال آرمی ورم پر نظر رکھیں۔"]},
    ],
    ("Maize", "Flowering"): [
        {"condition": COND_TEMP_HIGH, "temp_min": 35, "level": "HIGH",
         "message_en": "Heat during pollination causes poor kernel set.",
         "message_ur": "پولنیشن کے دوران گرمی سے دانے کم لگتے ہیں۔",
         "actions_en": ["Ensure irrigation during silking.", "Avoid water stress."],
         "actions_ur": ["ریشمی مرحلے میں آبپاشی یقینی بنائیں۔", "پانی کے دباؤ سے گریز کریں۔"]},
    ],
    ("Maize", "Harvest"): [
        {"condition": COND_CHANCE_RAIN_HIGH, "chance_min": 60, "level": "MEDIUM",
         "message_en": "Rain at harvest can cause ear rot and storage problems.",
         "message_ur": "کٹائی کے وقت بارش کان میں سڑن اور ذخیرہ کے مسائل پیدا کر سکتی ہے۔",
         "actions_en": ["Harvest at proper moisture.", "Dry and store properly."],
         "actions_ur": ["مناسب نمی پر کٹائی کریں۔", "اچھی طرح خشک اور ذخیرہ کریں۔"]},
    ],
}

# Default when no rule triggers: favorable conditions
DEFAULT_LOW_RISK = {
    "message_en": "Weather forecast is favorable for the current stage. No extreme conditions predicted.",
    "message_ur": "موجودہ مرحلے کے لیے موسم کی پیشگوئی سازگار ہے۔ انتہائی حالات کی پیشگوئی نہیں۔",
    "actions_en": ["Continue routine irrigation.", "Maintain standard checks."],
    "actions_ur": ["معمول کی آبپاشی جاری رکھیں۔", "معیاری جانچ پڑتال برقرار رکھیں."],
}

LEVEL_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}


def _rule_matches(rule: dict[str, Any], weather: dict[str, float]) -> bool:
    """Return True if the rule's condition is satisfied by current weather."""
    cond = rule.get("condition")
    if not cond:
        return False
    temp = weather.get("temp_c")
    humidity = weather.get("humidity")
    chance_rain = weather.get("chance_of_rain")
    wind = weather.get("wind_kph")

    if cond == COND_TEMP_HIGH and temp is not None:
        return temp >= rule.get("temp_min", 35)
    if cond == COND_TEMP_LOW and temp is not None:
        return temp <= rule.get("temp_max", 10)
    if cond == COND_HUMIDITY_HIGH and humidity is not None:
 
        return humidity >= rule.get("humidity_min", 80)
    if cond == COND_CHANCE_RAIN_HIGH and chance_rain is not None:
        return chance_rain >= rule.get("chance_min", 50)
    if cond == COND_WIND_HIGH and wind is not None:
        return wind >= rule.get("wind_min", 40)
    return False


def evaluate_climate_risk(
    crop: str,
    stage: str,
    weather: dict[str, float],
) -> list[dict[str, Any]]:
    """
    Evaluate climate risk rules for (crop, stage) against current weather.
    Returns list of triggered risk items, each with level, message_en, message_ur, actions_en, actions_ur.
    """
    key = (crop.strip(), stage.strip())
    rules = CLIMATE_RISK_RULES.get(key, [])
    triggered = []
    for rule in rules:
        if _rule_matches(rule, weather):
            triggered.append({
                "level": rule["level"],
                "message_en": rule.get("message_en", ""),
                "message_ur": rule.get("message_ur", rule.get("message_en", "")),
                "actions_en": rule.get("actions_en", []),
                "actions_ur": rule.get("actions_ur", rule.get("actions_en", [])),
            })
    if not triggered:
        # No rule triggered -> LOW risk, default message
        triggered = [{
            "level": "LOW",
            "message_en": DEFAULT_LOW_RISK["message_en"],
            "message_ur": DEFAULT_LOW_RISK["message_ur"],
            "actions_en": DEFAULT_LOW_RISK["actions_en"],
            "actions_ur": DEFAULT_LOW_RISK["actions_ur"],
        }]
    return triggered


def get_overall_level(triggered: list[dict[str, Any]]) -> str:
    """Return the highest risk level from triggered list."""
    if not triggered:
        return "LOW"
    return max(triggered, key=lambda x: LEVEL_ORDER.get(x["level"], 0))["level"]


if __name__ == "__main__":
    print(evaluate_climate_risk("Wheat", "Vegetative", {"temp_c": 35, "humidity": 90}))