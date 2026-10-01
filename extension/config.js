(function (root) {
  root.RELAY_CONFIG = {
  "baseUrl": "http://localhost:8000",
  "targetTabPrefix": "http://localhost:8000/client-test",
  "openTabIfMissing": true,
  "openUrlIfMissing": "http://localhost:8000/client-test",
  "fillOnly": true,
  "autodetectLabels": true,
  "fillWhenVisible": true,
  "scanFrames": true,
  "skipEmptyValues": true,
  "sweepHidden": true,
  "fields": [
    {
      "key": "first_name",
      "selectors": [
        "input[formcontrolname=\"firstName\"]"
      ],
      "labels": [
        "الاسم",
        "الا سم",
        "الإسم",
        "الاسم الأول",
        "الاسم الثلاثي",
        "الأسم",
        "ال اسم",
        "الاسـم",
        "الاس",
        "لاسم",
        "لسم",
        "الاسم الاول",
        "الاسم ثلاثي"
      ],
      "ensure": []
    },
    {
      "key": "father_name",
      "selectors": [
        "input[formcontrolname=\"middleName\"]"
      ],
      "labels": [
        "اسم الاب",
        "إسم الأب",
        "اسم الأب",
        "اسم الإب",
        "اسم الألب",
        "اسم الآب",
        "اسم الالت",
        "اسم الا ب"
      ],
      "ensure": []
    },
    {
      "key": "family_name",
      "selectors": [
        "input[formcontrolname=\"lastName\"]"
      ],
      "labels": [
        "النسبة",
        "الشهرة",
        "الكنية",
        "النسبه",
        "النبسه",
        "النسبـة",
        "النسـبة",
        "لنسبة",
        "الشهره",
        "الشعره",
        "الكنيه"
      ],
      "ensure": []
    },
    {
      "key": "mother_name",
      "selectors": [
        "input[formcontrolname=\"motherName\"]"
      ],
      "labels": [
        "اسم الام ونسبتها",
        "إسم الام",
        "اسم الام",
        "اسم ونسبة الأم",
        "اسم ونسبة الام",
        "اسم و نسبة الأم",
        "اسم و نسبة الام"
      ],
      "ensure": []
    },
    {
      "key": "mother_family_name",
      "selectors": [
        "input[formcontrolname=\"motherLastName\"]"
      ],
      "labels": [
        "نسبة الام",
        "نسبة الأم"
      ],
      "ensure": []
    },
    {
      "key": "birth_date",
      "selectors": [
        "input[formcontrolname=\"birthDate\"]"
      ],
      "labels": [
        "تاريخ الولادة",
        "محل وتاريخ الولادة",
        "محل و تاريخ الولادة",
        "تاريخ الميلاد",
        "بتاريخ الولادة",
        "تاريخ الولاده",
        "تاريخ الميالد",
        "محل وتاريخ الولاده",
        "محل و تاريخ الولاده",
        "محل وتاريخ الولا ده",
        "تاريخ الميلاده",
        "ب تاريخ الولادة"
      ],
      "ensure": []
    },
    {
      "key": "amanah",
      "selectors": [
        "input[formcontrolname=\"registry\"]"
      ],
      "labels": [
        "الامانة",
        "الأمانة",
        "الأمانه",
        "الامانه",
        "الامانته",
        "الامانـة"
      ],
      "ensure": []
    },
    {
      "key": "registry_number",
      "selectors": [
        "input[formcontrolname=\"record\"]"
      ],
      "labels": [
        "محل ورقم القيد",
        "رقم القيد",
        "محل القيد",
        "القيد",
        "محل و رقم القيد"
      ],
      "ensure": []
    },
    {
      "key": "national_number",
      "selectors": [
        "input[formcontrolname=\"cardNumber\"]",
        "input[id^=\"identityCards.0.cardNumber\"]"
      ],
      "labels": [
        "الرقم الوطني",
        "رقم وطني",
        "الرقم اليوطني"
      ],
      "ensure": [
        "button[mattooltip=\"إضافة بطاقة جديدة\"]"
      ]
    },
    {
      "key": "card_name",
      "value": "هوية",
      "selectors": [
        "mat-select[formcontrolname=\"cardName\"]"
      ],
      "labels": [
        "نوع البطاقة",
        "هوية",
        "قيد مدني",
        "سجل مدني"
      ],
      "ensure": [
        "button[mattooltip=\"إضافة بطاقة جديدة\"]"
      ],
      "valueByDocumentType": {
        "national_id": "هوية",
        "civil_registry": "قيد مدني"
      }
    },
    {
      "key": "card_issuer",
      "value": "نفوس",
      "selectors": [
        "mat-select[formcontrolname=\"cardIssuer\"]"
      ],
      "labels": [
        "جهة الإصدار",
        "نفوس"
      ],
      "ensure": [
        "button[mattooltip=\"إضافة بطاقة جديدة\"]"
      ]
    }
  ]
};
})(typeof self !== 'undefined' ? self : this);
