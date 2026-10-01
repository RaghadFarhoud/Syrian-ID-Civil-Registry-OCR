# ID / Civil Registry Extraction — REST API

خدمة استخراج بيانات الهوية والسجل المدني من الصور — **تعمل بالكامل بدون إنترنت**.

---

# 📦 تسليم المشروع للعميل (بلا إنترنت)

هذه هي طريقة التسليم المعتمدة: **المشروع يُسلَّم وفيه كل المكتبات والموديلات**،
والعميل لا يحتاج إنترنت إطلاقاً — لا لتحميل Python، ولا للمكتبات، ولا للموديلات.

## 1. المتطلب الوحيد: Python

| | |
|---|---|
| **الإصدار** | **Python 3.13.2 — نسخة 64-bit (x64)** |
| **التحميل** | `python-3.13.2-amd64.exe` من [python.org](https://www.python.org/downloads/release/python-3132/) |
| **مهم أثناء التثبيت** | ضع علامة على **«Add python.exe to PATH»** (أسفل يمين النافذة الأولى) |

- إن كان جهاز العميل **بدون إنترنت** أصلاً: ضع ملف التثبيت `python-3.13.2-amd64.exe`
  داخل مجلد `installers/` بالمشروع (سيتعرف عليه `install-offline.bat` ويثبّته وحده).
- إن كان جهاز العميل فيه إنترنت: أرسل له **رقم الإصدار فقط** وروابط التنزيل.
- **لا يكفي أي إصدار آخر.** بيئة المشروع (المجلد `venv/`) مبنية على 3.13،
  وأي نسخة مختلفة (3.11 / 3.12 / 3.14) ستكسر المكتبات ذات الكود الثنائي (native binaries).
- **64-bit فقط** — نسخة 32-bit لن تعمل.

## 2. الملفات التي تُرسَل (قائمة كاملة)

هذا كل شيء. لا شيء غيره مطلوب.

| الملف/المجلد | الحجم | لماذا؟ |
|---|---|---|
| `venv\` | **3.66 GB** | **كل المكتبات مثبّتة** (FastAPI, PaddleOCR, PaddlePaddle-GPU, OpenCV…) — هذا هو «البرامج كلها» |
| `tesseract\` | 121 MB | نسخة محمولة من Tesseract (عربي + إنجليزي + OSD) — لا يحتاج تثبيت |
| `models\` | 19 MB | موديلات الذكاء الاصطناعي الثلاثة (كشف النص + قراءة العربي + اتجاه السطر) |
| `core\`, `pipelines\` | 48 KB | كود المعالجة والاستخراج |
| `api.py`, `main.py` | 9 KB | نقطة التشغيل (السيرفر) |
| `static\` | 96 KB | صفحة الاستخدام العربية + صفحة تجريبية |
| `extension\` | 100 KB | إضافة Chrome لنقل البيانات لموقع العميل |
| `start.bat` | 1 KB | **زر التشغيل** — انقر نقراً مزدوجاً |
| `install-offline.bat` + `install-offline.ps1` | 11 KB | اختياري: فحوصات وتثبيت Python تلقائياً — `start.bat` يعمل بدونه |
| `run.ps1` | 5 KB | منطق التشغيل الداخلي (يستدعيه `start.bat`) |
| `requirements.txt`, `README.md` | 21 KB | مرجع فقط (غير مستخدمين على جهاز العميل) |
| `installers\` | 0 | اختياري: ضع `python-3.13.2-amd64.exe` هنا لو جهاز العميل بدون إنترنت |
| **المجموع** | **≈ 3.8 GB** | مضغوط (zip) يصير حوالي **1.8 GB** |

> **لا ترسل** ما يلي: `scripts\` و`setup.ps1` و`setup.sh` و`Makefile` و`Dockerfile`
> (أدوات المطور مع الإنترنت) — أو أرسلها، ما بتضر، بس ما بتلزم العميل.
> ملفات مثل `card.html` و`step 1.html` و`client website.html` هي **نسخ محفوظة من موقع العميل**
> للرجوع إليها فقط، وتحتوي روابط LAN — احذفها من نسخة التسليم لأنها غير مستعملة.

### كيف تبني نسخة التسليم (على جهازك أنت — مرة واحدة)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\export_offline_bundle.ps1 -Zip
```

السكربت يعمل الخطوات التالية تلقائياً:

1. يتحقق أن `venv\` فيه كل المكتبات (وأن PaddlePaddle مثبّت).
2. ينظّف الملفات الزائدة: مجلد `~addle` الميت (306 MB)، ومجلدات `__pycache__`، وملفات `.log`، ومجلد `.cache` داخل الموديلات.
3. يتحقق من الموديلات الثلاثة (وينزّلها **على جهازك** إن كانت ناقصة).
4. ينسخ نسخة Tesseract المحمولة إلى `tesseract\` (عربي + إنجليزي + OSD فقط).
5. يطبع لك **قائمة الملفات وأحجامها** ونسخة Python المطلوبة.
6. مع `-Zip` يبني `ID-Extraction-Offline.zip`.

> **مهم —Git:** `venv/` و`models/` و`wheels/` و`tesseract/` موجودة في `.gitignore`.
> فإذا بعت المشروع عبر Git لن تصلك هذه المجلدات! إمّا **zip** (الطريقة الصحيحة للعميل)،
> أو `git add -f venv models tesseract`.

> **طريقة الإرسال:** USB / قرص خارجي / Shared folder. **لا Gmail ولا أي إيميل**
> (الملف 1.8 GB والرفع يفشل)، ولا رابط تنزيل إنترنت — العميل بدون إنترنت.

## 3. خطوات العميل (٣ خطوات)

1. **ثبّت Python 3.13.2 (64-bit)** مرة واحدة إن لم يكن موجوداً
   إن كان جهاز العميل بدون إنترنت، شغّل **`install-offline.bat`** أولاً — هو يثبّت Python
   تلقائياً من `installers\` ويعيد تجهيز كل شيء.
2. **فكّ ضغط المشروع** في مجلد عادي (مثلاً `C:\ID-Extraction`) — لا يشترط مسار معيّن،
   ينفع على أي قرص، وحتى داخل مجلد فيه مسافات بالعربي.
3. **انقر نقراً مزدوجاً على `start.bat`** — وهذا هو كل ما على العميل فعله.

مثال مُخرَج `install-offline.bat` (اختياري):

```
      Repointing the environment to: C:\Users\...\Python313
[ OK ] Python 3.13 found at C:\Users\...\Python313\python.exe
      PaddlePaddle 3.3.1, CUDA available: cuda=True
[ OK ] GPU build active (paddlepaddle-gpu, CUDA 12.6 bundled - no CUDA install needed)
[ OK ] All 3 models present
[ OK ] Portable copy found: C:\ID-Extraction\tesseract\tesseract.exe
[ OK ] Paddle/HuggingFace forced offline for this Windows account
```

من هذه اللحظة: **افصل النت/امنعه بالكامل** — البرنامج يعمل بنفسه.

### التشغيل اليومي (كل مرة)

انقر نقراً مزدوجاً على **`start.bat`** في كل مرة — هذا هو كل ما على العميل.
يفتح المتصفح تلقائياً على `http://localhost:8000/` — اختر نوع المستند،
ارفع الصورة، واضغط **«استخراج البيانات»**.

> **مهم — لا يحتاج `install-offline.bat` أصلاً.** `start.bat` يعمل وحده،
> ويكفيه أن يكون Python 3.13.2 (64-bit) مثبّتاً على الجهاز. شغّل `install-offline.bat`
> مرة واحدة فقط إن أردت **فحصاً كاملاً قبل التشغيل** (تثبيت Python تلقائي +
> طباعة حالة كل المكوّنات: الموديلات، Tesseract، كرت الشاشة)، ولتفعيل إعدادات
> عدم الاتصال **دائماً** على مستوى حساب ويندوز كله (لا لعملية السيرفر وحدها).

> **مدة التشغيل:** المرة الأولى على جهاز جديد قد تستغرق **دقيقة إلى ثلاث دقائق**
> (ويندوز يجهّز ملفات المكتبات أول مرة). بعدها 20–40 ثانية.
> **لا تُغلق النافذة** ولا تظنّ أن البرنامج علّق — انتظر.

### ماذا يفعل `install-offline.bat` بالضبط؟

> هذه مرحلة «تأمين الإعداد» وهي **اختيارية**. إن شغّلت `start.bat` مباشرة،
> تجري نفس هذه التجهيزات تلقائياً أثناء التشغيل — **لا يُشترط**.
> أشغّلها إن أردت **التحقق قبل التشغيل**، أو لتثبيت إعدادات عدم الاتصال
> على مستوى حساب ويندوز كله.

> **وماذا يفعل `start.bat` تلقائياً عند الحاجة؟** إذا كان مسار Python المخزّن
> في `venv\pyvenv.cfg` لا ينطبق على جهاز العميل، يبحث عن Python 3.13 (64-bit)
> ويصحّح المسار بنفسه ثم يكمل التشغيل. لهذا ينتقل المشروع بين أي جهازين
> دون أن ينكسر، وحتى مع وجود المسار خاطئاً من الأصل.

| الخطوة | التفصيل |
|---|---|
| يبحث عن Python 3.13 | على جهاز العميل، وإن لم يجده يثبّته من `installers\` |
| **يصلح `venv\pyvenv.cfg`** | المجلد `venv` يتذكر مسار Python *بالحروف* الذي بُني عليه (كان `C:\Python313`)، فيعيد كتابته ليصير مسار جهاز العميل — **لذلك ينتقل المشروع بين الأجهزة بدون ما ينكسر** |
| يفحص كل المكتبات | يمنع تشغيل ناقص برسالة واضحة |
| يفحص الموديلات الثلاثة | نفس الشيء |
| يربط Tesseract المحمول | أو يثبّت برنامج التثبيت المرفق إن وُجد |
| يفعّل وضع عدم الاتصال | `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=1` + `HF_HUB_OFFLINE=1` + `TRANSFORMERS_OFFLINE=1` |

## 4. إثبات أن البرنامج فعلاً بلا إنترنت ✅

بعد تثبيت Python 3.13.2 (أو بعد `install-offline.bat`):
1. **افصل كابل النت** (أو عطّل محول الشبكة Network Adapter من إعدادات ويندوز).
2. انقر `start.bat` — المرة الأولى على جهاز جديد قد تأخذ 1–3 دقائق،
   وبعدها 30–60 ثانية.
3. جرّب استخراج صورة حقيقية.

وبدون تشغيل `install-offline.bat` أيضاً يعمل السيرفر: `start.bat` يضع المتغيرات
نفسها (`HF_HUB_OFFLINE` و`TRANSFORMERS_OFFLINE` و`PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK`)
في **عملية السيرفر نفسه**، فيكفي هذا. أما `install-offline.bat` فيضيفها **دائماً**
لحساب ويندوز، فتُستثنى حتى عمليات Python الأخرى على الجهاز.

**ما لا يجب أن تراه أبداً** في النافذة السوداء:

| رسالة | معناها |
|---|---|
| `Checking connectivity to the model hosters` | ⚠️ يحاول إنترنت — بلّغني فوراً |
| `the model files will be automatically downloaded` | ⚠️ يحاول ينزّل موديل — بلّغني |
| `Downloading AI models` / `Installing required packages` | ⚠️ تجاوز الإعداد |

**المتوقّع أن تراه فقط:**

```
Step 1/3: Checking the bundled Python environment
Step 2/3: Checking the packages
      All packages present - PaddlePaddle runtime: GPU (CUDA 12.6)
Step 3/3: Checking the AI models
      All 3 models present - no download needed
[PaddleOCR] using device: gpu:0
INFO api: OCR engine loaded in 5.39s (device=gpu:0)
Uvicorn running on http://0.0.0.0:8000
```

## 5. معلومات كرت الشاشة (GPU)

- النسخة المرسلة فيها **PaddlePaddle-GPU 3.3.1 مع مكتبات CUDA 12.6 كلها بداخلها** —
  **لا يحتاج العميل تثبيت CUDA ولا PyTorch ولا شيء.**
- **الشرط الوحيد:** تعريف كرت **Nvidia** (Driver) محدّث يدعم CUDA 12.
  افحصه بتشغيل `nvidia-smi` في موجه الأوامر.
- إن لم يوجد كرت Nvidia أو كان التعريف قديماً: البرنامج **يعمل عادي على المعالج (CPU)** تلقائياً
  بدون أي تعديل — والنتيجة نفسها، فقط الطلب يطلب ~5–10 ثوانٍ بدل ~1–2 ثانية.
- إن أردت نسخة **CPU فقط** (أخفّ بحوالي 2 GB): على جهازك `pip uninstall -y paddlepaddle-gpu && pip install paddlepaddle==3.3.1`
  ثم أعد تشغيل `export_offline_bundle.ps1`.

## 6. حل المشاكل

| ما تراه | السبب | الحل |
|---|---|---|
| `The 'venv' folder is missing` | نُسخ المشروع بدون `venv\` (حجمه 3.66 GB — بعض برامج النسخ تتخطاه) | انسخ المجلد كاملاً، أو أرسل الـzip |
| `did not find executable at ...\python.exe` | Python 3.13 غير مثبّت على جهاز العميل | ثبّت 3.13.2 (64-bit)، أو ضع `installers\python-3.13.2-amd64.exe` وأعد `install-offline.bat` |
| `Incomplete AI models` | `models\` ناقصة | أعد إرسال مجلد `models` كاملاً (19 MB) |
| `Portable Tesseract not found` | مجلد `tesseract\` ناقص | أعد إرسال المجلد (121 MB)، أو ثبّت Tesseract مع لغتي **ara + eng** |
| الصفحة تفتح لكن الاستخراج يعطي `500` | Tesseract غير موجود | تحقق من وجود `tesseract\tesseract.exe` |
| البرنامج بطيء جداً | يعمل على CPU | حدّث تعريف كرت Nvidia |
| النافذة لا تفتح المتصفح ويبدو أن البرنامج علّق | المرة الأولى: ويندوز يجهّز ملفات المكتبات | انتظر 1–3 دقائق (تظهر لك رسالة `the first time on a new machine this can take 1-3 minutes`) ولا تغلق النافذة |
| `TesseractNotFoundError` | مسار Tesseract | حدّده يدوياً: `setx TESSERACT_CMD "D:\...\tesseract.exe"` ثم أعد تشغيل الجهاز |

## 7. ماذا تغيّر في الكود لضمان عدم الاتصال؟

| الملف | التغيير |
|---|---|
| `run.ps1` | **حُذف** منه كل تنزيل: `winget` (تثبيت Python)، `pip install`، وتحميل الموديلات. صار يفحص فقط ويعطي رسالة واضحة عند النقص، **ويصحّح مسار Python تلقائياً** عند أول تشغيل على جهاز جديد، ويشغّل `python.exe -m uvicorn` (وليس `uvicorn.exe` — لأن ملفات `.exe` فيها مسار جهاز المطور مخبوز داخلها). |
| `core/ocr_engine.py` | يفعّل `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=1` و`HF_HUB_OFFLINE=1` و`TRANSFORMERS_OFFLINE=1` قبل تحميل PaddleOCR. |
| `main.py` | مسار `models\` صار **مطلقاً** (لا يعتمد على مجلد العمل) + رسالة خطأ واضحة بدل `FileNotFoundError` من PaddleX. |
| `core/preprocessing.py` | بحث Tesseract بقائمة أولويات: `TESSERACT_CMD` ← `tesseract/` المحمول ← المسار القياسي ← PATH. ودالة `correct_rotation` لا تُسقط البرنامج إذا لم يجد Tesseract. |
| `install-offline.ps1` / `.bat` | جديد — تهيئة جهاز العميل بدون إنترنت. |
| `scripts/export_offline_bundle.ps1` | جديد — بناء نسخة التسليم. |
| `static/*.html` | لا يوجد أي CDN خارجي (خطوط/JS/CSS كلها inline) — يعملان بدون إنترنت كما هما. |
| `extension/*` | كل الاتصال بـ `http://localhost:8000` فقط (loopback). |

---

# 🖥️ التشغيل السريع (بعد التثبيت)

1. افتح المجلد و**انقر نقراً مزدوجاً على `start.bat`**.
2. ينفتح المتصفح تلقائياً على `http://localhost:8000/`.
3. اختر نوع المستند، ارفع الصورة/الصور، واضغط **«استخراج البيانات»**.

> لا يوجد أي تحميل عند التشغيل: لا موديلات (~1.5 GB ولا شيء)، لا مكتبات.
> أول طلب بعد التشغيل أبطأ قليلاً لأنه يسخّن الموديل.

### إيقاف البرنامج
أغلق النافذة السوداء (أو اضغط `Ctrl+C`).

### قياس زمن كل طلب (GPU مقابل CPU)

- كل طلب يطبع في نافذة السيرفر سطر مثل:
  `REQUEST done: document_type=national_id engine=paddle device=gpu:0 elapsed=1.23s`
- الرد JSON يتضمن `elapsed_seconds` و `engine_device` لسهولة المقارنة.

---

# 🛠️ الإعداد للمطورين (يحتاج إنترنت — على جهازك أنت فقط)

> ⚠️ هذا القسم **للمطور فقط**. جهاز العميل لا يحتاجه ولا ينفّذه.

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   # أول مرة بس
.\setup.ps1
```

ثم:

```powershell
.\venv\Scripts\Activate.ps1
uvicorn api:app --host 0.0.0.0 --port 8000
```

على لينكس/ماك:

```bash
./setup.sh
source venv/bin/activate
uvicorn api:app --host 0.0.0.0 --port 8000
```

`setup.ps1` / `setup.sh` يكتشفان كرت Nvidia تلقائياً: يثبّتان `paddlepaddle-gpu` (CUDA 12.6)،
وإلا `paddlepaddle` (CPU). ولا ينزّلان الموديلات إلا عبر
`scripts/download_paddle_models.py` (اللي بينسخ الموديلات من الكاش إلى `models\`) —
و`run.ps1`/`setup.ps1` يتخطّاه إذا الموديلات موجودة.

> **Tesseract** (اختياري للمطوّر): يُثبَّت من [هون](https://github.com/UB-Mannheim/tesseract/wiki)
> مع العربية، أو انسخه محلياً إلى `tesseract\` (المشروع يكتشفه تلقائياً).
> مطلوب فعلياً في مسار الاستخراج: تصحيح دوران الصورة + قراءة بعض الأرقام.
> يُستخدم فقط كمحرك OCR بديل إذا اخترت `engine=tesseract` بدل `paddle`.

---

# 🔌 الواجهة البرمجية (REST API)

- **صفحة الاستخدام السهلة:** `http://localhost:8000/`
- **توثيق Swagger:** `http://localhost:8000/docs`
- **فحص الجاهزية:** `http://localhost:8000/health`

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
JSON يحتوي على المعلومات المطلوبة من الهوية أو القيد المدني

---

# 🔁 ناقل البيانات إلى موقع الإدخال (إضافة ID Relay)

تُستخدم لتسريع عمل موظفي إدخال البيانات: بعد الاستخراج تصير البيانات جاهزة
للنقل إلى نموذج موقع إدخال آخر مفتوح في تاب مختلف.

### الخطوات

1. **تعديل الإعدادات** — انسخ `extension/.env.example` إلى `extension/.env`
   وعبّأ القيم الخاصة بالموقع الحقيقي (عنوان التاب، سيليكتورات الحقول).
2. **توليد الإعداد** — شغّل:
   ```powershell
   python extension\build_config.py
   ```
3. **تركيب الإضافة** — افتح `chrome://extensions`، فعّل «وضع المطوّر» (Developer mode)،
   ثم «تحميل غير مضغوطة» (Load unpacked) واختر مجلد `extension`.
4. في صفحة التطبيق: ارفع المستند → «استخراج البيانات» → **«نقل البيانات إلى صفحة الإدخال ⇦»**.

> الإضافة تملأ الحقول وتنقل التركيز إلى تاب الموقع فقط. لا تضغط أي أزرار حفظ/إرسال
> أبداً (إعداد `RELAY_FILL_ONLY=1`).

### تجهيز بطاقة الهوية

قبل الرقم الوطني، الإضافة تضبط قائمة «نوع البطاقة» و«جهة الإصدار» حسب نوع المستند المستخرج:

| نوع المستند | نوع البطاقة | جهة الإصدار |
|---|---|---|
| `national_id` (بطاقة هوية) | هوية | نفوس |
| `civil_registry` (سجل مدني) | قيد مدني | نفوس |

تُعدَّل من `extension/.env`:

```ini
FIXED_VALUE_BY_DOCTYPE_card_name=national_id=هوية,civil_registry=قيد مدني
FIXED_VALUE_card_issuer=نفوس
```

- `FIXED_VALUE_BY_DOCTYPE_*` يقبل أي نوع مستند ترسله نقطة `/extract`، وتُطبَّق مقارنةً
  بعد توحيد الشكل (`national-id` = `national_id`، `بطاقة هوية` = `national_id` …).
- `FIXED_VALUE_*` هي القيمة الاحتياطية عند غياب النوع أو عدم معرفته.
- إن لم توجد القيمة المطلوبة في قائمة الموقع، تُبلَّغ النتيجة بالعناصر المتاحة بدل الفشل الصامت.
- زر «نسخ البيانات» يعمل كبديل يدوي إذا لم تكن الإضافة مثبتة.
- صفّ `static/client-test.html` يحاكي موقع العميل بأربع خطوات (بديل `demo-target.html`).
- كل الحقول غير المدرجة في الخريطة تُتجاهل نهائياً — لا يُدخل الناقل أي شيء إضافي.

## دليل التهيئة (أسئلة توجّه للعميل)

| # | السؤال | متى نحتاجه |
|---|---|---|
| 1 | عنوان موقع الإدخال الدقيق (URL) | ضروري لملء `RELAY_TARGET_TAB_PREFIX` |
| 2 | لقطة شاشة للنموذج + أسماء/معرّفات الحقول، أو نتائج «Inspect» لحقلين | لكتابة السليكتورات |
| 3 | نظير كل حقل من حقولنا (الاسم، اسم الأب، …) في نموذجهم | لخريطة الحقول |
| 4 | هل النموذج HTML عادي أم React/Angular (SPA)؟ | خياري (الناقل يدعم الاثنين) |
| 5 | نموذج بخطوة واحدة أم معالج بأكثر من خطوة/iframe؟ | افحص بنفسك عند الموقع |
| 6 | أي متصفح وعلى أي نظام؟ (متوقع: Chrome على Windows) | توزيع الإضافة |
| 7 | هل التاب مفتوح مسبقاً أم نفتحه نحن؟ | إعداد `RELAY_OPEN_TAB_IF_MISSING` |
