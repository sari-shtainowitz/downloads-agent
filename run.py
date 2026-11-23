import uuid
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from graph import build_graph

graph = build_graph(checkpointer=InMemorySaver())                # 💾 "שמור משחק"
config = {"configurable": {"thread_id": str(uuid.uuid4())}}      # 🏷️ שם ייחודי לריצה

result = graph.invoke({}, config)                                 # ▶️ מתחילים עם תיק ריק

# ✋ הגרף עצר לשאול?
if "__interrupt__" in result:
    question = result["__interrupt__"][0].value
    print("\n❓", question["question"])
    print("אפשרויות:", ", ".join(question["options"]))

    answers = {}
    for f in question["files"]:
        print(f"\n📄 {f['name']}  ({f['reason']})")
        answers[f["name"]] = input("מה לעשות? ")

    result = graph.invoke(Command(resume=answers), config)        # ▶️ ממשיכים עם התשובות

print("\n📦 סיכום:")
for line in result.get("moved", []):
    print(line)