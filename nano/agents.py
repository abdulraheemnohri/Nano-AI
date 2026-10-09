"""Small, bounded specialist delegation layer using Nano's configured model."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from .db import run
from .core import respond

ROLES = {
    "researcher": "You are Nano's research specialist. Separate verified facts from uncertainty. Do not claim browsing unless sources were provided.",
    "coder": "You are Nano's coding specialist. Provide safe, testable code and explain assumptions. Do not claim code was executed.",
    "planner": "You are Nano's planning specialist. Return ordered, practical steps with dependencies and risks.",
    "reviewer": "You are Nano's critical reviewer. Find errors, missing requirements, edge cases, and security concerns.",
    "writer": "You are Nano's writing specialist. Produce clear, well-structured prose suited to the requested audience.",
}
MAX_TASK_CHARS = 8000

def delegate(role, task, timeout_seconds=180):
    role = str(role or "").strip().lower()
    task = str(task or "").strip()
    if role not in ROLES: raise ValueError("Unknown role. Choose: "+", ".join(ROLES))
    if not task or len(task) > MAX_TASK_CHARS: raise ValueError("Task must contain 1 to 8000 characters.")
    if isinstance(timeout_seconds,bool) or not isinstance(timeout_seconds,int) or not 5 <= timeout_seconds <= 300:
        raise ValueError("timeout_seconds must be between 5 and 300.")
    cid = run("INSERT INTO conversations(title) VALUES(?)", ("Agent: "+role+" — "+task[:60],))
    prompt = f"[Specialist role: {role}]\n{ROLES[role]}\n\nDelegate task:\n{task}"
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(respond, cid, prompt)
    try:
        result = future.result(timeout=timeout_seconds)
        return {"role":role,"conversation_id":cid,"status":"complete","result":result}
    except TimeoutError:
        future.cancel()
        return {"role":role,"conversation_id":cid,"status":"timeout","result":"Agent exceeded the configured time limit; model generation may finish in the background."}
    except Exception as exc:
        return {"role":role,"conversation_id":cid,"status":"error","result":str(exc)[:1000]}
    finally:
        pool.shutdown(wait=False,cancel_futures=True)

def delegate_many(tasks, timeout_seconds=180):
    if not isinstance(tasks,list) or not 1 <= len(tasks) <= 4:
        raise ValueError("Provide between 1 and 4 specialist tasks.")
    results=[]
    for item in tasks:
        if not isinstance(item,dict): raise ValueError("Each task must include role and task.")
        results.append(delegate(item.get("role"),item.get("task"),timeout_seconds))
    return {"results":results,"completed":sum(x["status"]=="complete" for x in results)}
