import truststore
truststore.inject_into_ssl()

from dotenv import load_dotenv
load_dotenv()

from langsmith import Client

import config
from nodes import get_kind, quick_classify, deep_classify, route_after_classify

EVAL_DIR = config.PROJECT_DIR / "eval_files"
DATASET_NAME = "downloads-agent-eval"

# ===== התשובון: שם קובץ ← התשובה הנכונה =====
EXPECTED = {
    "IMG_001.png": "לימודים",
    "IMG_002.jpg": "תמונות",
    "doc1.docx":   "לימודים",
    "file1.pptx":  "לימודים",
    "notes.txt":   "לימודים",
    "doc2.txt":    "מסמכים",
    "track01.mp3": "שירים",
    "VID_001.mp4": "סרטי וידאו",
    "page.html":   "לבדיקה",
    "data.bin":    "לבדיקה",
}

client = Client()


# ===== 1. Dataset: יוצרים את המבחן ב-LangSmith (פעם אחת) =====
if not client.has_dataset(dataset_name=DATASET_NAME):
    dataset = client.create_dataset(dataset_name=DATASET_NAME)
    client.create_examples(
        dataset_id=dataset.id,
        examples=[
            {"inputs": {"file_name": name}, "outputs": {"category": category}}
            for name, category in EXPECTED.items()
        ],
    )


# ===== 2. Target: הסוכן שנבחן =====
def classify_one(file_name: str, use_deep: bool) -> dict:
    path = EVAL_DIR / file_name
    kind = get_kind(path)
    item = {"name": file_name, "path": str(path), "kind": kind,
            "category": None, "reason": "", "confident": False, "attempts": 0}

    if kind == "audio":
        return {"category": "שירים"}
    if kind == "other":
        return {"category": "לבדיקה"}

    state = quick_classify({"files": [item]})
    if use_deep:
        while route_after_classify(state) == "deep_classify":
            state = deep_classify(state)

    f = state["files"][0]
    return {"category": f["category"] if f["confident"] else "לבדיקה"}


# ===== 3. Evaluator: הבודקת =====
def correct_category(outputs: dict, reference_outputs: dict) -> bool:
    return outputs.get("category") == reference_outputs["category"]


# ===== 4. Experiments: לפני ואחרי =====
client.evaluate(
    lambda inputs: classify_one(inputs["file_name"], use_deep=False),
    data=DATASET_NAME,
    evaluators=[correct_category],
    experiment_prefix="v1-name-only",
    max_concurrency=1,
)

client.evaluate(
    lambda inputs: classify_one(inputs["file_name"], use_deep=True),
    data=DATASET_NAME,
    evaluators=[correct_category],
    experiment_prefix="v2-deep-look",
    max_concurrency=1,
)

print("✅ סיימתי! היכנסי ל-LangSmith, ואז Datasets & Experiments, ואז", DATASET_NAME)