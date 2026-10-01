
# هون الخرج يعني اسماء الحقول الموحدة بالخرج
REQUIRED_FIELDS = [
    "first_name",       
    "father_name",     
    "family_name",       
    "mother_name",     
    "birth_date",         
    "amanah",         
    "registry_number",
    "national_number",
]

OPTIONAL_FIELDS = [
    "mother_family_name",  
]

ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

CIVIL_REGISTRY_REQUIRED_FIELDS = REQUIRED_FIELDS
CIVIL_REGISTRY_ALL_FIELDS = ALL_FIELDS
NATIONAL_ID_REQUIRED_FIELDS = REQUIRED_FIELDS
NATIONAL_ID_ALL_FIELDS = ALL_FIELDS
# لا تعدل هون ابداً ولا حتى تضيف
FIELD_LABELS = {
    "first_name": ["الاسم", "الا سم", "الإسم"],
    "father_name": ["اسم الاب", "إسم الأب", "اسم الأب"],
    "family_name": ["النسبة", "الشهرة", "الكنية"],
    "mother_name": [
        "اسم الام ونسبتها", "إسم الام", "اسم الام", "اسم و نسبة الأم",
        "اسم ونسبة الأم", "اسم و نسبة الام",
    ],
    "mother_family_name": [],
    "birth_date": [
        "تاريخ الولادة", "محل وتاريخ الولادة","محل و تاريخ الولادة","تاريخ الميلاد",
        "بتاريخ الولادة",
    ],

    "amanah": ["الامانة", "الأمانة"],
    "registry_number": [
        "محل ورقم القيد", "رقم القيد", "محل القيد", "القيد",
    ],
    "national_number": ["الرقم الوطني", "رقم وطني"],
    "_grandfather_name": ["اسم الجد"],
    "_nationality": ["الجنسية"],
    "_gender": ["الجنس"],
    "_governorate": ["المحافظة"],
    "_religion": ["الدين"],
    "_marital_status": ["الوضع العائلي"],
    "_card_number": ["رقم البطاقة"],
    "_issue_date": ["تاريخ الاصدار", "تاريخ الإصدار", "تاريخ المنح"],
    "_registration_date": ["تاريخ التسجيل"],
    "_notes": ["ملاحظات"],
}

LABEL_MATCH_THRESHOLD = 78
MIN_LABEL_LENGTH_RATIO = 0.35
MIN_OCR_CONFIDENCE = 40
NOISE_CONFIDENCE_FLOOR = 25
EXPECTED_NATIONAL_NUMBER_LENGTH = 11