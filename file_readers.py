import base64
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np

MAX_SIDE = 768  # מקטינים תמונות כדי לחסוך


def _to_data_uri(img) -> str:
    """ממירה תמונה לטקסט שאפשר לשלוח למודל."""
    h, w = img.shape[:2]
    scale = MAX_SIDE / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)))
    ok, buf = cv2.imencode(".jpg", img)
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


def read_image(path: str) -> list[str]:
    """מחזירה רשימה עם תמונה אחת."""
    data = np.fromfile(path, dtype=np.uint8)   # עובד גם עם שמות בעברית
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return [_to_data_uri(img)] if img is not None else []


def read_video_frames(path: str, n_frames: int) -> list[str]:
    """מצלמת n_frames תמונות מתוך הסרטון, מפוזרות לאורכו."""
    tmp_dir = tempfile.mkdtemp()
    tmp_path = str(Path(tmp_dir) / ("video" + Path(path).suffix))
    shutil.copy(path, tmp_path)   # OpenCV לא אוהב שמות בעברית, אז מעתיקים לשם באנגלית
    frames = []
    cap = cv2.VideoCapture(tmp_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    for i in range(n_frames):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * (i + 1) / (n_frames + 1)))
        ok, frame = cap.read()
        if ok:
            frames.append(_to_data_uri(frame))
    cap.release()
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return frames


def read_document_text(path: str, max_chars: int) -> str:
    """מחזירה את תחילת הטקסט של מסמך."""
    suffix = Path(path).suffix.lower()
    try:
        if suffix == ".pdf":
            from pypdf import PdfReader
            text = "\n".join((p.extract_text() or "") for p in PdfReader(path).pages[:3])
        elif suffix == ".docx":
            import docx
            text = "\n".join(p.text for p in docx.Document(path).paragraphs)
        elif suffix == ".txt":
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
        else:
            text = ""
    except Exception as e:
        text = f"(לא הצלחתי לקרוא: {e})"
    return text[:max_chars]