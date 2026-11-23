from pathlib import Path

# ===== המודל =====
MODEL = "google_genai:gemini-3.5-flash-lite"

# ===== מצב ניסוי =====
TEST_MODE = False

# ===== כמה פעמים מותר להסתכל לעומק על קובץ לא ברור =====
MAX_DEEP_ATTEMPTS = 2

PROJECT_DIR = Path(__file__).parent
HOME = Path(r"D:\Users\User")
if TEST_MODE:
    DOWNLOADS = PROJECT_DIR / "test_downloads"
    OUT = PROJECT_DIR / "test_output"
    DESTINATIONS = {
        "סרטי וידאו": OUT / "Videos" / "סרטי וידאו",
        "שירים":      OUT / "Music" / "שירים הורדות",
        "מסמכים":     OUT / "Documents" / "מסמכים הורדות",
        "לימודים":    OUT / "Downloads" / "לימודים",
        "תמונות":     OUT / "Pictures" / "תמונות הורדות",
        "לבדיקה":     OUT / "Downloads" / "לבדיקה",
    }
else:
    DOWNLOADS = HOME / "Downloads"
    DESTINATIONS = {
        "סרטי וידאו": HOME / "Videos" / "סרטי וידאו",
        "שירים":      HOME / "Music" / "שירים הורדות",
        "מסמכים":     HOME / "Documents" / "מסמכים הורדות",
        "לימודים":    HOME / "Downloads" / "לימודים",
        "תמונות":     HOME / "Pictures" / "תמונות הורדות",
        "לבדיקה":     HOME / "Downloads" / "לבדיקה",
    }

# ===== רשימת שמות הקטגוריות (בשביל השאלה ב-ask_user) =====
CATEGORIES = list(DESTINATIONS.keys())

# ===== תיקיות בתוך ההורדות שהסוכן לא נוגע בהן =====
SKIP_FOLDERS = {"downloads_agent", "לימודים", "לבדיקה"}

# ===== איזו סיומת שייכת לאיזה סוג =====
EXTENSIONS = {
    "video":    {".mp4", ".mov", ".avi", ".mkv", ".webm"},
    "audio":    {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"},
    "image":    {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"},
    "document": {".pdf", ".docx", ".txt", ".pptx"},
}