from typing import Literal, TypedDict
from pydantic import BaseModel, Field


# ===== הכרטיס של כל קובץ =====
class FileItem(TypedDict):
    name: str               # שם הקובץ
    path: str               # הנתיב המלא
    kind: str               # video / audio / image / document / other
    category: str | None    # לאן להעביר (None = עוד לא הוחלט)
    reason: str             # למה הוחלט כך
    confident: bool         # האם המודל בטוח
    attempts: int           # כמה פעמים הסתכלנו לעומק


# ===== התיק המשותף של הגרף =====
class State(TypedDict, total=False):
    files: list[FileItem]   # כל הכרטיסים
    moved: list[str]        # דוח: מה הועבר לאן


# ===== הטופס שהמודל ממלא =====
class Classification(BaseModel):
    category: Literal["סרטי וידאו", "שירים", "מסמכים", "לימודים", "תמונות", "לבדיקה"] = Field(
        description="התיקייה שאליה הקובץ שייך"
    )
    confident: bool = Field(
        description="True אם את בטוחה. False אם אי אפשר לדעת בוודאות"
    )
    reason: str = Field(
        description="הסבר קצר בעברית, עד 10 מילים"
    )