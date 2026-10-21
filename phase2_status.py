"""Build the three shareable phase 2 deliverables without raw data."""
import hashlib
import json
from pathlib import Path
import re
import shutil

root=Path(__file__).resolve().parents[1];share=root/'reports/shareable';private=root/'reports/private/phase2'
classes=json.loads((share/'class_mapping_summary.json').read_text(encoding='utf8'))
issues=json.loads((share/'issue_resolution_summary.json').read_text(encoding='utf8'))
verification=json.loads((private/'verification.json').read_text(encoding='utf8'))
testlog=(root/'work/phase2_tests.log').read_text(encoding='utf-8-sig')
match=re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK',testlog)
if not match:raise RuntimeError('Successful test log required')
table='\n'.join(f"| {r['annotation_level']} | {r['source_split']} | {r['regions']} |" for r in classes['split_region_totals'])
problem_table='\n'.join(f"| {r['issue']} | {r['source_split']} | {r['annotation_level']} | {r['affected_annotation_files']} | {r['status']} |" for r in issues['issues'])
sp=issues['provisional_split'];review=issues['review_preparation']
status=f'''# حالة المرحلة الثانية — 19 أكتوبر 2026

## النتيجة

أُنشئ مشروع محلي فعلي بعقد داخلي 1.1 وقارئ XML/YOLO وvalidators وCLI
وتحويلات إحداثيات وeval_local_v0 ومسار مصطنع كامل. نجح {match[1]} اختبارًا
في {match[2]} ثانية في آخر تشغيل، ثم تحقق مستقل من manifests والتقسيم
والحالات الفعلية. لا تدريب ولا أوزان نموذج ولا تقييم رسمي أو أداء نموذج مقاس.

حُفظت البيانات الأصلية دون تعديل أو استخراج شامل. التقارير الأربعة وحزمة
المرحلة الأولى محفوظة؛ أضيفت هذه التقارير الثلاثة فقط. لم يُنشأ Git/remote
أو PR ولم يُنشر شيء. فحص git أكد أن المجلد ليس مستودعًا، ولم يوجد AGENTS.md
في المشروع أو أسلافه المحددين.

## ما نُفذ

- docs/CONTRACTS.md وOWNERSHIP.md وDECISIONS.md ومخطط prediction.schema.json.
- src/contracts.py: polygon/score/ID/dimension validators وسجلات JSONL ذرية.
- src/data/: قارئ directory/ZIP للقراءة فقط، XML وYOLO، اختيار word/line صريح،
  ربط split/stem لا XML filename/path، كشف الأبعاد والأسماء والحالات الفارغة،
  حفظ raw_bbox وsource dimensions والأعلام، ومنع test من train/validation.
- src/models/: Detector protocol وMockDetector للمستطيلات الحمراء المصطنعة،
  وResizePad للعكس دون clipping أو تبديل x/y. src/training نطاق محجوز موثق،
  ولا دالة تدريب وهمية أو تثبيت framework.
- src/evaluation/: eval_local_v0 المؤقت؛ src/submission/: تصدير داخلي حتمي
  وofficial exporter يرفض حتى وصول المواصفة.
- CLI فعلي: demo وvalidate وpredict وevaluate وsplit وexport-internal.
  التنبؤ يقبل manifest صور بلا labels؛ السجل الفارغ نجاح مستقل عن فشل الصورة.
- configs وrequirements.txt وREADME بأوامر نُفذت فعليًا و.gitignore يحجب
  الصور والlabels وmanifests والمراجعات الخاصة والأوزان والبيئة وoutputs.

## إعادة استخدام التدقيق والقراءات الإضافية

استُخدمت checkpoint.jsonl والبصمات وclass aliases ومشاكل المرحلة الأولى.
لم تُعد قراءة كل الصور أو إعادة حساب SHA-256 للأرشيف. قرئت 6156 زوجًا صغيرًا
من XML/YOLO لتحديد اقتران اسم الفئة بمعرف YOLO بعد التحقق من تطابق ترتيب
المناطق هندسيًا بفارق normalized≤1e-5؛ لم يظهر فشل مقارنة هندسية. هذه قراءة
محددة لسؤال لم تحفظه سجلات المرحلة الأولى لكل منطقة، وليست تدقيق 4GB جديدًا.
فك الصور اقتصر على عينة المراجعة الحالية/تحضيرها، لا 3078 صورة. أعيد تشغيل
التحضير أثناء تطويره، وبقيت بعض overlays القديمة محفوظة محليًا. أعيدت قراءة
خمس حالات metadata محددة للتحقق من كاشف المشاكل بعد الدمج.

البصمة المعاد استخدامها من الجولة الأولى:
`{issues['archive_identity']['sha256_from_phase1']}`.
هي هوية مسجلة سابقة، ولم ندّع إعادة توثيقها ببصمة كاملة في هذه الجولة.

## نتائج البيانات حسب المستوى والتقسيم

| المستوى | التقسيم | المناطق |
|---|---|---:|
{table}

خريطة الفئات المرصودة: CLASS_1 يرتبط بالأرقام 0 و15، CLASS_3 بالأرقام 1 و16،
وCLASS_2 بالرقم 2. المستوى word متسق عدديًا مع 0/1/2؛ في line توجد 8 مناطق
بأرقام 15/16 عبر ستة ملفات: أربعة train واثنان test. ليست هذه موافقة على
معنى الأرقام أو أمرًا لإعادة ترميزها. المعاني وتعريف script والهدف الرسمي
غير موثقة في README، لذا تبقى unresolved وscript=null. الخريطة العامة ليست
واحدًا لواحد، ولا تستخدم أرقام YOLO مباشرة كفئات معيارية.

CLASS_2 في word موجودة مرة واحدة داخل test، ولا تظهر في word/train؛ لا
تحذف أو تنقل للتدريب. الأسماء الحقيقية وخريطة التفاصيل محفوظة محليًا فقط،
والـaliases ثابتة عبر المستويات والتقسيمات. راجع class_mapping_summary.json.

## المشاكل والمراجعة

| المشكلة | التقسيم | المستوى | ملفات التعليق المتأثرة | الحالة |
|---|---|---|---:|---|
{problem_table}

الأعداد بحسب نوع المشكلة/ملف التعليق وليست عدد صور فريدة؛ قد تتداخل.
اختلاف الأبعاد: XML line/train واحد 1630×1200 مقابل صورة1764×1200، لم يُصلح
ولم يطبق scale. أسماء filename غير المطابقة: أربعة XML تخص صورتَي test
على المستويين؛ الربط الصحيح من manifest، والmetadata الأصلية محفوظة. الصورة
الخالية واحدة في train ولها ملفات بلا مناطق على المستويين؛ ليست label مفقودًا،
لكن كونها سلبية صحيحة يحتاج مراجعة بشرية.

اختيار المراجعة الحالي: {review['train_images']} صورة train تشمل كل حالات
train المعروفة، وأطراف كثافة المناطق/الحجم/aspect ratio مع تعبئة عشوائية
seed=2026. أضيفت {review['test_quality_only_images']} صور test للجودة فقط دون
استخدامها للاختيار أو العتبات. word وline منفصلان: {review['current_selection_overlays']}
overlay وسجل CSV. العدد الكلي المحفوظ محليًا، بما يشمل اختيارات قديمة،
{review['total_local_overlay_files_including_retained_previous_selections']}؛ يعرض
index.html وreview_decisions.csv الاختيار الحالي فقط.

كل سجلات المراجعة الحالية pending_human_review؛ reviewer فارغ؛ مراجعات
بشرية مكتملة = {issues['reviewer_completed_records']}. لم تُعرض صور البيانات في
المحادثة أو حزمة مشاركة أو Git. وجود overlays ليس دليل مراجعة إنسان.
لا corrections مطبقة وcorrection_version=null. الملفات الخاصة تحت
reports/private/visual_review وreports/private/phase2.

## التقسيم المقترح

مسبح train المؤهل للجودة مؤقتًا: {sp['eligible_train_pool']} من 2442؛ حُجزت
{sp['excluded_train_images']} صور معروفة المشكلات، بحجز الصورة عبر المستويين
احتياطًا. الناتج {sp['train_images']} train و{sp['val_images']} validation، seed2026،
و636 test خارج المسبح تمامًا. حفظت manifests وtrain_ids وval_ids ونسخة
split والـchecksum؛ تحقق الفصل والاتحاد والحتمية.

الـchecksum للتجزئة المعتمدة للمسبح: `{sp['manifest_sha256']}`؛ طريقة البصمة
هي UTF-8 JSON array بالترتيب المحفوظ وsorted keys وفواصل مضغوطة، وليست
وعدًا بأنها بصمة ملف JSONL بالبايت. لا group IDs مختلقة: هذا تقسيم صور
مؤقت، ولا يدعي خلو تسرب المشاهد/القصاصات. الأهلية ليست موافقة ترخيص أو
اعتماد بيانات أو إذن بدء تدريب. تقسيم validation يحتاج مراجعة الفريق.

## الاختبارات والتشغيل المنفذ

نجح {match[1]} اختبارًا يغطي RGB/رمادي/شفافية، اسمًا عربيًا وامتداد .JPG،
stem مكررًا بين تقسيمات، filename والأبعاد دون تغيير raw_bbox، بيانات خالية
مقابل تالفة، خلط level وtest والـIDs، صحة score/polygon، round-trip غير
متناظر لـresize/padding يميز x/y، TP/FP/FN والتكرار وحد IoU بالضبط وأقل منه،
غياب prediction، difficult جديد، وتصديرًا حتميًا وحالة خروج فشل غير صفرية.

المسار المصطنع نفذ على 3 صور JPEG، إحداها فارغة واسم آخر عربي؛ يعيد سجلًا
لكل صورة. TP=2 وFP=FN=0 نتيجة توصيل لأمثلة مصطنعة مصممة، ليست أداء OCR.
كل metrics تحمل evaluation_status=provisional وprotocol_id=eval_local_v0
وsplit_id وcoordinate_policy_id. IoU=.5 افتراض محلي؛ bbox هو غلاف min/max
للمضلع، مطابقة الثقة تنازليًا واحد لواحد، duplicate FP، جمع العدادات قبل
المقاييس، المقام الصفري=0، truncated محفوظ، difficult غير الصفرية توقف القياس.
لا AP/ROC/confusion matrix أو official=true.

التحقق الفعلي من السجلات: {verification['manifest_rows_validated']} manifest row،
خمس حالات metadata معلومة، 636 test منفصلة، و90 review row معلقة. لا إعادة
فك جميع صور البيانات ضمن هذا التحقق.

أوامر إعادة التشغيل من جذر المشروع، في PowerShell:

```powershell
.\\.venv\\Scripts\\python.exe -m unittest discover -v
.\\.venv\\Scripts\\python.exe -m src.cli demo --out work/demo_new
.\\.venv\\Scripts\\python.exe -m src.cli --help
```

demo نفذ باسم work/phase2_demo_final؛ اختر مجلدًا جديدًا للإعادة. README
يضم أوامر predict/validate/evaluate/export-internal/split المنفذة، وأدوات
phase2_prepare وverify_phase2 التي تأخذ --archive كمسار محلي دون تثبيته
في الكود. التحضير ليس مطلوبًا لإعادة المسار المصطنع. لا train command.

## البيئة والجاهزية

أنشئت .venv للمشروع بمفسر3.12.14 وNumPy2.3.5 وPillow12.3.0. ensurepip تعذر
فاستُخدم --without-pip --system-site-packages للوصول للحزم الموجودة للقراءة
فقط. لم يعدّل runtime المدار أو Python النظام ولم تُثبت أطر تدريب. هذه
بيئة اختبار محلية تستعير الحزم، وليست بيئة تدريب مكتفية أو اختبار GPU؛
لم تُنفذ CUDA tensors ولا قياسات موارد أو اختبار جهاز عضو ثانٍ.

| العضو | الجاهز الآن | ما يلزم تاليًا |
|---|---|---|
| عمرو | العقد وCLI والربط والمصدر والتصدير الداخلي والاختبارات | مراجعة بشرية أخرى، رد المنظمين، مواصفة exporter رسمي وتشغيل جهاز آخر |
| الثاني | loader وmanifests وإحصاءات الفئات والمشاكل وoverlays وتقسيم مؤقت | مراجعة الصور وتسجيل القرارات، تعريف الفئات، تصحيحات بإصدار وتجميع مشاهد موثق |
| الثالث | Detector protocol وMockDetector وinverse transforms | adapter حقيقي، قرار ترخيص/أوزان، بيئة framework وتجربة موارد قصيرة |
| الرابع | backend مؤقت واختبارات مطابقة وحالات محسوبة | مراجعة الافتراضات وwrapper رسمي عند وصوله وتقييم validation فقط لاحقًا |

## غير المحسوم وما لم يُنفذ

المراجعة البصرية معلّقة فعلًا. لم نصحح metadata/labels أو ندمج الفئات أو
نثبت تقسيم مشاهد. يلزم حسم اعتماد SYPHAXAR كنسخة ACIT-C، ودور test،
وتعريف script/class IDs وtarget policy، وVOC edge convention، والمقيّم
والتنسيق الرسمي وignore، وصلاحيات الأوزان والبيانات الخارجية، والتوقيعات
والساعة والمنطقة الزمنية. خطة المرحلة الثانية تنقل سياقًا عن الاتفاقية،
لكن ملف DOCX محلي لم يقدم بهذه الجولة ولم نتحقق من نصه استقلالًا.

لم يبدأ تدريب طويل أو قصير، ولم يُنزّل نموذج، ولم ينفذ benchmark حقيقي.
نجاح الجولة يثبت اتصال الأجزاء محليًا فقط؛ مراجعة زميل وتشغيل جهازه لم يحدثا.
التقارير الثلاثة لا تحتوي صورًا أو labels خامًا أو أسماء الفئات الحقيقية
أو مسارات شخصية؛ النسخ القابلة للتنزيل في outputs تطابق reports/shareable.
'''
(share/'PHASE2_STATUS.md').write_text(status,encoding='utf8')
names=['PHASE2_STATUS.md','class_mapping_summary.json','issue_resolution_summary.json'];out=root/'outputs';out.mkdir(exist_ok=True)
raw_names=json.loads((root/'reports/private/class_map_PRIVATE.json').read_text(encoding='utf8'))
for name in names:
    text=(share/name).read_text(encoding='utf8')
    if any(value in text for value in raw_names) or any(v in text for v in ['C:\\Users','GiGabyte']):raise RuntimeError('Privacy check failed')
    shutil.copy2(share/name,out/name)
print(json.dumps({'deliverables':names,'tests_passed':int(match[1]),'checksums':{n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in names}}))
