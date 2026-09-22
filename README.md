# ID / Civil Registry Extraction — REST API

خدمة استخراج بيانات الهوية والسجل المدني من الصور

## الإعداد (مرة وحدة لكل جهاز)

```powershell
git clone <[Repo link](https://github.com/RaghadFarhoud/Syrian-ID-Civil-Registry-OCR.git)>
cd id-civil_registry-extraction
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   # أول مرة بس
.\setup.ps1
```

`setup.ps1` بيشتغل تلقائياً: بيئة افتراضية (venv)، تثبيت كل المكتبات (paddleocr وباقي المتطلبات)، وتنزيل موديلات paddle لمرة وحدة

> **Tesseract** لازم ينثبت يدوياً من [هون](https://github.com/UB-Mannheim/tesseract/wiki) (اختر Arabic أثناء التثبيت) — الـ pip ما بيثبته، لأنو برنامج خارجي مو مكتبة بايثون.

## التشغيل

```powershell
.\venv\Scripts\Activate.ps1
uvicorn api:app --host 0.0.0.0 --port 8000
```

بعد التشغيل، جاهز على: `http://localhost:8000/docs`

## استخدام الـ API

**Endpoint:** `POST /extract`
**Content-Type:** `multipart/form-data`

| الحقل | القيمة |
|---|---|
| `document_type` | `national_id` (بيحتاج صورتين: أمامية+خلفية) أو `civil_registry` (صورة وحدة) |
| `engine` | `paddle` (افتراضي) أو `tesseract` |
| `files` | ملف/ملفات الصور |

### مثال (curl)
```bash
curl -X POST http://localhost:8000/extract \
  -F "document_type=national_id" \
  -F "files=@front.jpg" \
  -F "files=@back.jpg"
```

### الرد
 JSON 
بيحتوي على المعلومات المطلوبة من الهوية أو القيد المدني
