# ACIT OCR — المرحلة الثانية

مشروع محلي بواجهات داخلية 1.1. لا نموذج مدرّب ولا صيغة تسليم رسمية هنا.
نُفذ المسار المصطنع والاختبارات، وأُعدت manifests ومراجعة محلية من سجل التدقيق.

## البيئة الحالية

مفسر المشروع `.venv/Scripts/python.exe`: Python 3.12.14، NumPy 2.3.5، Pillow
12.3.0. أنشئت venv محلية بـ`--without-pip --system-site-packages` بعد تعذر
ensurepip؛ تستعير الحزم المثبتة في runtime التدقيق للقراءة فقط، دون تعديله.
هذه ليست بيئة تدريب مستقلة مكتملة ولا دليل تشغيل GPU. على جهاز آخر يلزم
إنشاء بيئة مستقلة مع نسخ requirements.txt؛ ذلك الجهاز لم يُختبر بعد.

## أوامر نُفذت بنجاح — PowerShell من جذر المشروع

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe -m src.cli --help
.\.venv\Scripts\python.exe -m src.cli demo --out work/demo_new
```

أمر demo نفذ فعليًا باسم `work/phase2_demo_final`؛ استخدم مسارًا جديدًا عند
الإعادة، إذ يرفض استبدال مجلد غير فارغ. ينتج صور JPEG مصطنعة، XML مصطنعًا،
manifest للـGT وآخر للصور فقط، predictions.jsonl وinternal_export.jsonl،
metrics.json وrun_metadata.json. MockDetector يكتشف مستطيلًا أحمر من البكسلات،
لا يقرأ labels. TP=2 وFP=FN=0 في هذه الأمثلة تحقق توصيل فقط، وليس أداء نموذج.

الأوامر التالية نُفذت على `work/phase2_demo_jpeg` (أو demo_final للتقييم):

```powershell
.\.venv\Scripts\python.exe -m src.cli predict --data-root work/phase2_demo_jpeg/data --manifest work/phase2_demo_jpeg/data/images_manifest.jsonl --out work/phase2_demo_jpeg/predict_cli.jsonl
.\.venv\Scripts\python.exe -m src.cli validate --data-root work/phase2_demo_jpeg/data --manifest work/phase2_demo_jpeg/data/manifest.jsonl --level word --out work/phase2_demo_jpeg/validation.json
.\.venv\Scripts\python.exe -m src.cli evaluate --data-root work/phase2_demo_final/data --manifest work/phase2_demo_final/data/manifest.jsonl --predictions work/phase2_demo_final/predictions.jsonl --level word --split-id synthetic_v1 --coordinate-policy-id continuous_zero_based_v1 --iou-threshold 0.5 --out work/phase2_demo_final/metrics_cli.json
.\.venv\Scripts\python.exe -m src.cli export-internal --predictions work/phase2_demo_jpeg/predict_cli.jsonl --manifest work/phase2_demo_jpeg/data/images_manifest.jsonl --out work/phase2_demo_jpeg/export_cli.jsonl
.\.venv\Scripts\python.exe -m src.cli split --manifest work/phase2_demo_jpeg/data/manifest.jsonl --out work/phase2_demo_jpeg/split.json
```

## البيانات الفعلية — محلي فقط

```powershell
$ArchivePath = Read-Host 'المسار الكامل للأرشيف المحلي'
.\.venv\Scripts\python.exe tools/phase2_prepare.py --archive $ArchivePath
.\.venv\Scripts\python.exe tools/verify_phase2.py --archive $ArchivePath
.\.venv\Scripts\python.exe -m src.cli split --manifest reports/private/phase2/eligible_word_train_pool.jsonl --out reports/private/phase2/split_cli_verified.json
```

نُفذت أداتا prepare/verify على الأرشيف المقدم. إعادة prepare ليست ضرورية
للتشغيل المصطنع؛ تقرأ 6156 زوج XML/YOLO لفحص علاقة أسماء الفئات بالأرقام
وسجلات التدقيق لبقية الحصر، وتفك صور عينة المراجعة فقط. لا تعيد تدقيق الأرشيف
كاملًا أو حساب بصمته. المسار الكامل قيمة محلية، لا يُثبت في المصدر.

تحت reports/private/phase2: manifest_word.jsonl وmanifest_line.jsonl، خريطة
الأسماء الفعلية، issues_private.json، split_word_provisional.json، ثم
eligible_word_train_pool.jsonl وverification.json من verify. كل منها خاص.
المسبح المؤهل المقترح 2436 صورة من train، بعد حجز ست حالات؛ تقسيمه 2071/365.
636 test خارج التدريب والتحقق واختيار العتبات؛ الأهلية هنا فحص جودة مقترح،
ولا تمنح إذن تدريب أو تثبت اعتماد إصدار البيانات.

افتح `reports/private/visual_review/index.html` محليًا لبدء المراجعة البشرية.
القائمة الحالية 40 train و5 test لأغراض الجودة فقط، لكل صورة word وline،
أي 90 overlay. احتفظنا بصور overlay من محاولات اختيار أقدم أيضًا؛ يعرض
index وCSV الاختيار الحالي فقط. review_decisions.csv يحوي reviewer فارغًا
وstatus=pending_human_review. لا يعتبر توليد الصور مراجعة. الإنسان يسجل
اسمه والمستوى والقرار والسبب وcorrection_version؛ لا تطبق الأداة تصحيحات.

## الواجهات والقيود

راجع docs/CONTRACTS.md وOWNERSHIP.md وDECISIONS.md ومخطط Prediction.
إعدادات configs توثق القيم الحالية؛ CLI يأخذ خيارات صريحة ولا يحمل YAML
تلقائيًا. eval_local_v0 مؤقت: bbox envelope، IoU=.5، مطابقة واحد لواحد حسب
الثقة، الاحتفاظ بـtruncated، رفض difficult جديد. لا evaluator رسمي أو
AP/ROC أو training CLI. export-internal ليس تسليم المسابقة، وexport_official
يرفض صراحة حتى وصول المواصفة.

لم تثبت معاني فئات script أو خريطة YOLO العالمية؛ توجد أرقام 15/16 في
Line-Level. لا rescale لملف الأبعاد المختلف أو حذف للفئة النادرة، ولا حسم
لـVOC pixel edge convention. تنقل الحالات والتفاصيل فقط ضمن مساحة الفريق
المصرح بها؛ Git ignore يحجب البيانات والمراجعة وmanifests والأوزان والبيئة.

المخرجات الثلاثة لهذه الجولة في reports/shareable، مع نسخة مطابقة في outputs.
التقارير الأربعة وحزمة المرحلة الأولى محفوظة، ولم يعاد إنشاؤها بهذه الجولة.
