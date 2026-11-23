import truststore
truststore.inject_into_ssl()

import shutil
from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import interrupt
from send2trash import send2trash

import config
from file_readers import read_image, read_video_frames, read_document_text
from state import State, FileItem, Classification

load_dotenv()


def get_kind(path: Path) -> str:
    """מחזירה את סוג הקובץ לפי הסיומת שלו."""
    suffix = path.suffix.lower()
    for kind, extensions in config.EXTENSIONS.items():
        if suffix in extensions:
            return kind
    return "other"


def scan_files(state: State):
    """תחנה 1: סורקת את ההורדות ויוצרת כרטיס לכל קובץ."""
    files = []

    for path in config.DOWNLOADS.iterdir():
        # מדלגים על תיקיות (לימודים, downloads_agent...) - רק קבצים
        if not path.is_file():
            continue

        kind = get_kind(path)

        item: FileItem = {
            "name": path.name,
            "path": str(path),
            "kind": kind,
            "category": None,
            "reason": "",
            "confident": False,
            "attempts": 0,
        }

        # שירים - ברור לפי הסיומת, לא צריך מודל
        if kind == "audio":
            item["category"] = "שירים"
            item["reason"] = "קובץ שמע"
            item["confident"] = True
        # קבצים בלי תוכן קריא - אין טעם בבדיקת עומק, ישר לשאול
        if kind == "other":
            item["attempts"] = config.MAX_DEEP_ATTEMPTS
        files.append(item)

    return {"files": files}


# ===== המודל והטופס (נוצרים פעם אחת) =====
model = init_chat_model(config.MODEL, temperature=0)
classifier = model.with_structured_output(Classification).with_retry(stop_after_attempt=3)

SYSTEM_PROMPT = """את מסדרת את תיקיית ההורדות של סטודנטית למדעי המחשב.
התיקיות האפשריות:
- לימודים: כל מה שקשור ללימודים: תרגילים, מצגות, סיכומים, צילומי מסך של קוד או שקופיות, הקלטות שיעורים.
- מסמכים: מסמכים אישיים שאינם לימודים, כמו קבלות, טפסים ואישורים.
- תמונות: תמונות אישיות שאינן חומר לימודי.
- סרטי וידאו: סרטונים שאינם שיעורים.
- שירים: קבצי שמע.
- לבדיקה: רק אם אין שום דרך לדעת.
אם אי אפשר לדעת בוודאות מהשם בלבד, סמני confident=False."""

quick_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "שם הקובץ: {name}\n סוג הקובץ: {kind}"),
])

quick_chain = quick_prompt | classifier


def quick_classify(state: State):
    """תחנה 2: מסווגת כל קובץ לפי השם שלו בלבד."""
    files = state["files"]
    todo = [f for f in files if f["category"] is None]

    if todo:
        inputs = [{"name": f["name"], "kind": f["kind"]} for f in todo]
        results = quick_chain.batch(inputs, config={"max_concurrency": 2})

        for f, result in zip(todo, results):
            f["category"] = result.category
            f["confident"] = result.confident
            f["reason"] = result.reason

    return {"files": files}


def build_deep_message(f: FileItem):
    """בונה הודעה עם התוכן של הקובץ. בניסיון השני, יותר תוכן."""
    more = f["attempts"] + 1          # ניסיון 1 = מעט, ניסיון 2 = יותר
    text = f"שם הקובץ: {f['name']}\nסוג הקובץ: {f['kind']}\nהחליטי לפי התוכן המצורף."
    images = []

    if f["kind"] == "image":
        images = read_image(f["path"])
    elif f["kind"] == "video":
        images = read_video_frames(f["path"], n_frames=2 * more)
    elif f["kind"] == "document":
        text += "\n\nתוכן הקובץ:\n" + read_document_text(f["path"], max_chars=1500 * more)

    content = [{"type": "text", "text": text}]
    for img in images:
        content.append({"type": "image_url", "image_url": {"url": img}})

    return [SystemMessage(SYSTEM_PROMPT), HumanMessage(content=content)]



def deep_classify(state: State):
    """תחנה 3: מסתכלת על התוכן של קבצים לא ברורים."""
    files = state["files"]
    for f in files:
        if not f["confident"] and f["attempts"] < config.MAX_DEEP_ATTEMPTS:
            result = classifier.invoke(build_deep_message(f))
            f["category"] = result.category
            f["confident"] = result.confident
            f["reason"] = result.reason
            f["attempts"] += 1
    return {"files": files}


def route_after_classify(state: State) -> str:
    """צומת הדרכים: לאן ממשיכים אחרי סיווג?"""
    files = state["files"]

    # יש קובץ לא בטוח שעוד מותר לבדוק אותו? → בדיקת עומק (לולאה 🔁)
    for f in files:
        if not f["confident"] and f["attempts"] < config.MAX_DEEP_ATTEMPTS:
            return "deep_classify"

    # נשארו קבצים לא בטוחים אחרי כל הניסיונות? → לשאול אותך ✋
    for f in files:
        if not f["confident"]:
            return "ask_user"

    # הכול ברור → להעביר
    return "move_files"


def ask_user(state: State):
    """תחנה 4: עוצרת ושואלת אותך רק על הקבצים הלא ברורים. ✋"""
    files = state["files"]
    unclear = [f for f in files if not f["confident"]]

    answers = interrupt({
        "question": "לא הצלחתי להחליט לגבי הקבצים האלה. מה לעשות איתם?",
        "files": [{"name": f["name"], "reason": f["reason"]} for f in unclear],
        "options": config.CATEGORIES + ["למחוק", "להשאיר"],
    })

    for f in unclear:
        f["category"] = answers.get(f["name"], "להשאיר")
        f["confident"] = True
        f["reason"] = "נבחר על ידך"

    return {"files": files}


def move_files(state: State):
    """תחנה 5: מעבירה, מוחקת לסל המיחזור, או משאירה."""
    moved = []
    for f in state["files"]:
        category = f["category"]

        if category == "להשאיר":
            continue

        if category == "למחוק":
            send2trash(f["path"])
            moved.append(f"🗑️ {f['name']} → סל המיחזור")
            continue

        folder = config.DESTINATIONS[category]
        folder.mkdir(parents=True, exist_ok=True)

        target = folder / f["name"]
        i = 1
        while target.exists():  # כבר יש קובץ בשם הזה? → מוסיפים מספר
            target = folder / f"{Path(f['name']).stem}_{i}{Path(f['name']).suffix}"
            i += 1

        shutil.move(f["path"], target)
        moved.append(f"✅ {f['name']} → {category}")

    return {"moved": moved}



if __name__ == "__main__":
    state = scan_files({})
    state = quick_classify(state)
    while route_after_classify(state) == "deep_classify":   # מדמה את הלולאה
        print("🔁 בדיקת עומק...")
        state = deep_classify(state)
    print("➡️ הצעד הבא:", route_after_classify(state))
    for f in state["files"]:
        print(f["name"], "|", f["category"], "| בטוח:", f["confident"], "|", f["reason"])