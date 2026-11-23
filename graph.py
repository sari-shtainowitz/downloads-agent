from langgraph.graph import StateGraph, START, END

from state import State
from nodes import scan_files, quick_classify, deep_classify, route_after_classify, ask_user, move_files


def build_graph(checkpointer=None):
    builder = StateGraph(State)

    # ===== התחנות =====
    builder.add_node("scan_files", scan_files)
    builder.add_node("quick_classify", quick_classify)
    builder.add_node("deep_classify", deep_classify)
    builder.add_node("ask_user", ask_user)
    builder.add_node("move_files", move_files)

    # ===== החצים =====
    builder.add_edge(START, "scan_files")
    builder.add_edge("scan_files", "quick_classify")

    # 🔀 ענף מותנה אחרי הסיווג המהיר
    builder.add_conditional_edges("quick_classify", route_after_classify,
                                  ["deep_classify", "ask_user", "move_files"])
    # 🔁 לולאה: אחרי בדיקת עומק, שוב אותו צומת (יכול לחזור ל-deep_classify)
    builder.add_conditional_edges("deep_classify", route_after_classify,
                                  ["deep_classify", "ask_user", "move_files"])

    builder.add_edge("ask_user", "move_files")
    builder.add_edge("move_files", END)

    return builder.compile(checkpointer=checkpointer)