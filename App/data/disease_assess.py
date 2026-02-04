"""
Phase 1: Data-driven disease/pest risk rules by (crop, stage).
Each rule: condition (temp/humidity/rain/wind) + thresholds → level + disease/pest + message + actions.
"""

from typing import Any

# Rule condition types
COND_TEMP_HIGH = "temp_high"       # temp_c >= temp_min
COND_TEMP_LOW = "temp_low"        # temp_c <= temp_max
COND_HUMIDITY_HIGH = "humidity_high"  # humidity >= humidity_min
COND_CHANCE_RAIN_HIGH = "chance_of_rain_high"  # chance_of_rain >= chance_min
COND_WIND_HIGH = "wind_high"      # wind_kph >= wind_min

# (crop, stage) -> list of rules. Each rule can trigger independently.
DISEASE_PEST_RULES: dict[tuple[str, str], list[dict[str, Any]]] = {
    # Wheat
    ("Wheat", "Sowing"): [
        {"condition": COND_HUMIDITY_HIGH, "humidity_min": 80, "level": "MEDIUM",
         "disease": "Seedling Fungal Disease",
         "message_en": "High humidity at sowing increases risk of fungal infection.",
         "message_ur": "بوائی کے وقت زیادہ نمی پھپھوندی کے خطرے کو بڑھاتی ہے۔",
         "actions_en": ["Use treated seeds", "Ensure proper drainage"],
         "actions_ur": ["علاج شدہ بیج استعمال کریں", "اچھی نکاسی یقینی بنائیں"]},
     
    ],
    ("Wheat", "Vegetative"): [
        {"condition": COND_HUMIDITY_HIGH, "humidity_min": 80, "level": "MEDIUM",
         "disease": "Leaf Rust / Powdery Mildew",
         "message_en": "High humidity favors foliar diseases. Scout for symptoms.",
         "message_ur": "زیادہ نمی پتوں کی بیماریوں کو پسند کرتی ہے۔ علامات دیکھیں۔",
         "actions_en": ["Scout regularly", "Avoid overhead irrigation at night"],
         "actions_ur": ["باقاعدگی سے معائنہ کریں", "رات کو اوپر سے آبپاشی سے گریز کریں"]},
    ],
    ("Wheat", "Flowering"): [
        {"condition": COND_HUMIDITY_HIGH, "humidity_min": 80, "level": "HIGH",
         "disease": "Yellow Rust",
         "message_en": "High humidity increases Yellow Rust risk. Apply fungicide if necessary.",
         "message_ur": "زیادہ نمی زرد زنگ کے خطرے کو بڑھاتی ہے۔ ضرورت ہو تو فنگسائڈ لگائیں۔",
         "actions_en": ["Apply preventive fungicide", "Monitor lower leaves daily"],
         "actions_ur": ["حفاظتی فنگسائڈ لگائیں", "نچلے پتوں پر روزانہ نظر رکھیں"]},
    ],
    ("Wheat", "Harvest"): [
        {"condition": COND_CHANCE_RAIN_HIGH, "chance_min": 60, "level": "MEDIUM",
         "disease": "Grain Rot",
         "message_en": "Rain at harvest can increase grain rot and storage problems.",
         "message_ur": "کٹائی کے وقت بارش دانے کے سڑنے اور ذخیرہ کے مسائل پیدا کر سکتی ہے۔",
         "actions_en": ["Harvest promptly", "Dry grains properly"],
         "actions_ur": ["فوری کٹائی کریں", "دانوں کو اچھی طرح خشک کریں"]},
    ],

    # Rice
    ("Rice", "Sowing"): [
        {"condition": COND_TEMP_LOW, "temp_max": 18, "level": "HIGH",
         "disease": "Seedling Rot",
         "message_en": "Low temperature delays germination and increases seedling disease risk.",
         "message_ur": "کم درجہ حرارت اگانے میں تاخیر اور پودوں کی بیماری بڑھاتا ہے۔",
         "actions_en": ["Use pre-germinated seeds", "Maintain nursery water level"],
         "actions_ur": ["پہلے سے اگے ہوئے بیج استعمال کریں", "نرسری میں پانی کا لیول برقرار رکھیں"]},
    ],
    ("Rice", "Vegetative"): [
        {"condition": COND_HUMIDITY_HIGH, "humidity_min": 85, "level": "MEDIUM",
         "disease": "Blast / Bacterial Blight",
         "message_en": "High humidity favors blast and blight. Monitor regularly.",
         "message_ur": "زیادہ نمی بلاسٹ اور بیکٹیریل بلائٹ کو پسند کرتی ہے۔ باقاعدہ نگرانی کریں۔",
         "actions_en": ["Scout fields", "Apply fungicide if needed"],
         "actions_ur": ["کھیتوں کا معائنہ کریں", "ضرورت پر فنگسائڈ لگائیں"]},
    ],
    ("Rice", "Flowering"): [
        {"condition": COND_CHANCE_RAIN_HIGH, "chance_min": 60, "level": "HIGH",
         "disease": "Grain Rot / Sheath Blight",
         "message_en": "Rain during flowering favors fungal diseases. Apply preventive measures.",
         "message_ur": "پھولنے کے دوران بارش پھپھوندی بیماریوں کو فروغ دیتی ہے۔ حفاظتی اقدامات کریں۔",
         "actions_en": ["Apply fungicide if needed", "Ensure proper drainage"],
         "actions_ur": ["ضرورت ہو تو فنگسائڈ لگائیں", "اچھی نکاسی یقینی بنائیں"]},
    ],
    ("Rice", "Harvest"): [
        {"condition": COND_CHANCE_RAIN_HIGH, "chance_min": 50, "level": "MEDIUM",
         "disease": "Grain Rot",
         "message_en": "Rain at harvest can cause grain rot and sprouting.",
         "message_ur": "کٹائی کے وقت بارش دانے کے سڑنے اور اگنے کا سبب بن سکتی ہے۔",
         "actions_en": ["Harvest before rain", "Dry grains immediately"],
         "actions_ur": ["بارش سے پہلے کٹائی کریں", "فوری طور پر دانے خشک کریں"]},
    ],
    # Cotton
    ("Cotton", "Sowing"): [
        {"condition": COND_TEMP_LOW, "temp_max": 18, "level": "MEDIUM",
         "disease_pest": "Seedling Pest / Damping Off",
         "message_en": "Cool soil delays emergence and may favor seedling pests.",
         "message_ur": "ٹھنڈی مٹی اگنے میں تاخیر اور پودوں کے کیڑوں کے لیے سازگار ہے۔",
         "actions_en": ["Wait for soil warming", "Use treated seeds"],
         "actions_ur": ["مٹی کے گرم ہونے کا انتظار کریں", "علاج شدہ بیج استعمال کریں"]},
    ],
    ("Cotton", "Vegetative"): [
        {"condition": COND_TEMP_HIGH, "temp_min": 40, "level": "HIGH",
         "disease_pest": "Bollworm",
         "message_en": "High temperature favors bollworm infestation.",
         "message_ur": "زیادہ درجہ حرارت ٹینڈے کے کیڑوں کو فروغ دیتا ہے۔",
         "actions_en": ["Monitor regularly", "Apply appropriate insecticide"],
         "actions_ur": ["باقاعدگی سے نگرانی کریں", "مناسب کیڑے مار دوا لگائیں"]},
    ],
    ("Cotton", "Flowering"): [
        {"condition": COND_HUMIDITY_HIGH, "humidity_min": 75, "level": "MEDIUM",
         "disease_pest": "Boll Rot / Aphids",
         "message_en": "High humidity favors boll rot and aphid infestation.",
         "message_ur": "زیادہ نمی ٹینڈے سڑن اور افڈ کے حملے کو فروغ دیتی ہے۔",
         "actions_en": ["Scout flowers and bolls", "Avoid excessive nitrogen"],
         "actions_ur": ["پھول اور ٹینڈے دیکھیں", "زیادہ نائٹروجن سے گریز کریں"]},
    ],
    ("Cotton", "Harvest"): [
        {"condition": COND_CHANCE_RAIN_HIGH, "chance_min": 50, "level": "MEDIUM",
         "disease_pest": "Lint Quality Issues",
         "message_en": "Rain during picking reduces lint quality and favors staining.",
         "message_ur": "چنائی کے دوران بارش روئی کے معیار کو کم اور داغ لگنے کو بڑھاتی ہے۔",
         "actions_en": ["Pick when weather is dry", "Avoid storing wet cotton"],
         "actions_ur": ["خشک موسم میں چنائی کریں", "گیلی روئی ذخیرہ نہ کریں"]},
    ],
    # Sugarcane
    ("Sugarcane", "Sowing"): [
        {"condition": COND_TEMP_LOW, "temp_max": 18, "level": "MEDIUM",
         "disease_pest": "Shoot Borer / Seedling Pests",
         "message_en": "Cool temperature favors shoot borer and seedling pest attack.",
         "message_ur": "ٹھنڈا درجہ حرارت شوٹ بورر اور پودوں کے کیڑوں کو فروغ دیتا ہے۔",
         "actions_en": ["Delay sowing if possible", "Use treated setts"],
         "actions_ur": ["اگر ممکن ہو تو بوائی مؤخر کریں", "علاج شدہ سیٹس استعمال کریں"]},
    ],
    ("Sugarcane", "Vegetative"): [
        {"condition": COND_HUMIDITY_HIGH, "humidity_min": 80, "level": "MEDIUM",
         "disease_pest": "Top Borer / Aphids",
         "message_en": "High humidity favors top borer and aphid attack.",
         "message_ur": "زیادہ نمی ٹاپ بورر اور افڈ کے حملے کو فروغ دیتا ہے۔",
         "actions_en": ["Monitor plants", "Use borer traps or insecticides if needed"],
         "actions_ur": ["پودوں کی نگرانی کریں", "ضرورت ہو تو کیڑے مار دوا یا ٹریپ لگائیں"]},
    ],
    ("Sugarcane", "Flowering"): [
        {"condition": COND_TEMP_HIGH, "temp_min": 40, "level": "HIGH",
         "disease_pest": "Top Borer / Aphids",
         "message_en": "High temperature favors pest attack during flowering.",
         "message_ur": "پھولنے کے دوران زیادہ درجہ حرارت کیڑوں کے حملے کو فروغ دیتا ہے۔",
         "actions_en": ["Scout regularly", "Apply insecticide if infestation detected"],
         "actions_ur": ["باقاعدگی سے نگرانی کریں", "اگر حملہ ہوا تو کیڑے مار دوا لگائیں"]},
    ],
    ("Sugarcane", "Harvest"): [
        {"condition": COND_CHANCE_RAIN_HIGH, "chance_min": 60, "level": "LOW",
         "disease_pest": "Storage Damage",
         "message_en": "Heavy rain may delay harvest and increase pest/storage damage.",
         "message_ur": "زیادہ بارش کٹائی مؤخر اور کیڑوں / ذخیرہ کو نقصان پہنچا سکتی ہے۔",
         "actions_en": ["Harvest when dry", "Plan crushing schedule around weather"],
         "actions_ur": ["خشک موسم میں کٹائی کریں", "موسم کے مطابق کرشنگ شیڈول بنائیں"]},
    ],
    # Maize
    ("Maize", "Sowing"): [
        {"condition": COND_TEMP_LOW, "temp_max": 10, "level": "HIGH",
         "disease_pest": "Seedling Disease",
         "message_en": "Cold soil delays emergence and favors seedling disease.",
         "message_ur": "سرد مٹی اگنے میں تاخیر اور پودوں کی بیماری کو فروغ دیتا ہے۔",
         "actions_en": ["Delay sowing until soil warms", "Use treated seed"],
         "actions_ur": ["مٹی گرم ہونے تک بوائی مؤخر کریں", "علاج شدہ بیج استعمال کریں"]},
    ],
    ("Maize", "Vegetative"): [
        {"condition": COND_TEMP_HIGH, "temp_min": 38, "level": "HIGH",
         "disease_pest": "Fall Armyworm",
         "message_en": "High temperature favors fall armyworm infestation.",
         "message_ur": "زیادہ درجہ حرارت فال آرمی ورم کے حملے کو فروغ دیتا ہے۔",
         "actions_en": ["Scout leaves", "Apply appropriate pesticide if needed"],
         "actions_ur": ["پتوں کا معائنہ کریں", "ضرورت ہو تو کیڑے مار دوا لگائیں"]},
    ],
    ("Maize", "Flowering"): [
        {"condition": COND_TEMP_HIGH, "temp_min": 35, "level": "HIGH",
         "disease_pest": "Fall Armyworm / Stalk Borer",
         "message_en": "High temperature favors pest attack during flowering.",
         "message_ur": "پھولنے کے دوران زیادہ درجہ حرارت کیڑوں کے حملے کو فروغ دیتا ہے۔",
         "actions_en": ["Monitor silks", "Irrigate to reduce stress"],
         "actions_ur": ["ریشمی مرحلے پر نگرانی کریں", "دباؤ کم کرنے کے لیے آبپاشی کریں"]},
    ],
    ("Maize", "Harvest"): [
        {"condition": COND_CHANCE_RAIN_HIGH, "chance_min": 60, "level": "MEDIUM",
         "disease_pest": "Ear Rot / Storage Damage",
         "message_en": "Rain at harvest can cause ear rot and storage problems.",
         "message_ur": "کٹائی کے وقت بارش کان میں سڑن اور ذخیرہ کے مسائل پیدا کر سکتی ہے۔",
         "actions_en": ["Harvest at proper moisture", "Dry and store properly"],
         "actions_ur": ["مناسب نمی پر کٹائی کریں", "اچھی طرح خشک اور ذخیرہ کریں"]},
    ],
}

# Default when no rule triggers
DEFAULT_LOW_RISK = {
    "message_en": "No significant disease/pest risk.",
    "message_ur": "کوئی خطرہ نہیں",
    "actions_en": [],
    "actions_ur": [],
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
        print("Temp: ", temp)
        return temp >= rule.get("temp_min", 35)
    if cond == COND_TEMP_LOW and temp is not None:
        print("Temp: ", temp)
        return temp <= rule.get("temp_max", 10)
    if cond == COND_HUMIDITY_HIGH and humidity is not None:
       
        return humidity >= rule.get("humidity_min", 80)
    if cond == COND_CHANCE_RAIN_HIGH and chance_rain is not None:
        print("Chance of rain: ", chance_rain)
        return chance_rain >= rule.get("chance_min", 50)
    if cond == COND_WIND_HIGH and wind is not None:
        print("Wind: ", wind)
        return wind >= rule.get("wind_min", 40)
    return False

def evaluate_disease_pest_risk(
    crop: str,
    stage: str,
    weather: dict[str, float],
) -> list[dict[str, Any]]:
    """
    Evaluate disease/pest risk rules for (crop, stage) against current weather.
    Returns list of triggered risk items, each with level, message_en, message_ur, actions_en, actions_ur.
    """
    key = (crop.strip(), stage.strip())
    rules = DISEASE_PEST_RULES.get(key, [])
    triggered: list[dict[str, Any]] = []

    for rule in rules:
        if _rule_matches(rule, weather):
            triggered.append({
                "level": rule.get("level", "LOW"),
                "message_en": rule.get("message_en", ""),
                "message_ur": rule.get("message_ur", rule.get("message_en", "")),
                "actions_en": rule.get("actions_en", []),
                "actions_ur": rule.get("actions_ur", rule.get("actions_en", [])),
            })

    if not triggered:
        triggered = [{
            "level": "LOW",
            "message_en": DEFAULT_LOW_RISK["message_en"],
            "message_ur": DEFAULT_LOW_RISK["message_ur"],
            "actions_en": DEFAULT_LOW_RISK["actions_en"],
            "actions_ur": DEFAULT_LOW_RISK["actions_ur"],
        }]
    return triggered

if __name__ == "__main__":
    print(evaluate_disease_pest_risk("Wheat", "Sowing", {"temp_c": 40, "humidity": 86, "chance_of_rain": 50, "wind_kph": 40, "condition": "TEMP_HIGH"}))
