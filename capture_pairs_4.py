import os
import subprocess
import time
import hashlib

# --- Настройки ---
original_dir = "original_photos"  # Папка с исходными фото
output_dir = "pairs"              # Папка для пар (оригинал + фото с экрана)
opencamera_dir = "/sdcard/DCIM/OpenCamera"  # Путь к фото на телефоне

os.makedirs(output_dir, exist_ok=True)

def get_last_photo_from_phone():
    """Получает имя последнего JPG-файла с телефона"""
    result = subprocess.run(
        ["adb", "shell", "ls", "-t", opencamera_dir],
        capture_output=True, text=True
    )
    files = [f.strip() for f in result.stdout.splitlines() if f.strip().endswith(".jpg")]
    return files[0] if files else None

def is_opencamera_running():
    """Проверяет, запущена ли OpenCamera"""
    result = subprocess.run(
        ["adb", "shell", "dumpsys", "window", "windows"],
        capture_output=True, text=True
    )
    return "net.sourceforge.opencamera/net.sourceforge.opencamera.MainActivity" in result.stdout

def get_file_hash(path):
    """Вычисляет SHA256-хеш файла по пути"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

# --- Основной цикл ---
for img_name in sorted(os.listdir(original_dir)):
    if not img_name.lower().endswith(('.jpg', '.jpeg', '.png')):
        continue

    img_path = os.path.join(original_dir, img_name)

    # Закрываем Preview, если он открыт
    subprocess.run(["pkill", "Preview"])
    time.sleep(1)

    # Открываем новое фото
    subprocess.run(["open", "-a", "Preview", img_path])
    time.sleep(2)

    # Запускаем OpenCamera, если не запущена
    if not is_opencamera_running():
        subprocess.run(["adb", "shell", "am", "start", "-n", "net.sourceforge.opencamera/.MainActivity"])
        time.sleep(3)

    # Получаем имя и хеш текущего последнего фото
    prev_photo = get_last_photo_from_phone()
    prev_hash = None
    if prev_photo:
        temp_path = "__temp_prev.jpg"
        subprocess.run(["adb", "pull", f"{opencamera_dir}/{prev_photo}", temp_path], capture_output=True)
        if os.path.exists(temp_path):
            prev_hash = get_file_hash(temp_path)
            os.remove(temp_path)

    print("📷 Сними экран вручную. Ждём появления нового снимка...")

    # Ждём появления нового снимка с другим хешем
    timeout = 30  # секунд
    start_time = time.time()
    new_photo = None

    while time.time() - start_time < timeout:
        current_photo = get_last_photo_from_phone()
        if current_photo and current_photo != prev_photo:
            temp_path = "__temp_check.jpg"
            subprocess.run(["adb", "pull", f"{opencamera_dir}/{current_photo}", temp_path], capture_output=True)
            if os.path.exists(temp_path):
                current_hash = get_file_hash(temp_path)
                if current_hash != prev_hash:
                    new_photo = current_photo
                    break
                os.remove(temp_path)
        time.sleep(1)

    if new_photo:
        remote_path = f"{opencamera_dir}/{new_photo}"
        local_path = os.path.join(output_dir, f"screen_{img_name}")
        subprocess.run(["adb", "pull", remote_path, local_path])
        print(f"✅ Скопировано: {local_path}")
        subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"])
    else:
        print("❌ Не удалось получить новый снимок. Попробуй ещё раз.")
