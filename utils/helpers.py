import os
import time
import random
from tqdm import tqdm
from .constants import WHEEL, DISABLED_PREFIX, DISABLED_TAG

def project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def resolve_path(rel_path: str) -> str:
    return os.path.join(project_root(), rel_path)

def spin_wheel():
    for _ in tqdm(range(30), desc="🎡 Обертання барабана"):
        time.sleep(0.05)
    return random.choice(WHEEL)

def mask_str(chars):
    return " ".join(chars)

def sanitize_category(text: str):
    return (text or "").replace(DISABLED_PREFIX, "").replace(DISABLED_TAG, "").strip()

def send_audio_if_exists(bot, chat_id, rel_path):
    path = resolve_path(rel_path)
    try:
        with open(path, "rb") as f:
            bot.send_audio(chat_id, f)
    except FileNotFoundError:
        pass

def send_animation_if_exists(bot, chat_id, rel_path, caption=None):
    path = resolve_path(rel_path)
    try:
        with open(path, "rb") as f:
            bot.send_animation(chat_id, f, caption=caption)
    except FileNotFoundError:
        pass
