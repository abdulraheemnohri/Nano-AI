"""Explicitly enabled local desktop control with small, auditable action surface."""
import base64
import io
import os

def desktop_action(action, x=None, y=None, text=None, key=None, approved=False):
    if os.getenv("NANO_ENABLE_DESKTOP_CONTROL","false").strip().lower() not in {"1","true","yes","on"}:
        raise PermissionError("Desktop control is disabled. Set NANO_ENABLE_DESKTOP_CONTROL=true on the local machine to opt in.")
    if action not in {"screenshot","click","type_text","press_key"}:
        raise ValueError("Allowed actions: screenshot, click, type_text, press_key.")
    if action!="screenshot" and not approved:
        raise PermissionError("Explicit approval is required for desktop input actions.")
    try:
        import pyautogui
    except ImportError as exc:
        raise RuntimeError("Desktop control requires the optional desktop extra: pip install -e '.[desktop]'.") from exc
    pyautogui.FAILSAFE=True
    pyautogui.PAUSE=0.15
    if action=="screenshot":
        image=pyautogui.screenshot()
        buffer=io.BytesIO()
        image.save(buffer,format="PNG")
        return {"action":"screenshot","width":image.width,"height":image.height,
                "image_base64":base64.b64encode(buffer.getvalue()).decode("ascii")}
    width,height=pyautogui.size()
    if action=="click":
        if isinstance(x,bool) or not isinstance(x,int) or isinstance(y,bool) or not isinstance(y,int):
            raise ValueError("x and y must be integer screen coordinates.")
        if not 0<=x<width or not 0<=y<height: raise ValueError("Coordinates are outside the screen.")
        pyautogui.click(x,y)
        return {"action":"click","x":x,"y":y,"screen":[width,height]}
    if action=="type_text":
        if not isinstance(text,str) or not text or len(text)>500: raise ValueError("Text must contain 1 to 500 characters.")
        pyautogui.write(text,interval=0.02)
        return {"action":"type_text","characters":len(text)}
    allowed_keys={"enter","esc","tab","space","backspace","delete","up","down","left","right","home","end"}
    if not isinstance(key,str) or key.lower() not in allowed_keys: raise ValueError("Key is not allowlisted.")
    pyautogui.press(key.lower())
    return {"action":"press_key","key":key.lower()}
