"""
KitagawaUtilits v7.2.

Простой и безопасный помощник для Android на Windows.

Что нового в версии 7.2:
  * встроенный загрузчик прошивок доведён до идеала: файл качается прямо
    в программе, без перекидывания в браузер;
  * SourceForge (crDroid, Evolution X, PixelOS, RisingOS, DerpFest,
    Project Elixir, Xiaomi.eu) разбирается через RSS и HTML-список файлов:
    выбирается самый свежий .zip и качается с зеркала use_mirror=autoselect;
  * Xiaomi / Redmi / POCO (HyperOS, MIUI, Xiaomi.eu): поиск прямой ссылки
    на bigota/cdnorg.d.miui.com по codename через зеркала и трекеры;
  * LineageOS, PixelExperience, ArrowOS, Paranoid Android — официальные
    API/JSON сборок с автоматическим извлечением последнего билда;
  * универсальный парсер страниц: .zip, .tgz, .tar.md5, .ozip, .ops, .bin;
  * браузер открывается только при капче/авторизации с понятным пояснением;
  * «💾 Быстрый бэкап»: фото, документы и список приложений через adb pull;
  * автопроверка обновлений на GitHub и кнопка «🚀 Доступно обновление».

Возможности версии 7.1:
  * умный резолвер прямых .zip-ссылок по коду устройства (codename):
    LineageOS API, SourceForge RSS (crDroid, Evolution X, PixelOS, RisingOS),
    GitHub Releases и OTA-JSON кастомных прошивок;
  * архив реально скачивается внутри окна с прогресс-баром, а браузер
    открывается только если ни один источник не отдал прямой файл;
  * прокручиваемая боковая панель и переключатель 5 языков внизу;
  * исправлена загрузка больших архивов: HTML-страница вместо файла
    больше не сохраняется как прошивка.

Возможности версии 7.0:
  * встроенный менеджер прямого скачивания прошивок прямо в программе;
  * живой прогресс-бар: процент, объём и скорость загрузки;
  * скачивание в фоновом потоке с потоковой записью на диск (chunk_size = 65536);
  * кнопка отмены загрузки и автопереход к установке после завершения;
  * скачанные архивы сохраняются в Downloads\\KitagawaFirmwares;
  * 5 языков интерфейса: русский, English, Українська, Español, 中文;
  * выбор языка в боковой панели с мгновенным переводом без перезапуска;
  * живое обновление каталога прошивок прямо из GitHub-репозитория.

Возможности версии 6.x:
  * вкладка «Здоровье и железо»: батарея, циклы, железо и безопасность через ADB;
  * трансляция экрана телефона на ПК через scrcpy с управлением мышкой;
  * в каталог добавлены Android-планшеты 2020–2026 с пометкой [Планшет];
  * анимированная заставка, вкладка «Поддержка и идеи» и форма Formspree;
  * плавная прокрутка на всех вкладках — нижние кнопки всегда доступны;
  * защита от «окирпичивания»: проверка заряда батареи перед прошивкой и очисткой;
  * безопасная очистка от рекламы и мусора без Root;
  * помощник с драйверами Google, установкой .apk и проверкой хешей прошивки;
  * каталог из 800+ прошивок и пошаговая инструкция для новичков.
"""

import ctypes
import hashlib
import html
import json
import math
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import zipfile
from tkinter import filedialog, messagebox

import customtkinter as ctk

try:  # Pillow нужен для иконки на заставке (идёт вместе с customtkinter).
    from PIL import Image
except Exception:  # noqa: BLE001
    Image = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------
APP_NAME = "KitagawaUtilits"
APP_VERSION = "7.2"
APP_SUBTITLE = "Простой и безопасный помощник для Android"
APP_TITLE = "KitagawaUtilits v7.2"

# Репозиторий проекта: автопроверка обновлений и живой каталог прошивок.
GITHUB_REPO = "Be3un4uk586/KitagawaUtilits"
GITHUB_REPO_URL = f"https://github.com/{GITHUB_REPO}"
GITHUB_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# Скрывает консольное окно Windows при запуске дочерних процессов.
CREATE_NO_WINDOW = 0x08000000

# Soft Crimson / Warm Dark Slate
COLOR_BG = "#121316"
COLOR_CARD = "#1B1D23"
COLOR_CARD_HOVER = "#252830"
COLOR_BORDER = "#2C2E36"
COLOR_ACCENT = "#C94A4A"
COLOR_ACCENT_HOVER = "#B03E3E"
COLOR_LAVENDER = "#C94A4A"
COLOR_CYAN = "#C94A4A"
COLOR_TEXT = "#E6E6E8"
COLOR_MUTED = "#9CA0AA"
COLOR_OK = "#8FD3B6"
COLOR_WARN = "#B57C38"
COLOR_ERR = "#D98A8A"

PARTITIONS = ["boot", "recovery", "init_boot", "vbmeta", "vendor_boot"]

INSTALL_LABELS = {
    "fastboot": "Через режим загрузчика",
    "adb_sideload": "Установка через кабель",
    "local_update": "Обычное обновление",
}

INSTALL_STYLES = {
    "fastboot": ("#33262A", "#D9A0A0"),
    "adb_sideload": ("#33262A", "#D9A0A0"),
    "local_update": ("#33262A", "#D9A0A0"),
}

PREFERRED_BRANDS = [
    "Vivo", "iQOO", "Xiaomi", "Redmi", "POCO", "Samsung", "Google",
    "OnePlus", "OPPO", "Realme", "Lenovo", "Honor", "Huawei", "Sony",
    "Nubia", "RedMagic", "Nothing", "Motorola", "ASUS",
]

SEARCH_PLACEHOLDER = "Поиск: модель, кодовое имя или ОС (например, OriginOS, POCO)"

# Куда уходят заявки из вкладки «Поддержка и идеи» (таблица Formspree).
FORMSPREE_URL = "https://formspree.io/f/xvkabrlv"

SUPPORT_TOPICS = [
    "Добавить модель телефона / прошивку",
    "Сообщить об ошибке",
    "Предложить улучшение",
]

SUPPORT_MESSAGE_PLACEHOLDER = "Напишите, какой телефон добавить или что поправить..."

# Официальный драйвер Google для Windows.
DRIVER_URL = "https://dl.google.com/android/repository/latest_usb_driver_windows.zip"

# Белый список проверенных рекламных и мусорных пакетов.
# Удаление этих приложений не мешает телефону работать.
SAFE_PACKAGES: dict[str, str] = {
    "com.miui.msa.global": "Встроенная реклама Xiaomi",
    "com.miui.systemAdSolution": "Рекламные баннеры Xiaomi",
    "com.miui.analytics": "Сбор статистики Xiaomi",
    "com.miui.daemon": "Служба диагностики Xiaomi",
    "com.miui.miservice": "Центр обслуживания Xiaomi",
    "com.miui.cloudservice": "Облако Xiaomi (фото на телефоне останутся)",
    "com.miui.cloudbackup": "Резервное копирование в облако Xiaomi",
    "com.miui.player": "Музыкальный плеер Xiaomi",
    "com.miui.videoplayer": "Видеоплеер Xiaomi",
    "com.miui.notes": "Заметки Xiaomi",
    "com.miui.weather2": "Погода Xiaomi",
    "com.facebook.system": "Фоновые службы Facebook",
    "com.facebook.appmanager": "Установщик приложений Facebook",
    "com.facebook.services": "Службы Facebook",
    "com.facebook.katana": "Приложение Facebook",
    "com.yandex.browser": "Предустановленный браузер Яндекс",
    "com.yandex.searchapp": "Поиск Яндекса",
    "com.yandex.music": "Яндекс Музыка (пробная версия)",
    "com.amazon.appmanager": "Службы магазина Amazon",
    "com.amazon.venezia": "Магазин приложений Amazon",
    "com.alibaba.aliexpresshd": "AliExpress",
    "com.zhiliaoapp.musically": "TikTok",
    "com.instagram.android": "Instagram",
    "com.netflix.mediaclient": "Netflix",
    "com.spotify.music": "Spotify",
    "com.booking": "Приложение Booking",
    "com.tripadvisor.tripadvisor": "Приложение TripAdvisor",
    "com.linkedin.android": "LinkedIn",
    "com.microsoft.office.officehubrow": "Microsoft Office",
    "com.samsung.android.app.spage": "Samsung Free (реклама)",
    "com.samsung.android.app.news": "Samsung News",
}

GUIDE_STEPS = [
    {
        "title": "Шаг 1. Включи на телефоне «Режим разработчика»",
        "paragraphs": [
            "Возьми телефон и открой «Настройки». Найди пункт «О телефоне» "
            "(иногда он называется «Сведения о телефоне»).",
            "Найди строку «Номер сборки» и нажми на неё 7 раз подряд. Появится "
            "сообщение «Вы стали разработчиком» — значит всё получилось.",
        ],
        "bullets": [
            "Если не можешь найти «Номер сборки», введи в поиске настроек слово «сборка».",
        ],
        "warnings": [],
    },
    {
        "title": "Шаг 2. Разреши компьютеру помогать телефону",
        "paragraphs": [
            "Вернись в «Настройки → Система → Для разработчиков» (на некоторых "
            "телефонах путь: «Настройки → Дополнительные настройки → Для разработчиков»).",
            "Включи переключатель «Отладка по USB». Это разрешение нужно, чтобы "
            "программа видела телефон и выполняла безопасные команды.",
            "Подключи телефон к компьютеру кабелем. На экране телефона появится "
            "окошко «Разрешить отладку по USB?». Поставь галочку «Всегда разрешать» "
            "и нажми «Разрешить».",
        ],
        "bullets": [
            "Используй оригинальный кабель. Если телефон не виден — попробуй другой "
            "USB-порт, лучше на задней панели компьютера.",
            "Пункт «Заводская разблокировка» нужен только для смены прошивки. Для "
            "очистки от рекламы и установки игр он не требуется.",
        ],
        "warnings": [
            "Разблокировка загрузчика стирает все данные и может лишить гарантии. "
            "Не включай её, если не собираешься менять прошивку.",
        ],
    },
    {
        "title": "Шаг 3. Проверь, что программа видит телефон",
        "paragraphs": [
            "Посмотри на цветную плашку в левом меню: зелёная «Устройство подключено» "
            "— всё хорошо, серая «Ожидание USB» — телефон пока не найден.",
            "Для подробной проверки открой вкладку «Управление телефоном» и нажми "
            "«Проверить телефон». Там же видно заряд батареи и состояние загрузчика.",
        ],
        "bullets": [
            "«Телефон найден» — можно пользоваться всеми вкладками.",
            "«Телефон в режиме загрузчика» — телефон готов к установке прошивки.",
            "Если телефон не виден — открой вкладку «Помощник и APK» и нажми "
            "«Установить драйверы».",
        ],
        "warnings": [],
    },
    {
        "title": "Шаг 4. Убери рекламу и мусор (самый безопасный способ)",
        "paragraphs": [
            "Открой вкладку «Очистка от рекламы». Режим «Только безопасная очистка» "
            "уже включён — программа покажет лишь проверенные рекламные и мусорные "
            "приложения, которые можно удалять без риска.",
            "Нажми «Найти рекламу и мусор в телефоне». Поставь галочки напротив "
            "ненужных приложений и нажми «Очистить выбранное».",
        ],
        "bullets": [
            "Телефон продолжит работать как раньше, а рекламы и лишних приложений станет меньше.",
            "Если что-то понадобится снова — нажми «Вернуть всё как было», и удалённые "
            "приложения вернутся обратно.",
            "Root и разблокировка загрузчика для этой вкладки не нужны.",
        ],
        "warnings": [
            "Не выключай «Только безопасную очистку», если не уверен в своих действиях: "
            "в полном списке есть важные системные приложения.",
        ],
    },
    {
        "title": "Шаг 5. Установи игру или программу (.apk)",
        "paragraphs": [
            "Открой вкладку «Помощник и APK» и нажми «Установить .apk файл с ПК на телефон».",
            "Выбери скачанный файл .apk. Программа сама установит его на подключённый телефон.",
            "Если на экране телефона появится вопрос про установку из неизвестного "
            "источника — разреши установку и нажми «Установить».",
        ],
        "bullets": [
            "Скачивай .apk только с официальных сайтов и из проверенных магазинов.",
            "Проверить целостность большого файла можно в блоке «Проверка файла прошивки».",
        ],
        "warnings": [
            "Не устанавливай файлы, в которых не уверен: вредоносные программы могут "
            "украсть данные.",
        ],
    },
    {
        "title": "Шаг 6. Обнови прошивку (только если действительно нужно)",
        "paragraphs": [
            "Открой «Прошивки», выбери бренд и модель. Если телефон подключён, нажми "
            "«Определить телефон» — программа сама подставит нужное устройство.",
            "Нажми «📥 Скачать в программу». Программа сама скачает архив с живым "
            "прогресс-баром, объёмом и скоростью загрузки, а файл сохранится в папку "
            "Downloads\\KitagawaFirmwares.",
            "Когда загрузка закончится, нажми «⚡ Перейти к установке» — путь к файлу "
            "подставится автоматически.",
            "Перед установкой проверь файл во вкладке «Помощник и APK»: посчитай хеш "
            "и сравни с хешем на сайте производителя.",
        ],
        "bullets": [
            "«Установка через кабель» — самый простой способ для обычного пользователя.",
            "«Через режим загрузчика» — для опытных, требует разблокированного загрузчика.",
            "«Обычное обновление» — официальное обновление из настроек телефона, "
            "загрузчик трогать не нужно.",
        ],
        "warnings": [
            "Перед прошивкой заряди телефон минимум до 50% и сделай резервную копию "
            "фото и контактов: прошивка обычно стирает данные.",
            "Программа не начнёт прошивку при заряде ниже 30% — это защита от поломки.",
            "Никогда не выдёргивай кабель во время установки прошивки.",
        ],
    },
    {
        "title": "Если что-то пошло не так",
        "paragraphs": [
            "Компьютер не видит телефон: открой «Помощник и APK» → «Установить драйверы», "
            "затем попробуй другой кабель и другой USB-порт.",
            "Удалил лишнее: открой «Очистка от рекламы» → «Вернуть всё как было».",
            "Телефон завис: зажми кнопку питания на 10–15 секунд, чтобы перезагрузить его.",
        ],
        "bullets": [
            "Проверь, что «Отладка по USB» включена и на экране телефона нажато «Разрешить».",
            "Перезапусти программу и компьютер, если связь с телефоном не появляется.",
            "Если телефон не включается после прошивки — обратись в сервисный центр "
            "производителя. Не пытайся разбирать его самостоятельно.",
        ],
        "warnings": [],
    },
]


def ui_font(size: int = 13, weight: str = "normal", family: str = "Segoe UI") -> ctk.CTkFont:
    """Единый системный шрифт приложения."""
    return ctk.CTkFont(family=family, size=size, weight=weight)


def enable_high_dpi() -> None:
    """Включает High-DPI режим Windows, чтобы шрифты не были мыльными."""
    if os.name != "nt":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        return
    except Exception:  # noqa: BLE001
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:  # noqa: BLE001
        pass


def resource_path(relative_path: str) -> str:
    """Абсолютный путь к ресурсу и из исходников, и из собранного .exe."""
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)


def application_dir() -> str:
    """Папка рядом с .exe (или с main.py при запуске из исходников)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.abspath(os.path.dirname(__file__))


TOOLS_DIR = resource_path("tools")
ADB = os.path.join(TOOLS_DIR, "adb.exe")
FASTBOOT = os.path.join(TOOLS_DIR, "fastboot.exe")
FIRMWARES_FILE = resource_path("firmwares.json")
DOWNLOADS_DIR = os.path.join(application_dir(), "downloads")
REMOVED_FILE = os.path.join(application_dir(), "removed_packages.json")

# Встроенный загрузчик сохраняет прошивки в «Загрузки» пользователя.
FIRMWARE_DOWNLOAD_DIR = os.path.join(
    os.path.expanduser("~"), "Downloads", "KitagawaFirmwares"
)

# Быстрый бэкап: Backups\{Модель}_{Дата} в профиле пользователя.
BACKUP_ROOT = os.path.join(os.path.expanduser("~"), "Backups")

# Локальные данные программы: кэш каталога и scrcpy.
LOCAL_DATA_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA") or application_dir(), APP_NAME
)
FIRMWARES_CACHE_FILE = os.path.join(LOCAL_DATA_DIR, "firmwares_cache.json")
SCRCPY_DIR = os.path.join(LOCAL_DATA_DIR, "scrcpy")

# Живой каталог прошивок: кнопка «Обновить базу» скачивает свежий JSON
# прямо из GitHub-репозитория, без пересборки .exe.
REMOTE_CATALOG_URL = (
    f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/firmwares.json"
)

# GitHub API для загрузки последнего релиза scrcpy-win64.
SCRCPY_RELEASE_API = "https://api.github.com/repos/Genymobile/scrcpy/releases/latest"

# ---------------------------------------------------------------------------
# Локализация (5 языков)
# ---------------------------------------------------------------------------
LANGUAGES = [
    ("ru", "🌐 Русский"),
    ("en", "🌐 English"),
    ("uk", "🌐 Українська"),
    ("es", "🌐 Español"),
    ("zh", "🌐 中文"),
]
LANGUAGE_LABELS = {code: label for code, label in LANGUAGES}
LABEL_TO_CODE = {label: code for code, label in LANGUAGES}
LANG = "ru"
LOCALES: dict[str, dict] = {}
SETTINGS_FILE = os.path.join(LOCAL_DATA_DIR, "settings.json")


def load_locales() -> None:
    """Загружает переводы из locales.json (работает и внутри собранного .exe)."""
    global LOCALES
    try:
        with open(resource_path("locales.json"), "r", encoding="utf-8") as handle:
            data = json.load(handle)
        LOCALES = data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        LOCALES = {}


def load_settings() -> None:
    """Читает сохранённый язык из settings.json."""
    global LANG
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        code = data.get("language") if isinstance(data, dict) else None
        if code in LANGUAGE_LABELS:
            LANG = code
    except Exception:  # noqa: BLE001
        LANG = "ru"


def save_settings() -> None:
    """Сохраняет выбранный язык в %LOCALAPPDATA%\\KitagawaUtilits\\settings.json."""
    try:
        os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as handle:
            json.dump({"language": LANG}, handle, ensure_ascii=False, indent=2)
    except Exception:  # noqa: BLE001
        pass


def t(key: str, **kwargs) -> str:
    """Перевод по ключу с откатом на русский и на сам ключ."""
    value = None
    for code in (LANG, "ru"):
        candidate = (LOCALES.get(code) or {}).get(key)
        if isinstance(candidate, str):
            value = candidate
            break
    if value is None:
        return key
    if kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return value
    return value


def tr(text):
    """Переводит точную строку интерфейса, если для неё есть перевод."""
    if not isinstance(text, str) or LANG == "ru":
        return text
    return (LOCALES.get(LANG) or {}).get(text, text)


def support_topics() -> list[str]:
    """Список тем формы поддержки на текущем языке."""
    values = (LOCALES.get(LANG) or {}).get("support_topics")
    if not isinstance(values, list):
        values = (LOCALES.get("ru") or {}).get("support_topics")
    if not isinstance(values, list):
        values = SUPPORT_TOPICS
    return [str(item) for item in values]


def set_language(code: str) -> None:
    """Меняет язык и сразу сохраняет выбор."""
    global LANG
    if code in LANGUAGE_LABELS:
        LANG = code
        save_settings()


def _patch_widget_translation(cls, attr: str) -> None:
    original = cls.__init__

    def wrapper(self, *args, **kwargs):
        value = kwargs.get(attr)
        if isinstance(value, str):
            kwargs[attr] = tr(value)
        original(self, *args, **kwargs)

    cls.__init__ = wrapper


def _patch_messageboxes() -> None:
    for name in ("showinfo", "showwarning", "showerror", "askyesno", "askokcancel"):
        original = getattr(messagebox, name)

        def wrapper(*args, _original=original, **kwargs):
            args = tuple(tr(item) if isinstance(item, str) else item for item in args)
            return _original(*args, **kwargs)

        setattr(messagebox, name, wrapper)


def _patch_file_dialogs() -> None:
    for name in ("askopenfilename", "asksaveasfilename"):
        original = getattr(filedialog, name)

        def wrapper(*args, _original=original, **kwargs):
            if isinstance(kwargs.get("title"), str):
                kwargs["title"] = tr(kwargs["title"])
            return _original(*args, **kwargs)

        setattr(filedialog, name, wrapper)


load_locales()
load_settings()

for _widget_cls, _widget_attr in (
    (ctk.CTkLabel, "text"),
    (ctk.CTkButton, "text"),
    (ctk.CTkSwitch, "text"),
    (ctk.CTkCheckBox, "text"),
    (ctk.CTkEntry, "placeholder_text"),
):
    _patch_widget_translation(_widget_cls, _widget_attr)
_patch_messageboxes()
_patch_file_dialogs()


def popen_flags() -> int:
    """Флаги создания процесса: без консольного окна на Windows."""
    return CREATE_NO_WINDOW if os.name == "nt" else 0


def format_size(num: float) -> str:
    """Человекочитаемый размер: 12.4 МБ, 1.80 ГБ, 512.0 КБ."""
    try:
        value = float(num)
    except (TypeError, ValueError):
        value = 0.0
    if value < 1024:
        return f"{int(value)} Б"
    value /= 1024.0
    if value < 1024:
        return f"{value:.1f} КБ"
    value /= 1024.0
    if value < 1024:
        return f"{value:.1f} МБ"
    value /= 1024.0
    return f"{value:.2f} ГБ"


class DownloadCancelled(Exception):
    """Пользователь отменил скачивание прошивки."""


class FirmwareDownloader:
    """Прямое скачивание прошивки в фоновом потоке.

    Особенности:
      * потоковая запись на диск кусками по 64 КБ — память не растёт
        даже при скачивании архивов на 3–5 ГБ;
      * прогресс, объём и скорость загрузки через колбэки в UI-поток;
      * отмена через threading.Event;
      * умный резолвер прямых ссылок по названию прошивки и codename:
        LineageOS API, SourceForge RSS (crDroid, Evolution X, PixelOS,
        RisingOS), GitHub Releases и OTA-JSON кастомных прошивок;
      * браузер открывается только если ни один API не отдал файл.
    """

    CHUNK_SIZE = 65536
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 KitagawaUtilits/7.2"
    )
    FILE_EXTENSIONS = (
        ".zip", ".img", ".bin", ".tar", ".tar.md5", ".tar.gz", ".tgz",
        ".ozip", ".ops", ".7z", ".rar", ".xz", ".gz",
    )
    # Для JSON/API-резолверов ищем именно полные архивы прошивки.
    ARCHIVE_EXTENSIONS = (
        ".zip", ".tgz", ".tar.md5", ".tar.gz", ".ozip", ".ops",
    )
    # Файлы, которые не являются полной прошивкой и не должны качаться.
    EXCLUDED_NAMES = (
        "boot.img", "recovery.img", "init_boot.img", "vendor_boot.img",
        "super_empty.img", "dtbo.img", "vbmeta.img", ".sha256", ".sha1",
        ".md5", ".json", ".txt", ".xml", ".html",
    )

    # GitHub: поддерживаем и страницу релиза, и корень репозитория.
    GITHUB_RE = re.compile(
        r"^https?://(?:www\.)?github\.com/([^/]+)/([^/?#]+)"
        r"(?:/releases(?:/(?:tag|download)/([^/?#]+))?)?",
        re.IGNORECASE,
    )
    HTML_LINK_RE = re.compile(
        r"""(?:href|src|data-url|data-href|data-download)\s*=\s*["']"""
        r"""([^"']+?\.(?:zip|img|bin|tar\.md5|tar\.gz|tgz|ozip|ops|7z|rar|xz))["']""",
        re.IGNORECASE,
    )
    # Прямые ссылки на файл, спрятанные в JSON/HTML (в том числе с \/).
    ESCAPED_LINK_RE = re.compile(
        r"https?:\\?/\\?/[^\"'<>\s]+?\.(?:zip|tgz|tar\.md5|ozip|ops|bin)",
        re.IGNORECASE,
    )
    SOURCEFORGE_FILE_LINK_RE = re.compile(
        r"https?://(?:www\.)?sourceforge\.net/projects/[^\"'<>\s]+?"
        r"\.(?:zip|tgz|tar\.md5|ozip|ops)/download",
        re.IGNORECASE,
    )
    SOURCEFORGE_ITEM_RE = re.compile(r"<item>(.*?)</item>", re.IGNORECASE | re.DOTALL)

    # Официальные зеркала Xiaomi (HyperOS / MIUI / Xiaomi.eu).
    XIAOMI_MIRROR_RE = re.compile(
        r"https?://(?:"
        r"(?:bigota|cdnorg|bn|hugeota|airbota)\.d\.miui\.com/"
        r"|[a-z0-9.-]*miui-ota-update[a-z0-9.-]*\.aliyuncs\.com/"
        r")[^\"'<>\s]+?\.(?:tgz|zip|tar\.md5)",
        re.IGNORECASE,
    )
    XIAOMI_PAGE_TEMPLATES = (
        "https://xiaomifirmwareupdater.com/hyperos/{codename}/",
        "https://xiaomifirmwareupdater.com/miui/{codename}/",
        "https://xiaomifirmwareupdater.com/archive/hyperos/{codename}/",
        "https://xiaomifirmwareupdater.com/archive/miui/{codename}/",
        "https://miuirom.org/phones/{codename}",
    )
    # Трекеры прошивок Xiaomi на GitHub (YAML/JSON с прямыми ссылками).
    XIAOMI_TRACKER_URLS = (
        "https://raw.githubusercontent.com/XiaomiFirmwareUpdater/"
        "miui-updates-tracker/master/data/latest.yml",
        "https://raw.githubusercontent.com/XiaomiFirmwareUpdater/"
        "miui-updates-tracker/master/data/miui.yml",
    )

    # Официальное API LineageOS (v2 — актуальное, v1 — запасное).
    LINEAGE_API_TEMPLATES = (
        "https://download.lineageos.org/api/v2/devices/{codename}/builds",
        "https://download.lineageos.org/api/v1/{codename}/nightly/1",
        "https://lineageos.org/api/v2/devices/{codename}/builds",
    )

    # API/JSON других популярных прошивок (пробуем по очереди).
    ROM_API_TEMPLATES = (
        "https://download.pixelexperience.org/api/v1/{codename}",
        "https://api.arrowos.net/v1/{codename}",
        "https://paranoidandroid.co/api/v1/{codename}",
        "https://download.pixelexperience.org/{codename}",
    )

    # Признаки капчи/авторизации — только тогда открываем браузер.
    CAPTCHA_MARKERS = (
        "captcha", "recaptcha", "hcaptcha", "cf-challenge",
        "sign in to download", "login to download", "please log in",
        "access denied", "authorization required",
    )

    # Какие SourceForge-проекты соответствуют названию прошивки.
    SOURCEFORGE_OS_PROJECTS = {
        "crdroid": ("crdroid",),
        "evolution x": ("evolution-x", "evolutionx"),
        "pixelos": ("pixelos", "pixelos-releases", "pixelos-aosp"),
        "risingos": ("risingos", "risingos-releases", "risingos-revived"),
        "derpfest": ("derpfest", "derp-fest"),
        "project elixir": ("project-elixir", "elixir"),
        "xiaomi.eu": ("xiaomi-eu-multilang-miui-roms",),
    }

    # GitHub-репозитории с OTA-JSON: {название прошивки: (репозитории, ветки)}.
    OTA_JSON_SOURCES = {
        "pixelos": (
            ("PixelOS-AOSP/ota", "PixelOS-AOSP/ota_configs"),
            ("sixteen", "fifteen", "main"),
        ),
        "risingos": (
            ("RisingOS-Revived/ota",),
            ("seventeen", "sixteen", "fifteen", "main"),
        ),
        "evolution x": (
            ("Evolution-X/OTA",),
            ("sixteen", "fifteen", "fourteen", "main"),
        ),
        "derpfest": (
            ("DerpFest-Devices/OTA", "DerpFest-AOSP/ota"),
            ("sixteen", "fifteen", "main"),
        ),
        "project elixir": (
            ("Project-Elixir/ota",),
            ("sixteen", "fifteen", "main"),
        ),
        "arrowos": (
            ("ArrowOS/ota",),
            ("thirteen", "twelve", "main"),
        ),
        "paranoid android": (
            ("AOSPA/ota", "paranoidandroid/ota"),
            ("sixteen", "fifteen", "main"),
        ),
    }

    def __init__(self, app, firmware: dict, on_progress=None, on_status=None,
                 on_done=None, on_fallback=None, on_error=None,
                 on_cancel=None) -> None:
        self.app = app
        self.firmware = firmware or {}
        self.on_progress = on_progress
        self.on_status = on_status
        self.on_done = on_done
        self.on_fallback = on_fallback
        self.on_error = on_error
        self.on_cancel = on_cancel

        self.cancel_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.downloaded = 0
        self.total = 0
        self.speed = 0.0
        self.path = ""
        self.fallback_reason = ""

    # ------------------------------------------------------------------
    # Управление потоком
    # ------------------------------------------------------------------
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        self.cancel_event.set()

    def _emit(self, callback, *args) -> None:
        """Безопасно вызывает UI-колбэк из рабочего потока."""
        if callback is None:
            return
        try:
            self.app.after(0, lambda: callback(*args))
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # Поиск прямой ссылки
    # ------------------------------------------------------------------
    @classmethod
    def is_direct_url(cls, url: str) -> bool:
        try:
            path = urllib.parse.urlparse(url).path.lower()
        except Exception:  # noqa: BLE001
            return False
        return path.endswith(cls.FILE_EXTENSIONS)

    @classmethod
    def _request(cls, url: str, accept: str | None = None) -> urllib.request.Request:
        headers = {
            "User-Agent": cls.USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
        }
        if accept:
            headers["Accept"] = accept
        return urllib.request.Request(url, headers=headers)

    # ------------------------------------------------------------------
    # Низкоуровневые помощники
    # ------------------------------------------------------------------
    def _fetch(self, url: str, accept: str | None = None,
               limit: int = 1024 * 1024, timeout: int = 20) -> bytes | None:
        try:
            request = self._request(url, accept)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(limit)
        except Exception:  # noqa: BLE001
            return None

    def _fetch_text(self, url: str, accept: str | None = None,
                    limit: int = 1024 * 1024, timeout: int = 20) -> str:
        raw = self._fetch(url, accept, limit, timeout)
        return raw.decode("utf-8", "replace") if raw else ""

    def _fetch_json(self, url: str, timeout: int = 20):
        raw = self._fetch(url, "application/json, text/plain, */*",
                          2 * 1024 * 1024, timeout)
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8", "replace"))
        except (ValueError, UnicodeError):
            return None

    def _fetch_text_fallback(self, url: str, accept: str | None = None,
                             limit: int = 2 * 1024 * 1024,
                             timeout: int = 25) -> str:
        """Читает страницу urllib-ом, а при 403 — через curl и PowerShell."""
        text = self._fetch_text(url, accept, limit, timeout)
        if text.strip():
            return text
        text = self._curl_text(url, timeout=timeout)
        if text.strip():
            return text
        return self._powershell_text(url, timeout=timeout + 10)

    @classmethod
    def _is_archive_url(cls, value) -> bool:
        """True, если строка — прямая http(s)-ссылка на архив прошивки."""
        if not isinstance(value, str):
            return False
        value = value.strip()
        if not value.lower().startswith(("http://", "https://")):
            return False
        if cls._is_excluded(value):
            return False
        try:
            path = urllib.parse.urlparse(value).path.lower()
        except Exception:  # noqa: BLE001
            return False
        if path.endswith(cls.ARCHIVE_EXTENSIONS):
            return True
        # SourceForge: .../file.zip/download (ссылку потом превратим в зеркало).
        if path.endswith("/download"):
            inner = path[: -len("/download")]
            return inner.endswith(cls.ARCHIVE_EXTENSIONS)
        return False

    @classmethod
    def _is_excluded(cls, value: str) -> bool:
        """Отсекает boot.img, recovery.img, контрольные суммы и JSON."""
        try:
            path = urllib.parse.unquote(
                urllib.parse.urlparse(value).path
            ).lower()
        except Exception:  # noqa: BLE001
            path = (value or "").lower()
        for suffix in cls.EXCLUDED_NAMES:
            # .tar.md5 — это полноценная прошивка Samsung, а не контрольная сумма.
            if suffix == ".md5" and path.endswith(".tar.md5"):
                continue
            if path.endswith(suffix) or f"{suffix}?" in path:
                return True
        return False

    def _find_archive_in_json(self, data, depth: int = 0) -> str | None:
        """Ищет первый .zip/.tgz в JSON любой структуры.

        Понимает формат LineageOS (files[0]["url"]), OTA-JSON кастомных
        прошивок (response[0]["url"]) и GitHub Releases (assets).
        """
        if depth > 8:
            return None
        if isinstance(data, dict):
            files = data.get("files")
            if isinstance(files, list):
                for item in files:
                    found = self._find_archive_in_json(item, depth + 1)
                    if found:
                        return found
            for key in ("url", "download_url", "download", "link", "file"):
                value = data.get(key)
                if self._is_archive_url(value):
                    return value.strip()
            for value in data.values():
                if self._is_archive_url(value):
                    return value.strip()
            for value in data.values():
                if isinstance(value, (dict, list)):
                    found = self._find_archive_in_json(value, depth + 1)
                    if found:
                        return found
            return None
        if isinstance(data, list):
            for item in data:
                found = self._find_archive_in_json(item, depth + 1)
                if found:
                    return found
            return None
        if self._is_archive_url(data):
            return data.strip()
        return None

    def _normalize_direct(self, candidate: str | None) -> str | None:
        """Превращает SourceForge-страницу /download в прямую ссылку зеркала."""
        if not candidate:
            return None
        candidate = candidate.strip()
        lowered = candidate.lower()
        if "sourceforge.net/projects/" in lowered and "/download" in lowered:
            direct = self._sourceforge_direct(candidate)
            if direct:
                return direct
            # SourceForge понимает use_mirror=autoselect и сам редиректит
            # на ближайшее зеркало — файл качается напрямую в программе.
            separator = "&" if "?" in candidate else "?"
            return f"{candidate}{separator}use_mirror=autoselect"
        return candidate

    # ------------------------------------------------------------------
    # LineageOS API
    # ------------------------------------------------------------------
    def _resolve_lineage(self, codename: str) -> str | None:
        """Берёт ссылку на .zip последней сборки из официального API LineageOS.

        API v2 отдаёт список сборок (сначала самые свежие), у каждой —
        список файлов. Берём последний файл самой свежей сборки, как на
        странице https://lineageos.org/api/v2/devices/<codename>/builds.
        """
        if not codename:
            return None
        safe = urllib.parse.quote(codename.strip(), safe="")
        for template in self.LINEAGE_API_TEMPLATES:
            api = template.format(codename=safe)
            data = self._fetch_json(api)
            if not data:
                continue
            # Новый формат API v2: [{"files": [{"url": ...}, ...]}, ...]
            builds = data if isinstance(data, list) else [data]
            for build in builds:
                if not isinstance(build, dict):
                    continue
                files = build.get("files")
                if not isinstance(files, list) or not files:
                    continue
                for item in reversed(files):
                    link = item.get("url") if isinstance(item, dict) else item
                    if self._is_archive_url(link):
                        return self._normalize_direct(str(link).strip())
            # Запасной разбор JSON любой структуры.
            found = self._find_archive_in_json(data)
            if found:
                return self._normalize_direct(found)
        # Если API недоступен — разбираем обычную страницу устройства.
        page = self._fetch_text_fallback(
            f"https://download.lineageos.org/devices/{safe}",
            "text/html,application/xhtml+xml", timeout=25,
        )
        return self._find_archive_in_html(page, "https://download.lineageos.org")

    def _resolve_rom_api(self, codename: str) -> str | None:
        """PixelExperience / ArrowOS / Paranoid Android: API и JSON сборок."""
        if not codename:
            return None
        safe = urllib.parse.quote(codename.strip(), safe="")
        for template in self.ROM_API_TEMPLATES:
            api = template.format(codename=safe)
            data = self._fetch_json(api, timeout=15)
            found = self._find_archive_in_json(data) if data else None
            if found:
                return self._normalize_direct(found)
        return None

    # ------------------------------------------------------------------
    # SourceForge RSS (crDroid, Evolution X, PixelOS, RisingOS, Xiaomi.eu)
    # ------------------------------------------------------------------
    @staticmethod
    def _rss_value(block: str, tag: str) -> str:
        match = re.search(
            rf"<{tag}>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</{tag}>",
            block, re.IGNORECASE | re.DOTALL,
        )
        return html.unescape(match.group(1).strip()) if match else ""

    @staticmethod
    def _curl_text(url: str, timeout: int = 25) -> str:
        """Запасной HTTP-клиент через curl.exe (есть в Windows 10/11).

        SourceForge иногда отвечает 403 на urllib из-за проверки Cloudflare,
        поэтому страницу загрузки читаем системным curl.
        """
        curl = os.path.join(
            os.environ.get("SystemRoot", r"C:\Windows"), "System32", "curl.exe"
        )
        if not os.path.isfile(curl):
            return ""
        try:
            result = subprocess.run(
                [
                    curl, "-sSL", "--max-time", str(timeout),
                    "-A", FirmwareDownloader.USER_AGENT, url,
                ],
                capture_output=True,
                timeout=timeout + 5,
                creationflags=popen_flags(),
            )
        except Exception:  # noqa: BLE001
            return ""
        if result.returncode != 0 or not result.stdout:
            return ""
        return result.stdout.decode("utf-8", "replace")

    @staticmethod
    def _powershell_path() -> str:
        powershell = os.path.join(
            os.environ.get("SystemRoot", r"C:\Windows"),
            "System32", "WindowsPowerShell", "v1.0", "powershell.exe",
        )
        return powershell if os.path.isfile(powershell) else "powershell.exe"

    @classmethod
    def _powershell_text(cls, url: str, timeout: int = 30) -> str:
        """Третий запасной клиент: Invoke-WebRequest через PowerShell.

        Cloudflare на SourceForge пропускает .NET HttpClient, но блокирует
        urllib и curl, поэтому используем системный PowerShell.
        """
        powershell = cls._powershell_path()
        safe_url = url.replace("'", "%27")
        script = (
            "$ProgressPreference='SilentlyContinue'; "
            f"$r=Invoke-WebRequest -UseBasicParsing -Uri '{safe_url}' "
            f"-TimeoutSec {max(5, timeout - 5)}; "
            "[Console]::OutputEncoding=[Text.Encoding]::UTF8; $r.Content"
        )
        try:
            result = subprocess.run(
                [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                timeout=timeout + 10,
                creationflags=popen_flags(),
            )
        except Exception:  # noqa: BLE001
            return ""
        if result.returncode != 0 or not result.stdout:
            return ""
        for encoding in ("utf-8", "cp1251", "cp866"):
            try:
                return result.stdout.decode(encoding)
            except UnicodeDecodeError:
                continue
        return result.stdout.decode("utf-8", "replace")

    @staticmethod
    def _extract_sourceforge_direct(page: str) -> str | None:
        if not page:
            return None
        for pattern in (
            r"url=(https?://downloads\.sourceforge\.net/[^\"'<>\s]+)",
            r"data-release-url=[\"'](https?://[^\"']+)[\"']",
        ):
            match = re.search(pattern, page, re.IGNORECASE)
            if match:
                candidate = html.unescape(match.group(1)).strip()
                if candidate.lower().startswith("http"):
                    return candidate
        return None

    def _sourceforge_direct(self, download_url: str) -> str | None:
        """Достаёт из страницы SourceForge ссылку на зеркало с токеном."""
        page = self._fetch_text_fallback(
            download_url, "text/html,application/xhtml+xml",
            limit=1024 * 1024, timeout=25,
        )
        return self._extract_sourceforge_direct(page)

    def _sourceforge_items(self, project: str, path: str) -> list[tuple[str, str]]:
        """Возвращает [(title, link), ...] из RSS-ленты папки SourceForge."""
        rss = (
            "https://sourceforge.net/projects/"
            f"{urllib.parse.quote(project, safe='')}/rss?path="
            f"{urllib.parse.quote(path, safe='/')}"
        )
        xml = self._fetch_text_fallback(
            rss, "application/rss+xml, application/xml, text/xml", timeout=25
        )
        if not xml:
            return []
        items: list[tuple[str, str]] = []
        for block in self.SOURCEFORGE_ITEM_RE.findall(xml):
            link = self._rss_value(block, "link")
            title = self._rss_value(block, "title")
            if not link:
                continue
            link = html.unescape(link).strip()
            if not self._is_archive_url(link) or self._is_excluded(link):
                continue
            items.append((title, link))
        return items

    def _sourceforge_files_page(self, project: str, codename: str) -> list[str]:
        """Разбирает HTML-список файлов папки устройства на SourceForge."""
        if not codename:
            return []
        safe_project = urllib.parse.quote(project, safe="")
        safe_code = urllib.parse.quote(codename.strip().strip("/"), safe="")
        page = self._fetch_text_fallback(
            f"https://sourceforge.net/projects/{safe_project}/files/{safe_code}/",
            "text/html,application/xhtml+xml", timeout=25,
        )
        if not page:
            return []
        pattern = re.compile(
            rf"https?://(?:www\.)?sourceforge\.net/projects/"
            rf"{re.escape(project)}/files/[^\"'<>\s]+?/download",
            re.IGNORECASE,
        )
        links: list[str] = []
        for link in pattern.findall(page):
            link = html.unescape(link).strip()
            if self._is_archive_url(link) and not self._is_excluded(link):
                if link not in links:
                    links.append(link)
        return links

    def _resolve_sourceforge(self, project: str, codename: str) -> str | None:
        """Ищет самый свежий архив в RSS SourceForge по codename."""
        paths: list[str] = []
        if codename:
            code = codename.strip().strip("/")
            paths.extend([f"/{code}", f"/{code}/"])
        paths.append("/")

        candidates: list[str] = []
        for path in paths:
            items = self._sourceforge_items(project, path)
            if not items:
                continue
            for title, link in items:
                if path == "/" and codename:
                    haystack = f"{title} {link}".lower()
                    if codename.strip().lower() not in haystack:
                        continue
                if link not in candidates:
                    candidates.append(link)
            # RSS отдаёт файлы от новых к старым — первый и есть самый свежий.
            if candidates:
                break

        if not candidates:
            candidates = self._sourceforge_files_page(project, codename)

        if not candidates:
            return None
        return self._normalize_direct(candidates[0])

    # ------------------------------------------------------------------
    # Xiaomi / Redmi / POCO (HyperOS, MIUI, Xiaomi.eu)
    # ------------------------------------------------------------------
    def _xiaomi_from_tracker(self, codename: str) -> list[str]:
        """Разбирает YAML-трекер MiFirmware: codename, дата и прямая ссылка."""
        code = codename.strip().lower()
        if not code:
            return []
        for tracker in self.XIAOMI_TRACKER_URLS:
            text = self._fetch_text_fallback(
                tracker, "text/plain, application/x-yaml, */*", timeout=20,
            )
            if not text:
                continue
            entries: list[tuple[str, str]] = []
            for block in re.split(r"(?m)^-\s+", text):
                if f"codename: {code}" not in block.lower():
                    continue
                link_match = re.search(r"(?m)^\s*link:\s*(\S+)", block)
                if not link_match:
                    continue
                link = link_match.group(1).strip("'\"")
                if not self._is_archive_url(link) or self._is_excluded(link):
                    continue
                date_match = re.search(r"(?m)^\s*date:\s*(\S+)", block)
                date = date_match.group(1).strip("'\"") if date_match else ""
                entries.append((date, link))
            if entries:
                entries.sort(key=lambda item: item[0], reverse=True)
                return [link for _date, link in entries]
        return []

    def _resolve_xiaomi(self, codename: str) -> str | None:
        """Находит прямую ссылку на прошивку Xiaomi по codename устройства."""
        if not codename:
            return None
        safe = urllib.parse.quote(codename.strip(), safe="")
        candidates: list[str] = []

        # 1) GitHub-трекер MiFirmware: выбираем самый свежий билд по дате.
        candidates = self._xiaomi_from_tracker(codename)
        if candidates:
            return candidates[0]

        # 2) Страницы зеркал xiaomifirmwareupdater.com / miuirom.org.
        for template in self.XIAOMI_PAGE_TEMPLATES:
            page_url = template.format(codename=safe)
            page = self._fetch_text_fallback(
                page_url, "text/html,application/xhtml+xml", timeout=20,
            )
            if not page:
                continue
            for link in self.XIAOMI_MIRROR_RE.findall(page):
                link = html.unescape(link).strip()
                if link not in candidates and not self._is_excluded(link):
                    candidates.append(link)
            if candidates:
                break
            # Запасной разбор любых ссылок на архивы внутри страницы.
            for link in self.HTML_LINK_RE.findall(page):
                link = link.strip()
                if link.startswith("//"):
                    link = "https:" + link
                elif not link.lower().startswith(("http://", "https://")):
                    link = urllib.parse.urljoin(page_url, link)
                if (self._is_archive_url(link) and not self._is_excluded(link)
                        and codename.strip().lower() in link.lower()
                        and link not in candidates):
                    candidates.append(link)
            if candidates:
                break

        if not candidates:
            return None
        # На страницах Xiaomi новые сборки идут первыми.
        return candidates[0]

    def _codename(self) -> str:
        """Codename устройства: из каталога, а если нет — из ссылки."""
        code = str(self.firmware.get("codename") or "").strip()
        if code:
            return code
        for key in ("download_url", "page_url"):
            url = str(self.firmware.get(key) or "")
            match = re.search(
                r"(?:/devices/|/downloads/|crdroid\.net/|pixelos\.net/|"
                r"evolution-x\.org/downloads/)([A-Za-z0-9._-]+)",
                url, re.IGNORECASE,
            )
            if match:
                return match.group(1)
        return ""

    def _sourceforge_from_url(self, url: str) -> str | None:
        """Резолвит обычную страницу проекта SourceForge."""
        match = re.match(
            r"^https?://(?:www\.)?sourceforge\.net/projects/([^/]+)/files(?:/(.*))?$",
            url, re.IGNORECASE,
        )
        if not match:
            return None
        project = match.group(1)
        path = (match.group(2) or "").strip("/")
        codename = self._codename()
        if path and path.lower() not in {"latest", "files"}:
            codename = path.split("/")[0]
        return self._resolve_sourceforge(project, codename)

    # ------------------------------------------------------------------
    # GitHub Releases и OTA-JSON
    # ------------------------------------------------------------------
    def _github_assets(self, data) -> str | None:
        assets = data.get("assets") if isinstance(data, dict) else None
        if not isinstance(assets, list):
            return None
        candidates: list[str] = []
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            link = asset.get("browser_download_url")
            name = str(asset.get("name") or link or "").lower()
            if isinstance(link, str) and name.endswith(self.FILE_EXTENSIONS):
                candidates.append(link)
        if not candidates:
            return None
        candidates.sort(
            key=lambda item: (0 if item.lower().endswith(".zip") else 1, len(item))
        )
        return candidates[0]

    def _resolve_github(self, url: str) -> str | None:
        match = self.GITHUB_RE.match(url)
        if not match:
            return None
        owner, repo, tag = match.groups()
        if "/releases/download/" in url:
            return None
        apis: list[str] = []
        if tag:
            apis.append(
                f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
            )
        apis.append(f"https://api.github.com/repos/{owner}/{repo}/releases/latest")
        for api in apis:
            data = self._fetch_json(api)
            found = self._github_assets(data) if data else None
            if found:
                return found
        releases = self._fetch_json(
            f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=10"
        )
        if isinstance(releases, list):
            for release in releases:
                found = self._github_assets(release)
                if found:
                    return found
        return None

    def _resolve_ota_json(self, repos, branches, codename: str) -> str | None:
        """Читает OTA-JSON кастомной прошивки из GitHub и берёт ссылку на .zip."""
        if not codename:
            return None
        codename = codename.strip()
        for repo in repos:
            for branch in branches:
                for template in ("{codename}.json", "builds/{codename}.json"):
                    path = template.format(codename=codename)
                    api = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
                    data = self._fetch_json(api, timeout=8)
                    found = self._find_archive_in_json(data) if data else None
                    if found:
                        return self._normalize_direct(found)
        return None

    # ------------------------------------------------------------------
    # Разбор HTML как последний шанс
    # ------------------------------------------------------------------
    def _page_needs_browser(self, page: str) -> bool:
        """True, если страница защищена капчей или требует входа."""
        lowered = (page or "").lower()
        return any(marker in lowered for marker in self.CAPTCHA_MARKERS)

    def _find_archive_in_html(self, page: str, base_url: str) -> str | None:
        """Универсальный парсер: ищет на странице ссылку на архив прошивки."""
        if not page:
            return None

        # 1) SourceForge-ссылки на файл внутри страницы.
        for link in self.SOURCEFORGE_FILE_LINK_RE.findall(page):
            link = html.unescape(link).strip()
            if self._is_excluded(link):
                continue
            direct = self._sourceforge_direct(link)
            if direct:
                return direct
            separator = "&" if "?" in link else "?"
            return f"{link}{separator}use_mirror=autoselect"

        # 2) Прямые архивы в href/src/data-url (включая относительные пути).
        for candidate in self.HTML_LINK_RE.findall(page):
            candidate = html.unescape(candidate).strip()
            if candidate.startswith("//"):
                candidate = "https:" + candidate
            elif not candidate.lower().startswith(("http://", "https://")):
                candidate = urllib.parse.urljoin(base_url, candidate)
            if self._is_archive_url(candidate) and not self._is_excluded(candidate):
                return self._normalize_direct(candidate)

        # 3) Ссылки, спрятанные в JSON/JS (в том числе с экранированием \/).
        for candidate in self.ESCAPED_LINK_RE.findall(page):
            candidate = html.unescape(candidate).replace("\\/", "/").strip()
            if (self._is_archive_url(candidate)
                    and not self._is_excluded(candidate)):
                return self._normalize_direct(candidate)

        # 4) Любые «голые» URL на странице (кнопки Download, CDN-ссылки).
        for candidate in re.findall(r"https?://[^\"'<>\s]+", page):
            candidate = html.unescape(candidate).rstrip(").,;")
            if self._is_archive_url(candidate) and not self._is_excluded(candidate):
                return self._normalize_direct(candidate)
        return None

    def _resolve_html(self, url: str) -> str | None:
        page = self._fetch_text_fallback(
            url, "text/html,application/xhtml+xml",
            limit=2 * 1024 * 1024, timeout=25,
        )
        if not page:
            return None
        if self._page_needs_browser(page):
            self.fallback_reason = (
                "сайт защищён капчей или требует входа в аккаунт"
            )
            return None
        return self._find_archive_in_html(page, url)

    def resolve_url(self, url: str) -> str | None:
        """Возвращает прямую ссылку на архив или None, если её не найти.

        Порядок: прямой файл -> GitHub -> Xiaomi -> LineageOS -> другие
        API -> SourceForge по названию прошивки -> SourceForge из URL ->
        OTA-JSON -> универсальный разбор HTML.
        """
        self.fallback_reason = ""
        if self.is_direct_url(url):
            return url

        codename = self._codename()
        os_name = str(self.firmware.get("os") or "").strip().lower()
        brand = str(self.firmware.get("brand") or "").strip().lower()
        haystack = f"{os_name} {brand} {url}".lower()

        github = self._resolve_github(url)
        if github:
            return github

        is_xiaomi = (
            "xiaomi.eu" not in os_name
            and "xiaomi-eu" not in haystack
            and (
                "hyperos" in os_name
                or "miui" in os_name
                or "xiaomifirmwareupdater" in haystack
                or "miuirom.org" in haystack
            )
        )
        if is_xiaomi:
            found = self._resolve_xiaomi(codename)
            if found:
                return found

        if "lineage" in haystack:
            found = self._resolve_lineage(codename)
            if found:
                return found

        if any(key in haystack for key in (
            "pixelexperience", "pixel experience", "arrowos", "arrow os",
            "paranoid", "aospa",
        )):
            found = self._resolve_rom_api(codename)
            if found:
                return found

        for key, projects in self.SOURCEFORGE_OS_PROJECTS.items():
            if key in haystack:
                for project in projects:
                    found = self._resolve_sourceforge(project, codename)
                    if found:
                        return found

        found = self._sourceforge_from_url(url)
        if found:
            return found

        for key, (repos, branches) in self.OTA_JSON_SOURCES.items():
            if key in haystack:
                found = self._resolve_ota_json(repos, branches, codename)
                if found:
                    return found

        return self._resolve_html(url)

    # ------------------------------------------------------------------
    # Скачивание
    # ------------------------------------------------------------------
    @staticmethod
    def _filename(url: str, firmware: dict) -> str:
        path = urllib.parse.urlparse(url).path.rstrip("/")
        if path.lower().endswith("/download"):
            path = path[: -len("/download")]
        name = os.path.basename(urllib.parse.unquote(path))
        if not name or "." not in name:
            name = f"{firmware.get('id', 'firmware')}.zip"
        name = re.sub(r'[<>:"/\\|?*]', "_", name)
        return name or "firmware.zip"

    @staticmethod
    def _unique_path(directory: str, filename: str) -> str:
        target = os.path.join(directory, filename)
        if not os.path.exists(target):
            return target
        stem, extension = os.path.splitext(filename)
        index = 1
        while os.path.exists(os.path.join(directory, f"{stem} ({index}){extension}")):
            index += 1
        return os.path.join(directory, f"{stem} ({index}){extension}")

    @staticmethod
    def _remove_quietly(path: str) -> None:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError:
            pass

    def _run(self) -> None:
        url = self.firmware.get("download_url") or self.firmware.get("page_url") or ""
        if not url:
            self._emit(self.on_error, "в каталоге нет ссылки на прошивку")
            return

        if self.cancel_event.is_set():
            self._emit(self.on_cancel)
            return

        self._emit(self.on_status, "resolving")
        try:
            direct = self.resolve_url(url)
        except Exception:  # noqa: BLE001
            direct = None

        if self.cancel_event.is_set():
            self._emit(self.on_cancel)
            return

        if not direct:
            reason = self.fallback_reason or (
                "ни один источник не отдал прямую ссылку на файл"
            )
            self._emit(self.on_fallback, url, reason)
            return

        self._emit(self.on_status, "resolved", direct)
        self._emit(self.on_status, "downloading")
        try:
            self._download(direct)
        except DownloadCancelled:
            self._emit(self.on_cancel)
        except Exception as exc:  # noqa: BLE001
            self._emit(self.on_error, str(exc))

    @staticmethod
    def _curl_path() -> str:
        curl = os.path.join(
            os.environ.get("SystemRoot", r"C:\Windows"), "System32", "curl.exe"
        )
        return curl if os.path.isfile(curl) else ""

    def _download(self, url: str) -> None:
        os.makedirs(FIRMWARE_DOWNLOAD_DIR, exist_ok=True)
        filename = self._filename(url, self.firmware)
        target = self._unique_path(FIRMWARE_DOWNLOAD_DIR, filename)
        temp = target + ".part"

        self.downloaded = 0
        self.total = 0
        self.speed = 0.0

        try:
            self._download_with_urllib(url, temp, target)
        except DownloadCancelled:
            self._remove_quietly(temp)
            raise
        except Exception as urllib_error:  # noqa: BLE001
            self._remove_quietly(temp)
            if not self._curl_path():
                raise
            # Cloudflare на SourceForge отдаёт 403 urllib, но пропускает curl.
            try:
                self._download_with_curl(url, temp, target)
            except DownloadCancelled:
                self._remove_quietly(temp)
                raise
            except Exception as curl_error:  # noqa: BLE001
                self._remove_quietly(temp)
                raise RuntimeError(
                    f"{urllib_error}; через curl: {curl_error}"
                ) from curl_error

        if self.total <= 0:
            self.total = self.downloaded
        self.path = target
        self._emit(self.on_progress, self.downloaded, self.total, self.speed)
        self._emit(self.on_done, target)

    def _download_with_urllib(self, url: str, temp: str, target: str) -> None:
        last_time = time.time()
        last_bytes = 0
        request = self._request(url, "*/*")
        with urllib.request.urlopen(request, timeout=30) as response, \
                open(temp, "wb") as output:
            content_type = (response.headers.get("Content-Type") or "").lower()
            if "text/html" in content_type:
                raise RuntimeError(
                    "сервер вернул HTML-страницу вместо архива "
                    "(ссылка устарела или требует входа на сайт)"
                )
            self.total = int(response.headers.get("Content-Length") or 0)
            self._emit(self.on_progress, 0, self.total, 0.0)

            while True:
                if self.cancel_event.is_set():
                    raise DownloadCancelled()
                chunk = response.read(self.CHUNK_SIZE)
                if not chunk:
                    break
                output.write(chunk)
                self.downloaded += len(chunk)
                now = time.time()
                if now - last_time >= 0.2:
                    instant = (self.downloaded - last_bytes) / max(
                        now - last_time, 1e-6
                    )
                    self.speed = (
                        instant if self.speed <= 0
                        else self.speed * 0.6 + instant * 0.4
                    )
                    last_time = now
                    last_bytes = self.downloaded
                    self._emit(self.on_progress, self.downloaded,
                               self.total, self.speed)

        if self.cancel_event.is_set():
            raise DownloadCancelled()
        if self.downloaded <= 0:
            raise RuntimeError("скачанный файл пустой")
        if self.total <= 0:
            self.total = self.downloaded
        os.replace(temp, target)

    def _curl_remote_size(self, url: str) -> int:
        """Узнаёт размер файла через curl (HEAD или Range-запрос)."""
        curl = self._curl_path()
        if not curl:
            return 0
        attempts = (
            [curl, "-sS", "-L", "-r", "0-0", "-D", "-", "-o", os.devnull,
             "--max-time", "30", "-A", self.USER_AGENT, url],
            [curl, "-sSIL", "--max-time", "30", "-A", self.USER_AGENT, url],
        )
        for command in attempts:
            try:
                result = subprocess.run(
                    command, capture_output=True, timeout=45,
                    creationflags=popen_flags(),
                )
            except Exception:  # noqa: BLE001
                continue
            text = result.stdout.decode("latin-1", "replace")
            types = re.findall(r"(?im)^content-type:\s*([^\r\n]+)", text)
            if types and "text/html" in types[-1].lower():
                continue
            ranges = re.findall(
                r"(?im)^content-range:\s*bytes\s+\d+-\d+/(\d+)", text
            )
            if ranges:
                return int(ranges[-1])
            sizes = re.findall(r"(?im)^content-length:\s*(\d+)", text)
            if sizes:
                return int(sizes[-1])
        return 0

    def _download_with_curl(self, url: str, temp: str, target: str) -> None:
        """Скачивание системным curl с живым прогрессом по размеру файла."""
        curl = self._curl_path()
        if not curl:
            raise RuntimeError("curl.exe не найден")
        self.total = self._curl_remote_size(url)
        self._emit(self.on_progress, 0, self.total, 0.0)

        process = subprocess.Popen(
            [
                curl, "-sS", "-L", "--fail", "--retry", "2",
                "--retry-delay", "2", "--connect-timeout", "30",
                "-A", self.USER_AGENT, "-o", temp, url,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=popen_flags(),
        )
        last_time = time.time()
        last_bytes = 0
        try:
            while True:
                if self.cancel_event.is_set():
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except Exception:  # noqa: BLE001
                        process.kill()
                    raise DownloadCancelled()

                size = os.path.getsize(temp) if os.path.exists(temp) else 0
                self.downloaded = size
                now = time.time()
                if now - last_time >= 0.2:
                    instant = (size - last_bytes) / max(now - last_time, 1e-6)
                    self.speed = (
                        instant if self.speed <= 0
                        else self.speed * 0.6 + instant * 0.4
                    )
                    last_time = now
                    last_bytes = size
                    self._emit(self.on_progress, size, self.total, self.speed)

                if process.poll() is not None:
                    break
                time.sleep(0.1)
        except DownloadCancelled:
            raise
        except Exception:
            process.terminate()
            raise

        error = b""
        if process.stderr is not None:
            try:
                error = process.stderr.read() or b""
            except Exception:  # noqa: BLE001
                error = b""
        if process.returncode != 0:
            message = error.decode("utf-8", "replace").strip()
            raise RuntimeError(
                message or f"curl завершился с кодом {process.returncode}"
            )

        final_size = os.path.getsize(temp) if os.path.exists(temp) else 0
        if final_size <= 0:
            raise RuntimeError("скачанный файл пустой")
        if self.total <= 0:
            self.total = final_size
        self.downloaded = final_size
        os.replace(temp, target)


class SplashScreen:
    """Анимированная заставка при запуске программы."""

    WIDTH = 420
    HEIGHT = 260
    DURATION = 1.8

    def __init__(self, master: "KitagawaUtilitsApp") -> None:
        self.master = master
        self._started = time.time()
        self._closed = False
        self._icon_size = 0
        self._pil_icon = None
        self._icon_image = None

        self.window = tk.Toplevel(master)
        self.window.overrideredirect(True)
        self.window.configure(bg=COLOR_ACCENT)
        try:
            self.window.attributes("-alpha", 0.0)
            self.window.attributes("-topmost", True)
        except tk.TclError:
            pass

        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        left = max(0, (screen_width - self.WIDTH) // 2)
        top = max(0, (screen_height - self.HEIGHT) // 2)
        self.window.geometry(f"{self.WIDTH}x{self.HEIGHT}+{left}+{top}")

        # Коралловая рамка толщиной 2 пикселя вокруг темного корпуса.
        border = tk.Frame(self.window, bg=COLOR_ACCENT)
        border.pack(fill="both", expand=True)

        body = ctk.CTkFrame(border, fg_color="#16181D", corner_radius=16)
        body.pack(fill="both", expand=True, padx=2, pady=2)
        body.grid_columnconfigure(0, weight=1)

        self.icon_label = ctk.CTkLabel(body, text="")
        self.icon_label.grid(row=0, column=0, pady=(24, 6))

        ctk.CTkLabel(
            body,
            text=APP_NAME,
            font=ui_font(size=24, weight="bold"),
            text_color=COLOR_TEXT,
        ).grid(row=1, column=0)

        ctk.CTkLabel(
            body,
            text=t("splash_subtitle"),
            font=ui_font(size=11),
            text_color=COLOR_MUTED,
        ).grid(row=2, column=0, pady=(4, 16))

        self.progress = ctk.CTkProgressBar(
            body,
            width=330,
            height=10,
            corner_radius=5,
            fg_color="#2A2D35",
            progress_color=COLOR_ACCENT,
        )
        self.progress.grid(row=3, column=0)
        self.progress.set(0)

        ctk.CTkLabel(
            body,
            text=f"v{APP_VERSION}",
            font=ui_font(size=10),
            text_color="#6B6B72",
        ).grid(row=4, column=0, pady=(10, 16))

        self._load_icon()
        self.window.after(30, self._tick)

    # ------------------------------------------------------------------
    # Иконка
    # ------------------------------------------------------------------
    def _load_icon(self) -> None:
        path = resource_path("app.ico")
        if Image is not None and os.path.isfile(path):
            try:
                image = Image.open(path)
                image.load()
                self._pil_icon = image
            except Exception:  # noqa: BLE001
                self._pil_icon = None

        if self._pil_icon is not None:
            self._apply_icon(84)
        else:
            self.icon_label.configure(
                text="⚡",
                font=ui_font(size=52, weight="bold"),
                text_color=COLOR_ACCENT,
            )

    def _apply_icon(self, size: int) -> None:
        if self._pil_icon is None or size == self._icon_size:
            return
        self._icon_size = size
        image = ctk.CTkImage(
            light_image=self._pil_icon,
            dark_image=self._pil_icon,
            size=(size, size),
        )
        self.icon_label.configure(image=image)
        self._icon_image = image

    # ------------------------------------------------------------------
    # Анимация
    # ------------------------------------------------------------------
    def _tick(self) -> None:
        if self._closed:
            return

        elapsed = time.time() - self._started
        if elapsed >= self.DURATION:
            self._close()
            return

        # Плавное появление, ровное свечение и мягкое затухание.
        if elapsed < 0.45:
            alpha = elapsed / 0.45
        elif elapsed > 1.45:
            alpha = max(0.0, 1.0 - (elapsed - 1.45) / 0.35)
        else:
            alpha = 1.0
        try:
            self.window.attributes("-alpha", max(0.0, min(1.0, alpha)))
        except tk.TclError:
            pass

        progress = max(0.0, min(1.0, (elapsed - 0.08) / 1.3))
        self.progress.set(progress)

        # Легкая пульсация иконки во время заполнения прогресс-бара.
        if self._pil_icon is not None and progress < 1.0:
            pulse = int(round(85 + 5 * math.sin(elapsed * 10.0)))
            self._apply_icon(pulse)

        self.window.after(30, self._tick)

    def _close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.window.destroy()
        except tk.TclError:
            pass
        self.master._on_splash_finished()


class KitagawaUtilitsApp(ctk.CTk):
    """Главное окно приложения."""

    def __init__(self) -> None:
        enable_high_dpi()
        super().__init__()

        ctk.set_appearance_mode("dark")
        self.title(APP_TITLE)
        try:
            self.iconbitmap(resource_path("app.ico"))
        except Exception:  # noqa: BLE001
            pass
        self.geometry("1240x880")
        self.minsize(1080, 740)
        self.configure(fg_color=COLOR_BG)

        # Пока играет заставка, главное окно скрыто.
        self.withdraw()
        self._splash: SplashScreen | None = None

        # Очередь логов: рабочие потоки -> UI-поток.
        self._log_queue: "queue.Queue[tuple[str, str]]" = queue.Queue()
        self._busy = 0
        self._busy_lock = threading.Lock()
        self._status_thread: threading.Thread | None = None
        self._last_connection_state: bool | None = None
        self._watch_started = False

        self._img_path: str | None = None
        self._zip_path: str | None = None
        self._checksum_path: str | None = None
        self._log_collapsed = False

        # Данные для вкладки очистки.
        self._all_packages: list[str] = []
        self._scan_packages: list[str] = []
        self._cleanup_vars: dict[str, tk.BooleanVar] = {}

        self._firmwares_error: str | None = None
        self._firmwares_source: str | None = None
        self.firmwares = self._load_firmwares()
        self.brands = self._build_brand_order()

        self._action_widgets: list[ctk.CTkBaseClass] = []
        self.pages: dict[str, ctk.CTkFrame] = {}
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        self._current_page = "catalog"

        # Автопроверка обновлений на GitHub.
        self._update_info: dict | None = None
        self._update_button: ctk.CTkButton | None = None
        # Быстрый бэкап.
        self._backup_button: ctk.CTkButton | None = None
        self._backup_progress: ctk.CTkProgressBar | None = None
        self._backup_status: ctk.CTkLabel | None = None

        self._build_ui()
        self._configure_log_tags()

        self.after(100, self._drain_log_queue)
        self.show_page("catalog")
        self._initial_logs()
        self._start_connection_watch()
        self.after(1500, self._check_updates_async)

        # Заставка запускается после сборки интерфейса и сама откроет окно.
        try:
            self._splash = SplashScreen(self)
        except Exception:  # noqa: BLE001
            self._splash = None
            self.deiconify()

    def _on_splash_finished(self) -> None:
        """Заставка завершила анимацию — показываем главное окно."""
        self._splash = None
        self.deiconify()
        self.lift()
        try:
            self.focus_force()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # Автопроверка обновлений с GitHub
    # ------------------------------------------------------------------
    @staticmethod
    def _version_tuple(value: str) -> tuple[int, ...]:
        numbers = re.findall(r"\d+", (value or "").lstrip("vV"))
        return tuple(int(item) for item in numbers) or (0,)

    def _check_updates_async(self) -> None:
        threading.Thread(target=self._check_updates_worker, daemon=True).start()

    def _check_updates_worker(self) -> None:
        try:
            request = urllib.request.Request(
                GITHUB_RELEASE_API,
                headers={
                    "User-Agent": f"{APP_NAME}/{APP_VERSION}",
                    "Accept": "application/vnd.github+json",
                },
            )
            with urllib.request.urlopen(request, timeout=12) as response:
                data = json.loads(response.read(512 * 1024).decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001
            return
        if not isinstance(data, dict):
            return
        tag = str(data.get("tag_name") or "").strip()
        url = str(data.get("html_url") or "").strip()
        if not tag or not url:
            return
        if self._version_tuple(tag) <= self._version_tuple(APP_VERSION):
            return
        self._update_info = {"tag": tag, "url": url}
        self.after(0, self._show_update_button)

    def _show_update_button(self) -> None:
        if not self._update_info:
            return
        try:
            if self._update_button is not None:
                self._update_button.pack(fill="x", padx=12, pady=(14, 4))
                self._update_button.lift()
        except Exception:  # noqa: BLE001
            pass
        self.log(
            f"Доступно обновление {self._update_info['tag']} — "
            "кнопка «🚀 Доступно обновление» в левом меню.",
            "ok",
        )

    def _open_update(self) -> None:
        if not self._update_info:
            return
        try:
            webbrowser.open(self._update_info["url"])
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # Загрузка каталога
    # ------------------------------------------------------------------
    def _load_firmwares(self) -> list[dict]:
        """Сначала свежий кэш из LOCALAPPDATA, затем встроенный каталог."""
        errors: list[str] = []
        for path in (FIRMWARES_CACHE_FILE, FIRMWARES_FILE):
            items = self._read_catalog_file(path, errors)
            if items is not None:
                self._firmwares_source = path
                self._firmwares_error = None
                return items
        self._firmwares_error = "; ".join(errors) or "файл каталога не найден"
        return []

    @staticmethod
    def _read_catalog_file(path: str, errors: list[str]) -> list[dict] | None:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            return None
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{os.path.basename(path)}: {exc}")
            return None

        items = data.get("firmwares", []) if isinstance(data, dict) else data
        if not isinstance(items, list):
            errors.append(f"{os.path.basename(path)}: поле firmwares должно быть списком")
            return None
        valid = [
            item for item in items
            if isinstance(item, dict) and item.get("brand") and item.get("model")
        ]
        if not valid:
            errors.append(f"{os.path.basename(path)}: каталог пуст")
            return None
        return valid

    def _build_brand_order(self) -> list[str]:
        present: list[str] = []
        for firmware in self.firmwares:
            brand = firmware.get("brand")
            if brand and brand not in present:
                present.append(brand)
        ordered = [brand for brand in PREFERRED_BRANDS if brand in present]
        ordered.extend(brand for brand in present if brand not in ordered)
        return ordered

    def _models_for_brand(self, brand: str) -> list[str]:
        models: list[str] = []
        for firmware in self.firmwares:
            if firmware.get("brand") == brand:
                model = firmware.get("model")
                if model and model not in models:
                    models.append(model)
        return models

    def _initial_logs(self) -> None:
        self.log(f"{APP_NAME} {APP_VERSION} запущен.", "section")
        if self._firmwares_error:
            self.log(f"Не удалось загрузить каталог прошивок: {self._firmwares_error}", "error")
            self.log(f"Ожидался файл: {FIRMWARES_FILE}", "warn")
        else:
            self.log(f"Каталог прошивок загружен: {len(self.firmwares)} записей, "
                     f"{len(self.brands)} брендов.", "ok")
            if self._firmwares_source == FIRMWARES_CACHE_FILE:
                self.log(f"Используется обновлённый кэш каталога: "
                         f"{FIRMWARES_CACHE_FILE}", "ok")
        self._check_tools()
        self.log("Выберите бренд и модель или нажмите «Определить телефон».", "muted")
        self.log("Новичку советуем начать с вкладки «Очистка от рекламы».", "muted")

    # ------------------------------------------------------------------
    # Построение интерфейса
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=0, sticky="nsew")
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        self._build_sidebar(main)

        self.content = ctk.CTkFrame(main, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=18, pady=(18, 8))
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.pages["catalog"] = self._build_catalog_page()
        self.pages["manual"] = self._build_manual_page()
        self.pages["cleanup"] = self._build_cleanup_page()
        self.pages["tools"] = self._build_tools_page()
        self.pages["manage"] = self._build_manage_page()
        self.pages["hardware"] = self._build_hardware_page()
        self.pages["guide"] = self._build_guide_page()
        self.pages["support"] = self._build_support_page()

        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_remove()

        self._build_log_panel()

    # ---------------------------- Боковая панель ----------------------------
    def _build_sidebar(self, parent: ctk.CTkFrame) -> None:
        sidebar = ctk.CTkFrame(
            parent,
            width=268,
            fg_color=COLOR_CARD,
            corner_radius=16,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        sidebar.grid(row=0, column=0, sticky="ns", padx=(18, 0), pady=18)
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(0, weight=1)

        # Прокручиваемая часть: заголовок, статус и кнопки вкладок.
        # Если окно низкое, меню можно прокрутить колесиком мыши.
        scroll = ctk.CTkScrollableFrame(
            sidebar,
            width=240,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_fg_color="transparent",
            scrollbar_button_color=COLOR_CARD_HOVER,
            scrollbar_button_hover_color=COLOR_ACCENT,
        )
        scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 2))
        self._sidebar_scroll = scroll

        ctk.CTkLabel(
            scroll,
            text=APP_NAME,
            font=ui_font(size=21, weight="bold"),
            text_color=COLOR_TEXT,
            wraplength=210,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(20, 0))

        ctk.CTkLabel(
            scroll,
            text=t("version_label"),
            font=ui_font(size=12, weight="bold"),
            text_color=COLOR_ACCENT,
        ).pack(anchor="w", padx=20, pady=(2, 2))

        ctk.CTkLabel(
            scroll,
            text=t("app_subtitle"),
            font=ui_font(size=11),
            text_color=COLOR_MUTED,
            wraplength=210,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(4, 14))

        self.connection_badge = ctk.CTkLabel(
            scroll,
            text=t("conn_waiting"),
            fg_color=COLOR_CARD_HOVER,
            text_color=COLOR_MUTED,
            corner_radius=10,
            height=34,
            width=210,
            font=ui_font(size=12, weight="bold"),
        )
        self.connection_badge.pack(fill="x", padx=14, pady=(0, 12))

        nav_items = [
            ("catalog", t("nav_catalog")),
            ("manual", t("nav_manual")),
            ("cleanup", t("nav_cleanup")),
            ("tools", t("nav_tools")),
            ("manage", t("nav_manage")),
            ("hardware", t("nav_hardware")),
            ("guide", t("nav_guide")),
            ("support", t("nav_support")),
        ]
        for key, label in nav_items:
            button = ctk.CTkButton(
                scroll,
                text=label,
                anchor="w",
                height=44,
                corner_radius=10,
                fg_color="transparent",
                hover_color=COLOR_CARD_HOVER,
                text_color=COLOR_TEXT,
                font=ui_font(size=13, weight="bold"),
                command=lambda page=key: self.show_page(page),
            )
            button.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = button

        # Коралловая кнопка обновления: появляется, если на GitHub есть
        # релиз новее текущей версии.
        self._update_button = ctk.CTkButton(
            scroll,
            text="🚀 Доступно обновление",
            anchor="w",
            height=42,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT,
            font=ui_font(size=13, weight="bold"),
            command=self._open_update,
        )
        self._update_button.pack(fill="x", padx=12, pady=(14, 4))
        if not self._update_info:
            self._update_button.pack_forget()

        # Нижняя закреплённая часть: переключатель 5 языков всегда на виду.
        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", padx=14, pady=(4, 12))
        ctk.CTkFrame(footer, height=1, fg_color=COLOR_BORDER).pack(
            fill="x", pady=(0, 8)
        )

        language_row = ctk.CTkFrame(footer, fg_color="transparent")
        language_row.pack(fill="x")
        ctk.CTkLabel(
            language_row,
            text="🌐",
            font=ui_font(size=14),
            text_color=COLOR_MUTED,
        ).pack(side="left", padx=(4, 6))
        self.language_menu = ctk.CTkOptionMenu(
            language_row,
            values=[label for _code, label in LANGUAGES],
            height=32,
            corner_radius=8,
            fg_color=COLOR_CARD_HOVER,
            button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT_HOVER,
            dropdown_fg_color=COLOR_CARD,
            dropdown_hover_color=COLOR_CARD_HOVER,
            font=ui_font(size=11, weight="bold"),
            dropdown_font=ui_font(size=11),
            command=self.change_language,
        )
        self.language_menu.set(LANGUAGE_LABELS.get(LANG, LANGUAGES[0][1]))
        self.language_menu.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            footer,
            text=f"{APP_TITLE}  ·  Windows 10/11",
            font=ui_font(size=10),
            text_color="#6B6B72",
        ).pack(anchor="w", padx=6, pady=(8, 0))

    def show_page(self, name: str) -> None:
        self._current_page = name
        for key, page in self.pages.items():
            if key == name:
                page.grid()
            else:
                page.grid_remove()
        for key, button in self.nav_buttons.items():
            if key == name:
                button.configure(fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER)
            else:
                button.configure(fg_color="transparent", hover_color=COLOR_CARD_HOVER)

    def change_language(self, label: str) -> None:
        code = LABEL_TO_CODE.get(label)
        if not code or code == LANG:
            return
        set_language(code)
        self._rebuild_interface()

    def _rebuild_interface(self) -> None:
        """Мгновенно пересобирает интерфейс на выбранном языке."""
        current = getattr(self, "_current_page", "catalog")
        for child in list(self.winfo_children()):
            if isinstance(child, tk.Toplevel):
                continue
            child.destroy()
        self.pages = {}
        self.nav_buttons = {}
        self._action_widgets = []
        self._log_collapsed = False
        self._last_connection_state = None
        self._update_button = None
        self._backup_button = None
        self._backup_progress = None
        self._backup_status = None
        self._build_ui()
        self._configure_log_tags()
        self.show_page(current)
        self.log(t("language_changed"), "ok")

    def _make_scroll_page(self) -> ctk.CTkScrollableFrame:
        """Общий контейнер вкладки с прокруткой колесиком мыши."""
        page = ctk.CTkScrollableFrame(
            self.content,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=COLOR_ACCENT,
            scrollbar_button_hover_color=COLOR_ACCENT_HOVER,
        )
        page.grid_columnconfigure(0, weight=1)
        return page

    def _build_hint(self, parent: ctk.CTkFrame, row: int, text: str,
                    pady=(0, 10)) -> None:
        """Плашка «Что здесь происходит и как это работает»."""
        card = ctk.CTkFrame(
            parent,
            fg_color="#1F2128",
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        card.grid(row=row, column=0, sticky="ew", pady=pady)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card,
            text="💡",
            font=ui_font(size=18),
        ).grid(row=0, column=0, rowspan=2, padx=(14, 8), pady=10, sticky="n")

        ctk.CTkLabel(
            card,
            text="Что здесь происходит и как это работает",
            font=ui_font(size=12, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(0, 14), pady=(10, 0))

        ctk.CTkLabel(
            card,
            text=text,
            font=ui_font(size=12),
            text_color="#B9C0CC",
            wraplength=790,
            justify="left",
            anchor="w",
        ).grid(row=1, column=1, sticky="w", padx=(0, 14), pady=(2, 10))

    # ------------------------------ Каталог ------------------------------
    def _build_catalog_page(self) -> ctk.CTkScrollableFrame:
        page = self._make_scroll_page()

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="📦 Прошивки",
            font=ui_font(size=22, weight="bold"),
            text_color=COLOR_TEXT,
        ).grid(row=0, column=0, sticky="w")
        self.catalog_subtitle = ctk.CTkLabel(
            header,
            text=t("catalog_subtitle", firmwares=len(self.firmwares),
                   brands=len(self.brands)),
            font=ui_font(size=12),
            text_color=COLOR_MUTED,
        )
        self.catalog_subtitle.grid(row=1, column=0, sticky="w", pady=(2, 0))

        self._build_hint(
            page,
            1,
            "Здесь лежат официальные прошивки для телефонов. Выберите бренд и модель, "
            "скачайте файл или нажмите «Определить телефон», если смартфон уже подключён "
            "кабелем. Прошивка — это замена системы телефона: делайте её только при "
            "необходимости, зарядив телефон и сохранив фото и контакты.",
        )

        search_card = ctk.CTkFrame(
            page,
            fg_color=COLOR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        search_card.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        search_card.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            search_card,
            height=40,
            corner_radius=10,
            fg_color=COLOR_BG,
            border_color=COLOR_BORDER,
            placeholder_text=t("search_placeholder"),
            font=ui_font(size=13),
            text_color=COLOR_TEXT,
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(16, 8), pady=12)
        self.search_entry.bind("<KeyRelease>", self._on_search_changed)

        ctk.CTkButton(
            search_card,
            text="✕",
            width=40,
            height=40,
            corner_radius=10,
            fg_color=COLOR_CARD_HOVER,
            hover_color="#2A2D35",
            font=ui_font(size=14, weight="bold"),
            command=self._clear_search,
        ).grid(row=0, column=1, padx=(0, 8), pady=12)

        self.catalog_refresh_button = ctk.CTkButton(
            search_card,
            text="🔄 Обновить базу",
            width=170,
            height=40,
            corner_radius=10,
            fg_color=COLOR_CARD_HOVER,
            hover_color="#2A2D35",
            text_color=COLOR_TEXT,
            font=ui_font(size=12, weight="bold"),
            command=self.refresh_catalog,
        )
        self.catalog_refresh_button.grid(row=0, column=2, padx=(0, 16), pady=12)

        filter_card = ctk.CTkFrame(
            page,
            fg_color=COLOR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        filter_card.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        filter_card.grid_columnconfigure(0, weight=1)
        filter_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            filter_card,
            text="Бренд",
            font=ui_font(size=12, weight="bold"),
            text_color=COLOR_MUTED,
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 2))
        ctk.CTkLabel(
            filter_card,
            text="Модель телефона",
            font=ui_font(size=12, weight="bold"),
            text_color=COLOR_MUTED,
        ).grid(row=0, column=1, sticky="w", padx=(8, 18), pady=(14, 2))

        self.brand_menu = ctk.CTkOptionMenu(
            filter_card,
            values=self.brands or ["—"],
            height=38,
            corner_radius=8,
            fg_color=COLOR_CARD_HOVER,
            button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT_HOVER,
            dropdown_fg_color=COLOR_CARD,
            dropdown_hover_color=COLOR_CARD_HOVER,
            font=ui_font(size=13),
            dropdown_font=ui_font(size=13),
            command=self._on_brand_change,
        )
        self.brand_menu.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))

        self.model_menu = ctk.CTkOptionMenu(
            filter_card,
            values=["—"],
            height=38,
            corner_radius=8,
            fg_color=COLOR_CARD_HOVER,
            button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT_HOVER,
            dropdown_fg_color=COLOR_CARD,
            dropdown_hover_color=COLOR_CARD_HOVER,
            font=ui_font(size=13),
            dropdown_font=ui_font(size=13),
            command=self._on_model_change,
        )
        self.model_menu.grid(row=1, column=1, sticky="ew", padx=(8, 18), pady=(0, 10))

        bottom_row = ctk.CTkFrame(filter_card, fg_color="transparent")
        bottom_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 14))
        bottom_row.grid_columnconfigure(0, weight=1)

        self.detect_button = ctk.CTkButton(
            bottom_row,
            text="Определить подключенный телефон автоматически",
            height=38,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ui_font(size=13, weight="bold"),
            command=self.detect_device,
        )
        self.detect_button.grid(row=0, column=0, sticky="w")
        self._action_widgets.append(self.detect_button)

        self.count_label = ctk.CTkLabel(
            bottom_row,
            text="",
            font=ui_font(size=12),
            text_color=COLOR_MUTED,
        )
        self.count_label.grid(row=0, column=1, sticky="e")

        self.cards_frame = ctk.CTkFrame(page, fg_color="transparent")
        self.cards_frame.grid(row=4, column=0, sticky="ew", pady=(0, 8))

        if self.brands:
            self.brand_menu.set(self.brands[0])
            self._on_brand_change(self.brands[0])
        else:
            self._show_catalog_error()

        return page

    def _show_catalog_error(self) -> None:
        for child in self.cards_frame.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self.cards_frame,
            text=("Каталог прошивок недоступен.\n"
                  f"Проверьте файл firmwares.json: {self._firmwares_error or 'нет данных'}"),
            font=ui_font(size=14),
            text_color=COLOR_ERR,
            justify="left",
        ).pack(anchor="w", padx=8, pady=20)

    def _on_brand_change(self, brand: str | None = None) -> None:
        brand = brand or self.brand_menu.get()
        models = self._models_for_brand(brand)
        self.model_menu.configure(values=models or ["—"])
        self.model_menu.set(models[0] if models else "—")
        self._rebuild_cards()

    def _on_model_change(self, _model: str | None = None) -> None:
        self._rebuild_cards()

    def _search_query(self) -> str:
        text = self.search_entry.get().strip()
        if text == t("search_placeholder"):
            return ""
        return text

    def _on_search_changed(self, _event=None) -> None:
        self._rebuild_cards()

    def _clear_search(self) -> None:
        self.search_entry.delete(0, "end")
        self._rebuild_cards()

    # ------------------------------------------------------------------
    # Обновление каталога из интернета
    # ------------------------------------------------------------------
    def _update_catalog_subtitle(self) -> None:
        if not hasattr(self, "catalog_subtitle"):
            return
        self.catalog_subtitle.configure(
            text=t("catalog_subtitle", firmwares=len(self.firmwares),
                   brands=len(self.brands))
        )

    def refresh_catalog(self) -> None:
        if not REMOTE_CATALOG_URL:
            self.log("Облачная ссылка каталога не настроена — используется встроенная база.",
                     "muted")
            messagebox.showinfo(
                "Каталог актуален",
                f"Каталог актуален ({len(self.firmwares)} прошивок).\n\n"
                "Ссылка облачного обновления готова к подключению: укажите адрес "
                "JSON-каталога в переменной REMOTE_CATALOG_URL в main.py.",
                parent=self,
            )
            return
        self._run_task(self._refresh_catalog_worker)

    def _refresh_catalog_worker(self) -> None:
        self.log("=== Обновление каталога прошивок из интернета ===", "section")
        self.log(f"URL: {REMOTE_CATALOG_URL}", "cmd")
        request = urllib.request.Request(
            REMOTE_CATALOG_URL,
            headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
            data = json.loads(raw.decode("utf-8"))
            items = data.get("firmwares", []) if isinstance(data, dict) else data
            if not isinstance(items, list):
                raise ValueError("в ответе нет списка firmwares")
            valid = [
                item for item in items
                if isinstance(item, dict) and item.get("brand") and item.get("model")
            ]
            if len(valid) < 10:
                raise ValueError("в каталоге слишком мало записей")

            os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
            payload = data if isinstance(data, dict) else {"firmwares": valid}
            payload["firmwares"] = valid
            payload["updated"] = time.strftime("%Y-%m-%d")
            temp_path = FIRMWARES_CACHE_FILE + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            os.replace(temp_path, FIRMWARES_CACHE_FILE)

            self.log(f"Скачано записей: {len(valid)}. Кэш сохранён: "
                     f"{FIRMWARES_CACHE_FILE}", "ok")
            self.after(0, lambda: self._apply_catalog(valid, FIRMWARES_CACHE_FILE))
        except Exception as exc:  # noqa: BLE001
            self.log(f"Не удалось обновить каталог: {exc}", "error")
            self.after(0, lambda: messagebox.showwarning(
                "Не удалось обновить каталог",
                "Проверьте подключение к интернету и адрес REMOTE_CATALOG_URL.\n\n"
                f"Причина: {exc}",
                parent=self,
            ))

    def _apply_catalog(self, items: list[dict], source: str) -> None:
        self.firmwares = items
        self.brands = self._build_brand_order()
        self._firmwares_source = source
        self._firmwares_error = None

        if self.brands:
            self.brand_menu.configure(values=self.brands)
            self.brand_menu.set(self.brands[0])
            self._on_brand_change(self.brands[0])
        else:
            self._show_catalog_error()

        self._update_catalog_subtitle()
        self.log(f"Каталог обновлён: {len(items)} записей, {len(self.brands)} брендов.", "ok")
        messagebox.showinfo(
            "Каталог обновлён",
            f"Загружено {len(items)} прошивок для {len(self.brands)} брендов.",
            parent=self,
        )

    @staticmethod
    def _search_blob(firmware: dict) -> str:
        parts = [
            firmware.get("brand", ""),
            firmware.get("model", ""),
            firmware.get("codename", ""),
            firmware.get("os", ""),
            firmware.get("os_version", ""),
            firmware.get("android", ""),
        ]
        return " ".join(str(part) for part in parts).lower()

    def _rebuild_cards(self) -> None:
        for child in self.cards_frame.winfo_children():
            child.destroy()

        query = self._search_query().lower()
        if query:
            entries = [
                firmware for firmware in self.firmwares
                if query in self._search_blob(firmware)
            ]
            self.count_label.configure(text=t("search_results", count=len(entries)))
        else:
            brand = self.brand_menu.get()
            model = self.model_menu.get()
            entries = [
                firmware for firmware in self.firmwares
                if firmware.get("brand") == brand and firmware.get("model") == model
            ]
            self.count_label.configure(text=t("found_firmwares", count=len(entries)))

        if not entries:
            message = (
                t("no_results_query", query=self._search_query())
                if query else t("no_results_device")
            )
            ctk.CTkLabel(
                self.cards_frame,
                text=message,
                font=ui_font(size=13),
                text_color=COLOR_MUTED,
            ).pack(anchor="w", padx=8, pady=20)
            return

        for firmware in entries:
            self._build_firmware_card(firmware)

    def _build_firmware_card(self, firmware: dict) -> None:
        card = ctk.CTkFrame(
            self.cards_frame,
            fg_color=COLOR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        card.pack(fill="x", padx=4, pady=8)
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=0)

        install_type = firmware.get("install_type", "fastboot")
        badge_bg, badge_fg = INSTALL_STYLES.get(install_type, ("#3A3F4B", "#C7CBD4"))

        # ---------------- Левая колонка: информация ----------------
        left = ctk.CTkFrame(card, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(18, 12), pady=16)

        title = f"{firmware.get('os', 'Прошивка')} {firmware.get('os_version', '')}".strip()
        ctk.CTkLabel(
            left,
            text=title,
            font=ui_font(size=17, weight="bold"),
            text_color=COLOR_TEXT,
            wraplength=540,
            justify="left",
        ).pack(anchor="w")

        badges = ctk.CTkFrame(left, fg_color="transparent")
        badges.pack(anchor="w", pady=(6, 4))
        self._badge(badges, f"Android {firmware.get('android', '—')}",
                    "#A84444", "#F7E7E7").pack(side="left", padx=(0, 6))
        self._badge(badges, INSTALL_LABELS.get(install_type, install_type),
                    badge_bg, badge_fg).pack(side="left", padx=(0, 6))
        self._badge(badges, firmware.get("region", "Global")).pack(side="left")

        subtitle = (
            f"{firmware.get('model', '')}  ·  код устройства: {firmware.get('codename', '—')}"
        )
        ctk.CTkLabel(
            left,
            text=subtitle,
            font=ui_font(size=12),
            text_color=COLOR_MUTED,
        ).pack(anchor="w", pady=(0, 8))

        notes = firmware.get("notes", "")
        if notes:
            ctk.CTkLabel(
                left,
                text=notes,
                font=ui_font(size=12),
                text_color="#B9C0CC",
                wraplength=540,
                justify="left",
            ).pack(anchor="w", pady=(0, 8))

        requirements = firmware.get("requirements") or []
        if requirements:
            requirement_text = t("what_needed") + "  •  ".join(requirements)
            ctk.CTkLabel(
                left,
                text=requirement_text,
                font=ui_font(size=11),
                text_color=COLOR_MUTED,
                wraplength=540,
                justify="left",
            ).pack(anchor="w", pady=(0, 8))

        for warning in (firmware.get("warnings") or [])[:3]:
            pill = ctk.CTkFrame(
                left,
                fg_color="#2B2620",
                corner_radius=8,
                border_width=1,
                border_color="#4A3B26",
            )
            pill.pack(fill="x", pady=3)
            ctk.CTkLabel(
                pill,
                text=f"⚠  {warning}",
                font=ui_font(size=11),
                text_color="#B57C38",
                wraplength=510,
                justify="left",
            ).pack(anchor="w", padx=10, pady=6)

        # ---------------- Правая колонка: действия ----------------
        right = ctk.CTkFrame(card, fg_color="transparent", width=248)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 18), pady=16)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            right,
            text="Размер файла",
            font=ui_font(size=10, weight="bold"),
            text_color=COLOR_MUTED,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            right,
            text=firmware.get("size", "—"),
            font=ui_font(size=16, weight="bold"),
            text_color=COLOR_TEXT,
        ).grid(row=1, column=0, sticky="w", pady=(0, 10))

        ctk.CTkLabel(
            right,
            text="Как устанавливается",
            font=ui_font(size=10, weight="bold"),
            text_color=COLOR_MUTED,
        ).grid(row=2, column=0, sticky="w")
        ctk.CTkLabel(
            right,
            text=INSTALL_LABELS.get(install_type, install_type),
            font=ui_font(size=13, weight="bold"),
            text_color=badge_fg,
        ).grid(row=3, column=0, sticky="w")

        # Состояние загрузки именно этой карточки.
        download_state: dict = {"downloader": None, "path": "", "determinate": False}

        download_button = ctk.CTkButton(
            right,
            text=t("dl_download"),
            width=220,
            height=46,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ui_font(size=13, weight="bold"),
        )
        download_button.grid(row=4, column=0, sticky="ew", pady=(16, 8))

        goto_button = ctk.CTkButton(
            right,
            text="Как установить",
            width=220,
            height=42,
            corner_radius=10,
            fg_color=COLOR_CARD_HOVER,
            hover_color="#2A2D35",
            text_color=COLOR_TEXT,
            font=ui_font(size=13, weight="bold"),
            command=lambda fw=firmware: self._goto_flash(fw),
        )
        goto_button.grid(row=5, column=0, sticky="ew")

        if not firmware.get("direct"):
            ctk.CTkLabel(
                right,
                text=t("dl_page_hint"),
                font=ui_font(size=10),
                text_color=COLOR_WARN,
                wraplength=220,
                justify="left",
            ).grid(row=6, column=0, sticky="w", pady=(8, 0))

        progress_frame = ctk.CTkFrame(right, fg_color="transparent")
        progress_frame.grid(row=7, column=0, sticky="ew", pady=(10, 0))
        progress_frame.grid_columnconfigure(0, weight=1)
        progress_frame.grid_remove()

        progress_bar = ctk.CTkProgressBar(
            progress_frame,
            height=8,
            corner_radius=4,
            progress_color=COLOR_ACCENT,
            fg_color="#2A2D35",
        )
        progress_bar.grid(row=0, column=0, sticky="ew")
        progress_bar.set(0)

        status_label = ctk.CTkLabel(
            progress_frame,
            text="",
            font=ui_font(size=10),
            text_color=COLOR_MUTED,
            anchor="w",
            wraplength=220,
            justify="left",
        )
        status_label.grid(row=1, column=0, sticky="w", pady=(4, 0))

        cancel_button = ctk.CTkButton(
            progress_frame,
            text=t("dl_cancel"),
            height=28,
            corner_radius=8,
            fg_color=COLOR_CARD_HOVER,
            hover_color="#2A2D35",
            text_color=COLOR_TEXT,
            font=ui_font(size=11),
            command=lambda state=download_state: self._cancel_download(state),
        )
        cancel_button.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        cancel_button.grid_remove()

        download_button.configure(
            command=lambda fw=firmware, button=download_button,
            cancel=cancel_button, progress=progress_bar, frame=progress_frame,
            status=status_label, state=download_state: self._start_download(
                fw, button, cancel, progress, frame, status, state
            )
        )

    @staticmethod
    def _badge(parent, text: str, bg: str = "#3A3F4B", fg: str = "#C7CBD4") -> ctk.CTkLabel:
        return ctk.CTkLabel(
            parent,
            text=text,
            font=ui_font(size=11, weight="bold"),
            text_color=fg,
            fg_color=bg,
            corner_radius=8,
            height=24,
            width=max(58, len(text) * 7 + 18),
        )

    # ------------------------------ Установка прошивки ------------------------------
    def _build_manual_page(self) -> ctk.CTkScrollableFrame:
        page = self._make_scroll_page()

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(
            header,
            text="⚡ Установка прошивки",
            font=ui_font(size=22, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Два простых способа: через кабель или через режим загрузчика",
            font=ui_font(size=12),
            text_color=COLOR_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        self._build_hint(
            page,
            1,
            "Здесь вы устанавливаете скачанную прошивку на телефон. Если не уверены, "
            "выберите «Установить прошивку через кабель» — это способ для обычных "
            "пользователей. Способ «через режим загрузчика» сложнее и подходит только "
            "для опытных. Перед началом программа проверит заряд телефона: при заряде "
            "ниже 30% установка не начнётся, чтобы телефон не выключился посередине.",
        )

        # --- Прошивка через кабель (Sideload) ---
        self.sideload_card = ctk.CTkFrame(
            page, fg_color=COLOR_CARD, corner_radius=14,
            border_width=1, border_color=COLOR_BORDER,
        )
        self.sideload_card.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.sideload_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.sideload_card,
            text="Способ 1. Установить прошивку через кабель (ZIP-архив)",
            font=ui_font(size=15, weight="bold"),
            text_color=COLOR_TEXT,
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 2))

        ctk.CTkLabel(
            self.sideload_card,
            text="Самый простой способ. Подходит для обычных обновлений и многих прошивок.",
            font=ui_font(size=11),
            text_color=COLOR_MUTED,
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 8))

        ctk.CTkLabel(
            self.sideload_card,
            text="Файл прошивки (.zip)",
            font=ui_font(size=12, weight="bold"),
            text_color=COLOR_MUTED,
        ).grid(row=2, column=0, sticky="w", padx=18, pady=4)

        zip_row = ctk.CTkFrame(self.sideload_card, fg_color="transparent")
        zip_row.grid(row=2, column=1, sticky="ew", padx=(8, 18), pady=4)
        zip_row.grid_columnconfigure(0, weight=1)

        self.zip_entry = ctk.CTkEntry(
            zip_row,
            height=36,
            corner_radius=8,
            fg_color=COLOR_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            placeholder_text="Файл не выбран",
            state="readonly",
            font=ui_font(size=12),
        )
        self.zip_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.zip_button = ctk.CTkButton(
            zip_row,
            text="Выбрать .zip",
            width=140,
            height=36,
            corner_radius=8,
            fg_color=COLOR_CARD_HOVER,
            hover_color="#2A2D35",
            font=ui_font(size=12),
            command=self.choose_zip,
        )
        self.zip_button.grid(row=0, column=1)
        self._action_widgets.append(self.zip_button)

        self.sideload_button = ctk.CTkButton(
            self.sideload_card,
            text="Установить прошивку через кабель",
            height=44,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ui_font(size=14, weight="bold"),
            command=self.start_sideload,
        )
        self.sideload_button.grid(row=3, column=0, columnspan=2, sticky="ew",
                                  padx=18, pady=(12, 8))
        self._action_widgets.append(self.sideload_button)

        ctk.CTkLabel(
            self.sideload_card,
            text=("На телефоне заранее выберите «Применить обновление из ADB» "
                  "(Apply update from ADB) в меню восстановления. Программа покажет, "
                  "когда можно нажимать кнопку."),
            font=ui_font(size=11),
            text_color=COLOR_MUTED,
            wraplength=820,
            justify="left",
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 16))

        # --- Через режим загрузчика (Fastboot) ---
        self.fastboot_card = ctk.CTkFrame(
            page, fg_color=COLOR_CARD, corner_radius=14,
            border_width=1, border_color=COLOR_BORDER,
        )
        self.fastboot_card.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.fastboot_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.fastboot_card,
            text="Способ 2. Прошить один файл через режим загрузчика (для опытных)",
            font=ui_font(size=15, weight="bold"),
            text_color=COLOR_TEXT,
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 2))

        ctk.CTkLabel(
            self.fastboot_card,
            text=("Этот способ нужен для замены отдельных частей системы. "
                  "Он требует разблокированного загрузчика."),
            font=ui_font(size=11),
            text_color=COLOR_MUTED,
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 8))

        ctk.CTkLabel(
            self.fastboot_card,
            text="Что прошиваем",
            font=ui_font(size=12, weight="bold"),
            text_color=COLOR_MUTED,
        ).grid(row=2, column=0, sticky="w", padx=18, pady=4)

        self.partition_menu = ctk.CTkOptionMenu(
            self.fastboot_card,
            values=PARTITIONS,
            width=240,
            height=36,
            corner_radius=8,
            fg_color=COLOR_CARD_HOVER,
            button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT_HOVER,
            dropdown_fg_color=COLOR_CARD,
            dropdown_hover_color=COLOR_CARD_HOVER,
            font=ui_font(size=13),
            dropdown_font=ui_font(size=13),
        )
        self.partition_menu.set("boot")
        self.partition_menu.grid(row=2, column=1, sticky="w", padx=(8, 18), pady=4)

        ctk.CTkLabel(
            self.fastboot_card,
            text=("boot — обычная загрузка системы • recovery — режим восстановления • "
                  "init_boot / vendor_boot — служебные файлы • vbmeta — проверка подписи"),
            font=ui_font(size=10),
            text_color=COLOR_MUTED,
            wraplength=800,
            justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 4))

        ctk.CTkLabel(
            self.fastboot_card,
            text="Файл образа (.img)",
            font=ui_font(size=12, weight="bold"),
            text_color=COLOR_MUTED,
        ).grid(row=4, column=0, sticky="w", padx=18, pady=4)

        img_row = ctk.CTkFrame(self.fastboot_card, fg_color="transparent")
        img_row.grid(row=4, column=1, sticky="ew", padx=(8, 18), pady=4)
        img_row.grid_columnconfigure(0, weight=1)

        self.img_entry = ctk.CTkEntry(
            img_row,
            height=36,
            corner_radius=8,
            fg_color=COLOR_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            placeholder_text="Файл не выбран",
            state="readonly",
            font=ui_font(size=12),
        )
        self.img_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.img_button = ctk.CTkButton(
            img_row,
            text="Выбрать .img",
            width=140,
            height=36,
            corner_radius=8,
            fg_color=COLOR_CARD_HOVER,
            hover_color="#2A2D35",
            font=ui_font(size=12),
            command=self.choose_img,
        )
        self.img_button.grid(row=0, column=1)
        self._action_widgets.append(self.img_button)

        self.flash_button = ctk.CTkButton(
            self.fastboot_card,
            text="Прошить выбранный файл",
            height=44,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ui_font(size=14, weight="bold"),
            command=self.start_flash,
        )
        self.flash_button.grid(row=5, column=0, columnspan=2, sticky="ew",
                               padx=18, pady=(12, 8))
        self._action_widgets.append(self.flash_button)

        ctk.CTkLabel(
            self.fastboot_card,
            text=("Внимание: неверный файл может сломать телефон. Прошивай только файл "
                  "для своей модели и только при разблокированном загрузчике."),
            font=ui_font(size=11),
            text_color=COLOR_WARN,
            wraplength=820,
            justify="left",
        ).grid(row=6, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 16))

        return page

    # ------------------------------ Очистка ------------------------------
    def _build_cleanup_page(self) -> ctk.CTkScrollableFrame:
        page = self._make_scroll_page()

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(
            header,
            text="🧹 Очистка от рекламы и мусора (без Root)",
            font=ui_font(size=22, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Убираем встроенную рекламу и лишние приложения — телефон остаётся рабочим",
            font=ui_font(size=12),
            text_color=COLOR_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        self._build_hint(
            page,
            1,
            "Программа ищет в телефоне встроенную рекламу и ненужные приложения и "
            "предлагает их удалить. В безопасном режиме показываются только проверенные "
            "приложения из белого списка — важные системные файлы скрыты, поэтому "
            "случайно сломать телефон нельзя. Удалённые приложения можно вернуть одной "
            "кнопкой «Вернуть всё как было».",
        )

        controls = ctk.CTkFrame(
            page,
            fg_color=COLOR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        controls.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        controls.grid_columnconfigure(0, weight=1)

        self.safe_mode_var = tk.BooleanVar(value=True)
        self.safe_mode_switch = ctk.CTkSwitch(
            controls,
            text="Только безопасная очистка (Рекомендуется)",
            variable=self.safe_mode_var,
            onvalue=True,
            offvalue=False,
            font=ui_font(size=13, weight="bold"),
            text_color=COLOR_TEXT,
            progress_color=COLOR_ACCENT,
            button_color="#E6E6E8",
            button_hover_color="#FFFFFF",
            command=self._on_safe_mode_change,
        )
        self.safe_mode_switch.grid(row=0, column=0, sticky="w", padx=18, pady=(14, 2))
        self.safe_mode_switch.select()

        ctk.CTkLabel(
            controls,
            text=("В этом режиме видны только проверенные рекламные и мусорные "
                  "приложения. Критически важные системные файлы скрыты."),
            font=ui_font(size=11),
            text_color=COLOR_MUTED,
            wraplength=800,
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 8))

        search_row = ctk.CTkFrame(controls, fg_color="transparent")
        search_row.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))
        search_row.grid_columnconfigure(0, weight=1)

        self.cleanup_search = ctk.CTkEntry(
            search_row,
            height=38,
            corner_radius=8,
            fg_color=COLOR_BG,
            border_color=COLOR_BORDER,
            placeholder_text="Найти приложение по названию или пакету",
            font=ui_font(size=12),
            text_color=COLOR_TEXT,
        )
        self.cleanup_search.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.cleanup_search.bind("<KeyRelease>", lambda _e: self._render_cleanup_list())

        self.scan_cleanup_button = ctk.CTkButton(
            search_row,
            text="🔍 Найти рекламу и мусор",
            width=230,
            height=38,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ui_font(size=12, weight="bold"),
            command=self.scan_cleanup,
        )
        self.scan_cleanup_button.grid(row=0, column=1, padx=(0, 10))
        self._action_widgets.append(self.scan_cleanup_button)

        self.select_all_button = ctk.CTkButton(
            search_row,
            text="Выбрать всё",
            width=120,
            height=38,
            corner_radius=8,
            fg_color=COLOR_CARD_HOVER,
            hover_color="#2A2D35",
            font=ui_font(size=12),
            command=self._toggle_select_all,
        )
        self.select_all_button.grid(row=0, column=2)

        self.cleanup_count_label = ctk.CTkLabel(
            controls,
            text=t("cleanup_counts", found=0, selected=0),
            font=ui_font(size=11),
            text_color=COLOR_MUTED,
            anchor="w",
        )
        self.cleanup_count_label.grid(row=3, column=0, sticky="w", padx=18, pady=(0, 12))

        self.cleanup_list_frame = ctk.CTkFrame(page, fg_color="transparent")
        self.cleanup_list_frame.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(
            self.cleanup_list_frame,
            text=("Нажмите «Найти рекламу и мусор», чтобы программа проверила телефон. "
                  "Это безопасно и ничего не удаляет."),
            font=ui_font(size=12),
            text_color=COLOR_MUTED,
            justify="left",
        ).pack(anchor="w", padx=8, pady=20)

        actions = ctk.CTkFrame(page, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)

        self.clean_selected_button = ctk.CTkButton(
            actions,
            text="🧹 Очистить выбранное",
            height=46,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ui_font(size=14, weight="bold"),
            command=self.clean_selected,
        )
        self.clean_selected_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._action_widgets.append(self.clean_selected_button)

        self.restore_button = ctk.CTkButton(
            actions,
            text="↩ Вернуть всё как было",
            height=46,
            corner_radius=10,
            fg_color=COLOR_CARD_HOVER,
            hover_color="#2A2D35",
            text_color=COLOR_TEXT,
            font=ui_font(size=14, weight="bold"),
            command=self.restore_all_packages,
        )
        self.restore_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self._action_widgets.append(self.restore_button)

        return page

    def _on_safe_mode_change(self) -> None:
        if self.safe_mode_var.get():
            self.log("Включён безопасный режим: показываем только проверенные приложения.", "ok")
        else:
            self.log("Внимание: показаны все системные приложения. Удаляйте только то, "
                     "в чём уверены.", "warn")
        if self._all_packages:
            self._render_cleanup_list(self._filter_cleanup_packages(self._all_packages))
        else:
            self.log("Нажмите «Найти рекламу и мусор», чтобы обновить список.", "muted")

    def _filter_cleanup_packages(self, packages: list[str]) -> list[str]:
        if self.safe_mode_var.get():
            return [pkg for pkg in packages if pkg in SAFE_PACKAGES]
        return list(packages)

    @staticmethod
    def _parse_package_list(output: str) -> set[str]:
        result: set[str] = set()
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("package:") and ":" in line:
                result.add(line.split(":", 1)[1].strip())
        return result

    def scan_cleanup(self) -> None:
        self._run_task(self._scan_cleanup_worker)

    def _scan_cleanup_worker(self) -> None:
        safe_mode = bool(self.safe_mode_var.get())
        self.log("=== Поиск рекламы и мусора ===", "section")
        self.log("Режим: " + ("только безопасная очистка (рекомендуется)." if safe_mode
                              else "все системные приложения (осторожно!)."),
                 "ok" if safe_mode else "warn")
        self.log("$ adb shell pm list packages -s", "cmd")
        code, output = self._capture([ADB, "shell", "pm", "list", "packages", "-s"],
                                     timeout=90.0)
        if code != 0:
            self.log("Телефон не ответил. Проверьте кабель и разрешение отладки.", "error")
            self.after(0, lambda: messagebox.showwarning(
                APP_NAME,
                "Телефон не ответил.\n\nПроверьте кабель, включите «Отладку по USB» "
                "и разрешите доступ на экране телефона.",
                parent=self,
            ))
            return

        packages = sorted(self._parse_package_list(output))
        self._all_packages = packages
        found = self._filter_cleanup_packages(packages)
        self.log(f"Всего системных приложений: {len(packages)}. Показано: {len(found)}.",
                 "info")
        if safe_mode and not found:
            self.log("Рекламы и мусора из безопасного списка не найдено — телефон чистый.", "ok")
        self.after(0, self._render_cleanup_list, found)

    def _render_cleanup_list(self, packages: list[str] | None = None) -> None:
        if packages is not None:
            self._scan_packages = list(packages)

        for child in self.cleanup_list_frame.winfo_children():
            child.destroy()

        query = self.cleanup_search.get().strip().lower()
        shown = 0
        for pkg in self._scan_packages:
            friendly = SAFE_PACKAGES.get(pkg, tr("Системное приложение"))
            if query and query not in pkg.lower() and query not in friendly.lower():
                continue
            var = self._cleanup_vars.setdefault(pkg, tk.BooleanVar(value=False))
            row = ctk.CTkFrame(
                self.cleanup_list_frame,
                fg_color=COLOR_CARD,
                corner_radius=10,
                border_width=1,
                border_color=COLOR_BORDER,
            )
            row.pack(fill="x", padx=4, pady=4)

            ctk.CTkCheckBox(
                row,
                text="",
                variable=var,
                width=24,
                checkbox_width=22,
                checkbox_height=22,
                corner_radius=6,
                fg_color=COLOR_ACCENT,
                hover_color=COLOR_ACCENT_HOVER,
                border_color="#5A5E68",
                command=self._update_cleanup_count,
            ).pack(side="left", padx=(12, 8), pady=10)

            text_frame = ctk.CTkFrame(row, fg_color="transparent")
            text_frame.pack(side="left", fill="x", expand=True, pady=8)
            ctk.CTkLabel(
                text_frame,
                text=friendly,
                font=ui_font(size=13, weight="bold"),
                text_color=COLOR_TEXT,
                anchor="w",
            ).pack(anchor="w")
            ctk.CTkLabel(
                text_frame,
                text=pkg,
                font=ui_font(size=10),
                text_color=COLOR_MUTED,
                anchor="w",
            ).pack(anchor="w")
            shown += 1

        if shown == 0:
            ctk.CTkLabel(
                self.cleanup_list_frame,
                text=("Ничего не найдено. Нажмите «Найти рекламу и мусор» "
                      "или измените поисковый запрос."),
                font=ui_font(size=12),
                text_color=COLOR_MUTED,
                justify="left",
            ).pack(anchor="w", padx=8, pady=20)

        self._update_cleanup_count()

    def _update_cleanup_count(self) -> None:
        if not hasattr(self, "cleanup_count_label"):
            return
        selected = sum(
            1 for pkg in self._scan_packages
            if pkg in self._cleanup_vars and self._cleanup_vars[pkg].get()
        )
        self.cleanup_count_label.configure(
            text=t("cleanup_counts", found=len(self._scan_packages), selected=selected)
        )

    def _toggle_select_all(self) -> None:
        packages = list(self._scan_packages)
        if not packages:
            return
        all_selected = all(
            pkg in self._cleanup_vars and self._cleanup_vars[pkg].get()
            for pkg in packages
        )
        for pkg in packages:
            self._cleanup_vars.setdefault(pkg, tk.BooleanVar(value=False)).set(not all_selected)
        self._update_cleanup_count()

    def _selected_cleanup_packages(self) -> list[str]:
        return [
            pkg for pkg in self._scan_packages
            if pkg in self._cleanup_vars and self._cleanup_vars[pkg].get()
        ]

    def clean_selected(self) -> None:
        selected = self._selected_cleanup_packages()
        if not selected:
            messagebox.showwarning(
                APP_NAME,
                "Сначала поставьте галочки напротив приложений, которые хотите удалить.",
                parent=self,
            )
            return

        preview = "\n".join(
            f"• {SAFE_PACKAGES.get(pkg, pkg)} ({pkg})" for pkg in selected[:12]
        )
        if len(selected) > 12:
            preview += f"\n… и ещё {len(selected) - 12}"

        confirmed = messagebox.askyesno(
            "Очистить выбранное?",
            f"Удалить {len(selected)} приложений?\n\n{preview}\n\n"
            "Телефон продолжит работать как раньше. Если передумаете — нажмите "
            "«Вернуть всё как было».",
            parent=self,
        )
        if not confirmed:
            self.log("Очистка отменена пользователем.", "warn")
            return

        if not self._ensure_battery("очистки от рекламы"):
            return

        self._run_task(lambda: self._clean_selected_worker(selected))

    def _clean_selected_worker(self, packages: list[str]) -> None:
        self.log("=== Удаление выбранных приложений ===", "section")
        removed = self._load_removed()
        success = 0
        for pkg in packages:
            self.log(f"$ adb shell pm uninstall -k --user 0 {pkg}", "cmd")
            code, output = self._capture(
                [ADB, "shell", "pm", "uninstall", "-k", "--user", "0", pkg],
                timeout=90.0,
            )
            if output:
                self.log(output, "info")
            if code == 0 and "success" in output.lower():
                success += 1
                removed.add(pkg)
                self.log(f"Удалено: {pkg}", "ok")
            else:
                self.log(f"Не удалось удалить: {pkg}", "error")

        self._save_removed(removed)
        self.log(f"Готово: удалено {success} из {len(packages)} приложений.",
                 "ok" if success else "warn")
        self.after(400, self.scan_cleanup)

    def restore_all_packages(self) -> None:
        if self._busy > 0:
            self.log("Дождитесь завершения текущей операции.", "warn")
            return
        self._start_task()

        def gather() -> None:
            candidates: list[str] = []
            try:
                candidates = self._collect_restore_candidates()
            except Exception as exc:  # noqa: BLE001
                self.log(f"Ошибка подготовки восстановления: {exc}", "error")
            finally:
                self._finish_task()
            self.after(0, lambda: self._confirm_restore(candidates))

        threading.Thread(target=gather, daemon=True).start()

    def _collect_restore_candidates(self) -> list[str]:
        self.log("Ищу удалённые приложения, которые можно вернуть...", "info")
        removed = self._load_removed()
        _, active_out = self._capture([ADB, "shell", "pm", "list", "packages"],
                                      timeout=60.0)
        _, all_out = self._capture([ADB, "shell", "pm", "list", "packages", "-u"],
                                   timeout=60.0)
        active = self._parse_package_list(active_out)
        every = self._parse_package_list(all_out)
        if not every:
            self.log("Телефон не ответил — не удалось получить список приложений.", "error")
            return []
        candidates = {pkg for pkg in removed if pkg in every}
        candidates |= {pkg for pkg in (every - active) if pkg in SAFE_PACKAGES}
        return sorted(candidates)

    def _confirm_restore(self, candidates: list[str]) -> None:
        if not candidates:
            messagebox.showinfo(
                "Возвращать нечего",
                "Программа не нашла удалённых приложений, которые можно вернуть.\n\n"
                "Если вы ничего не удаляли — всё в порядке.",
                parent=self,
            )
            return

        preview = "\n".join(
            f"• {SAFE_PACKAGES.get(pkg, pkg)} ({pkg})" for pkg in candidates[:12]
        )
        if len(candidates) > 12:
            preview += f"\n… и ещё {len(candidates) - 12}"

        confirmed = messagebox.askyesno(
            "Вернуть всё как было?",
            f"Вернуть {len(candidates)} приложений обратно в телефон?\n\n{preview}\n\n"
            "Это безопасно: приложения просто снова появятся.",
            parent=self,
        )
        if not confirmed:
            self.log("Восстановление отменено.", "warn")
            return

        self._run_task(lambda: self._restore_worker(candidates))

    def _restore_worker(self, packages: list[str]) -> None:
        self.log("=== Возврат удалённых приложений ===", "section")
        removed = self._load_removed()
        success = 0
        for pkg in packages:
            self.log(f"$ adb shell cmd package install-existing {pkg}", "cmd")
            code, output = self._capture(
                [ADB, "shell", "cmd", "package", "install-existing", pkg],
                timeout=90.0,
            )
            if output:
                self.log(output, "info")
            if code == 0 and ("installed" in output.lower() or "success" in output.lower()):
                success += 1
                removed.discard(pkg)
                self.log(f"Возвращено: {pkg}", "ok")
            else:
                self.log(f"Не удалось вернуть: {pkg}", "error")

        self._save_removed(removed)
        self.log(f"Готово: возвращено {success} из {len(packages)} приложений.",
                 "ok" if success else "warn")
        if success:
            self.after(0, lambda: messagebox.showinfo(
                APP_NAME,
                "Приложения возвращены.\n\nПерезагрузите телефон, чтобы они снова "
                "появились в меню.",
                parent=self,
            ))
        self.after(500, self.scan_cleanup)

    def _load_removed(self) -> set[str]:
        try:
            with open(REMOVED_FILE, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, list):
                return {str(item) for item in data}
        except Exception:  # noqa: BLE001
            pass
        return set()

    def _save_removed(self, packages: set[str]) -> None:
        try:
            with open(REMOVED_FILE, "w", encoding="utf-8") as handle:
                json.dump(sorted(packages), handle, ensure_ascii=False, indent=2)
        except Exception as exc:  # noqa: BLE001
            self.log(f"Не удалось сохранить список удалённых приложений: {exc}", "warn")

    # ------------------------------ Помощник и APK ------------------------------
    def _build_tools_page(self) -> ctk.CTkScrollableFrame:
        page = self._make_scroll_page()

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(
            header,
            text="🛠 Помощник, Драйверы и APK",
            font=ui_font(size=22, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Если компьютер не видит телефон, нужно поставить игру или проверить файл",
            font=ui_font(size=12),
            text_color=COLOR_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        self._build_hint(
            page,
            1,
            "Здесь собраны три простые помощника. Драйверы нужны, если компьютер не "
            "видит телефон. Установка .apk позволяет поставить игру или программу с "
            "компьютера одним нажатием. Проверка хеша показывает, что скачанный файл "
            "прошивки целый и не повреждён при загрузке.",
        )

        # Карточки размещаем прямо на прокручиваемой странице.

        # --- Драйверы ---
        drivers_card = ctk.CTkFrame(
            page, fg_color=COLOR_CARD, corner_radius=14,
            border_width=1, border_color=COLOR_BORDER,
        )
        drivers_card.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        drivers_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            drivers_card,
            text="1. Компьютер не видит телефон? Установить драйверы",
            font=ui_font(size=15, weight="bold"),
            text_color=COLOR_TEXT,
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 2))

        ctk.CTkLabel(
            drivers_card,
            text=("Программа скачает официальный драйвер Google, распакует его и "
                  "запустит установку. Windows может попросить разрешение "
                  "администратора — нажмите «Да»."),
            font=ui_font(size=11),
            text_color=COLOR_MUTED,
            wraplength=800,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 8))

        self.drivers_button = ctk.CTkButton(
            drivers_card,
            text="Установить драйверы",
            height=44,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ui_font(size=13, weight="bold"),
            command=self.install_drivers,
        )
        self.drivers_button.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))
        self._action_widgets.append(self.drivers_button)

        # --- APK ---
        apk_card = ctk.CTkFrame(
            page, fg_color=COLOR_CARD, corner_radius=14,
            border_width=1, border_color=COLOR_BORDER,
        )
        apk_card.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        apk_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            apk_card,
            text="2. Установить игру или программу (.apk) с компьютера",
            font=ui_font(size=15, weight="bold"),
            text_color=COLOR_TEXT,
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 2))

        ctk.CTkLabel(
            apk_card,
            text=("Выберите скачанный файл .apk — программа сама установит его на "
                  "подключённый телефон. Телефон должен быть разблокирован."),
            font=ui_font(size=11),
            text_color=COLOR_MUTED,
            wraplength=800,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 8))

        self.apk_button = ctk.CTkButton(
            apk_card,
            text="Установить .apk файл с ПК на телефон",
            height=44,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ui_font(size=13, weight="bold"),
            command=self.install_apk,
        )
        self.apk_button.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))
        self._action_widgets.append(self.apk_button)

        # --- Экран телефона на ПК (scrcpy) ---
        scrcpy_card = ctk.CTkFrame(
            page, fg_color=COLOR_CARD, corner_radius=14,
            border_width=1, border_color=COLOR_BORDER,
        )
        scrcpy_card.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        scrcpy_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            scrcpy_card,
            text="📺 Экран телефона на ПК (Управление мышкой)",
            font=ui_font(size=15, weight="bold"),
            text_color=COLOR_TEXT,
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 2))

        ctk.CTkLabel(
            scrcpy_card,
            text=("Транслирует экран телефона в отдельное окно Windows: можно управлять "
                  "мышкой и клавиатурой, даже если сенсор разбит. При первом запуске "
                  "программа сама скачает scrcpy-win64 (~11 МБ, распаковка ~30 МБ) "
                  "в локальную папку данных."),
            font=ui_font(size=11),
            text_color=COLOR_MUTED,
            wraplength=800,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 8))

        self.scrcpy_button = ctk.CTkButton(
            scrcpy_card,
            text=t("scrcpy_start"),
            height=44,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ui_font(size=13, weight="bold"),
            command=self.start_scrcpy,
        )
        self.scrcpy_button.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 8))

        self.scrcpy_status = ctk.CTkLabel(
            scrcpy_card,
            text="",
            font=ui_font(size=11),
            text_color=COLOR_MUTED,
            anchor="w",
            wraplength=800,
            justify="left",
        )
        self.scrcpy_status.grid(row=3, column=0, sticky="w", padx=18, pady=(0, 16))

        # --- Хеши ---
        hash_card = ctk.CTkFrame(
            page, fg_color=COLOR_CARD, corner_radius=14,
            border_width=1, border_color=COLOR_BORDER,
        )
        hash_card.grid(row=5, column=0, sticky="ew", pady=(0, 10))
        hash_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hash_card,
            text="3. Проверка файла прошивки (чтобы не установить битый файл)",
            font=ui_font(size=15, weight="bold"),
            text_color=COLOR_TEXT,
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 2))

        ctk.CTkLabel(
            hash_card,
            text=("Выберите скачанный файл прошивки (.zip или .img) и нажмите "
                  "«Посчитать хеши». Затем вставьте хеш с сайта производителя и "
                  "нажмите «Сравнить» — программа скажет, совпадает ли файл."),
            font=ui_font(size=11),
            text_color=COLOR_MUTED,
            wraplength=800,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 8))

        ctk.CTkLabel(
            hash_card,
            text="Файл прошивки",
            font=ui_font(size=12, weight="bold"),
            text_color=COLOR_MUTED,
        ).grid(row=2, column=0, sticky="w", padx=18, pady=4)

        hash_row = ctk.CTkFrame(hash_card, fg_color="transparent")
        hash_row.grid(row=2, column=1, sticky="ew", padx=(8, 18), pady=4)
        hash_row.grid_columnconfigure(0, weight=1)

        self.hash_file_entry = ctk.CTkEntry(
            hash_row,
            height=36,
            corner_radius=8,
            fg_color=COLOR_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            placeholder_text="Файл не выбран",
            state="readonly",
            font=ui_font(size=12),
        )
        self.hash_file_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.hash_choose_button = ctk.CTkButton(
            hash_row,
            text="Выбрать файл",
            width=140,
            height=36,
            corner_radius=8,
            fg_color=COLOR_CARD_HOVER,
            hover_color="#2A2D35",
            font=ui_font(size=12),
            command=self.choose_checksum_file,
        )
        self.hash_choose_button.grid(row=0, column=1)
        self._action_widgets.append(self.hash_choose_button)

        self.hash_calc_button = ctk.CTkButton(
            hash_card,
            text="Посчитать хеши (MD5 и SHA256)",
            height=42,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ui_font(size=13, weight="bold"),
            command=self.compute_checksums,
        )
        self.hash_calc_button.grid(row=3, column=0, columnspan=2, sticky="ew",
                                   padx=18, pady=(10, 8))
        self._action_widgets.append(self.hash_calc_button)

        ctk.CTkLabel(
            hash_card,
            text="MD5 файла",
            font=ui_font(size=11, weight="bold"),
            text_color=COLOR_MUTED,
        ).grid(row=4, column=0, sticky="w", padx=18, pady=(4, 2))

        self.md5_entry = ctk.CTkEntry(
            hash_card,
            height=34,
            corner_radius=8,
            fg_color=COLOR_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            placeholder_text="появится после расчёта",
            state="readonly",
            font=ui_font(family="Consolas", size=11),
        )
        self.md5_entry.grid(row=4, column=1, sticky="ew", padx=(8, 18), pady=(4, 2))

        ctk.CTkLabel(
            hash_card,
            text="SHA256 файла",
            font=ui_font(size=11, weight="bold"),
            text_color=COLOR_MUTED,
        ).grid(row=5, column=0, sticky="w", padx=18, pady=2)

        self.sha_entry = ctk.CTkEntry(
            hash_card,
            height=34,
            corner_radius=8,
            fg_color=COLOR_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            placeholder_text="появится после расчёта",
            state="readonly",
            font=ui_font(family="Consolas", size=11),
        )
        self.sha_entry.grid(row=5, column=1, sticky="ew", padx=(8, 18), pady=2)

        ctk.CTkLabel(
            hash_card,
            text="Хеш с сайта",
            font=ui_font(size=11, weight="bold"),
            text_color=COLOR_MUTED,
        ).grid(row=6, column=0, sticky="w", padx=18, pady=(6, 12))

        self.expected_entry = ctk.CTkEntry(
            hash_card,
            height=34,
            corner_radius=8,
            fg_color=COLOR_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            placeholder_text="Вставьте сюда хеш со страницы загрузки",
            font=ui_font(family="Consolas", size=11),
        )
        self.expected_entry.grid(row=6, column=1, sticky="ew", padx=(8, 18), pady=(6, 4))

        self.compare_button = ctk.CTkButton(
            hash_card,
            text="Сравнить с сайтом",
            height=40,
            corner_radius=10,
            fg_color=COLOR_CARD_HOVER,
            hover_color="#2A2D35",
            text_color=COLOR_TEXT,
            font=ui_font(size=13, weight="bold"),
            command=self.compare_checksums,
        )
        self.compare_button.grid(row=7, column=0, columnspan=2, sticky="ew",
                                 padx=18, pady=(0, 16))

        return page

    def install_drivers(self) -> None:
        self._run_task(self._install_drivers_worker)

    def _install_drivers_worker(self) -> None:
        self.log("=== Установка драйверов Google USB Driver ===", "section")
        temp_dir = tempfile.mkdtemp(prefix="kitagawa_usb_driver_")
        zip_path = os.path.join(temp_dir, "latest_usb_driver_windows.zip")
        try:
            self.log("Скачиваю официальный драйвер Google...", "info")
            self.log(f"URL: {DRIVER_URL}", "cmd")
            request = urllib.request.Request(
                DRIVER_URL,
                headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"},
            )
            with urllib.request.urlopen(request, timeout=60) as response, \
                    open(zip_path, "wb") as handle:
                total = int(response.headers.get("Content-Length") or 0)
                downloaded = 0
                last_log = 0.0
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    handle.write(chunk)
                    downloaded += len(chunk)
                    now = time.time()
                    if total and (now - last_log > 1.0 or downloaded >= total):
                        last_log = now
                        self.log(f"  скачано {downloaded / 1048576:.1f} / "
                                 f"{total / 1048576:.1f} МБ", "muted")

            self.log("Распаковываю архив с драйвером...", "info")
            extract_dir = os.path.join(temp_dir, "driver")
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(extract_dir)

            inf_path = ""
            for root, _dirs, files in os.walk(extract_dir):
                for name in files:
                    if name.lower() == "android_winusb.inf":
                        inf_path = os.path.join(root, name)
                        break
                if inf_path:
                    break

            if not inf_path:
                self.log("В скачанном архиве не найден android_winusb.inf.", "error")
                return

            self.log(f"Файл драйвера: {inf_path}", "muted")
            self.log("Запускаю установку драйвера. Windows может спросить разрешение.",
                     "warn")
            code = self._stream_process(["pnputil", "/add-driver", inf_path, "/install"])
            if code == 0:
                self.log("Драйвер успешно установлен.", "ok")
                self.after(0, lambda: messagebox.showinfo(
                    APP_NAME,
                    "Драйвер установлен!\n\nТеперь отключите телефон от USB и "
                    "подключите снова. Затем проверьте связь кнопкой «Проверить телефон» "
                    "во вкладке «Управление телефоном».",
                    parent=self,
                ))
                return

            self.log("Не удалось установить драйвер без прав администратора. "
                     "Открываю окно установки от имени администратора.", "warn")
            try:
                result = ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "runas",
                    "pnputil.exe",
                    f'/add-driver "{inf_path}" /install',
                    None,
                    1,
                )
            except Exception as exc:  # noqa: BLE001
                self.log(f"Ошибка запуска от имени администратора: {exc}", "error")
                return

            if result > 32:
                self.log("Открылось окно установки. Нажмите «Да» в запросе Windows.", "warn")
                self.after(0, lambda: messagebox.showinfo(
                    APP_NAME,
                    "Открылось окно установки драйвера.\n\nПодтвердите запрос "
                    "«Разрешить этому приложению вносить изменения?» кнопкой «Да». "
                    "После завершения отключите и подключите телефон заново.",
                    parent=self,
                ))
            else:
                self.log("Запуск от имени администратора отменён или не удался.", "error")
        except Exception as exc:  # noqa: BLE001
            self.log(f"Ошибка установки драйверов: {exc}", "error")
            self.after(0, lambda: messagebox.showwarning(
                APP_NAME,
                "Не удалось установить драйверы.\n\nПроверьте подключение к интернету "
                "и попробуйте снова. Можно скачать драйвер вручную со страницы "
                "developer.android.com/studio/run/win-usb.",
                parent=self,
            ))

    def install_apk(self) -> None:
        path = filedialog.askopenfilename(
            title="Выберите файл программы (.apk)",
            filetypes=[("Приложения Android", "*.apk"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        if not os.path.isfile(path):
            messagebox.showwarning(APP_NAME, "Файл не найден.", parent=self)
            return

        confirmed = messagebox.askyesno(
            "Установить приложение?",
            f"Установить «{os.path.basename(path)}» на подключённый телефон?\n\n"
            "Телефон должен быть разблокирован. Если он спросит разрешение на "
            "установку — нажмите «Разрешить».",
            parent=self,
        )
        if not confirmed:
            self.log("Установка .apk отменена пользователем.", "warn")
            return

        def worker() -> None:
            self.log(f"=== Установка приложения: {os.path.basename(path)} ===", "section")
            code = self._stream_process([ADB, "install", "-r", path])
            if code == 0:
                self.log("Приложение успешно установлено.", "ok")
                self.after(0, lambda: messagebox.showinfo(
                    APP_NAME,
                    "Готово! Приложение установлено на телефон.",
                    parent=self,
                ))
            else:
                self.log(f"Не удалось установить приложение (код {code}).", "error")
                self.after(0, lambda: messagebox.showwarning(
                    APP_NAME,
                    "Не удалось установить приложение.\n\nПроверьте, что телефон "
                    "подключён, разблокирован и разрешает установку из неизвестных "
                    "источников.",
                    parent=self,
                ))

        self._run_task(worker)

    def _set_scrcpy_status(self, text: str, color: str) -> None:
        self.scrcpy_status.configure(text=text, text_color=color)

    def start_scrcpy(self) -> None:
        self.scrcpy_button.configure(state="disabled", text=t("scrcpy_checking"))
        self._set_scrcpy_status(t("scrcpy_checking_connection"), COLOR_MUTED)
        threading.Thread(target=self._scrcpy_worker, daemon=True).start()

    @staticmethod
    def _find_scrcpy() -> str | None:
        for root, _dirs, files in os.walk(SCRCPY_DIR):
            if "scrcpy.exe" in files:
                return os.path.join(root, "scrcpy.exe")
        return None

    def _scrcpy_worker(self) -> None:
        self.log("=== Трансляция экрана телефона (scrcpy) ===", "section")
        _, devices_out = self._capture([ADB, "devices"], timeout=15.0)
        if not self._parse_adb_devices(devices_out):
            self.log("Телефон не найден для трансляции экрана.", "warn")
            self.after(0, lambda: self._scrcpy_failed(t("hw_phone_not_found")))
            return

        exe = self._find_scrcpy()
        if exe is None:
            self.log("scrcpy не найден — скачиваю последний релиз scrcpy-win64.", "info")
            self.after(0, lambda: self._set_scrcpy_status(
                t("scrcpy_downloading"), COLOR_WARN
            ))
            try:
                exe = self._download_scrcpy()
            except Exception as exc:  # noqa: BLE001
                self.log(f"Не удалось скачать scrcpy: {exc}", "error")
                self.after(0, lambda: self._scrcpy_failed(
                    t("scrcpy_download_failed", error=exc)
                ))
                return

        self.log(f"Запускаю: {exe}", "cmd")
        try:
            subprocess.Popen(
                [exe, "--window-title", "KitagawaUtilits Screen Mirror"],
                cwd=os.path.dirname(exe),
                creationflags=popen_flags(),
            )
        except Exception as exc:  # noqa: BLE001
            self.log(f"Не удалось запустить scrcpy: {exc}", "error")
            self.after(0, lambda: self._scrcpy_failed(
                t("scrcpy_failed", error=exc)
            ))
            return

        self.log("Окно телефона открыто. Управляйте мышкой и клавиатурой.", "ok")
        self.after(0, self._scrcpy_started)

    def _download_scrcpy(self) -> str:
        os.makedirs(SCRCPY_DIR, exist_ok=True)
        request = urllib.request.Request(
            SCRCPY_RELEASE_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "Mozilla/5.0",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            release = json.load(response)

        assets = release.get("assets", []) if isinstance(release, dict) else []
        asset = next(
            (
                item for item in assets
                if "scrcpy-win64" in str(item.get("name", "")).lower()
                and str(item.get("name", "")).lower().endswith(".zip")
            ),
            None,
        )
        if asset is None:
            raise RuntimeError("в последнем релизе нет архива scrcpy-win64")

        url = asset.get("browser_download_url")
        if not url:
            raise RuntimeError("не удалось получить ссылку на архив")

        archive_path = os.path.join(SCRCPY_DIR, os.path.basename(url))
        self.log(f"URL: {url}", "cmd")
        download = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(download, timeout=60) as response, \
                open(archive_path, "wb") as handle:
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            last_mark = -1
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                handle.write(chunk)
                downloaded += len(chunk)
                if total:
                    mark = (downloaded * 100 // total) // 20 * 20
                    if mark != last_mark:
                        last_mark = mark
                        self.log(f"  скачано {mark}%", "muted")

        self.log(f"Архив скачан: {archive_path}", "ok")
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(SCRCPY_DIR)

        exe = self._find_scrcpy()
        if exe is None:
            raise RuntimeError("в архиве не найден scrcpy.exe")
        self.log(f"scrcpy распакован: {exe}", "ok")
        return exe

    def _scrcpy_started(self) -> None:
        self.scrcpy_button.configure(state="normal", text=t("scrcpy_start"))
        self._set_scrcpy_status(t("scrcpy_started"), COLOR_OK)

    def _scrcpy_failed(self, message: str) -> None:
        self.scrcpy_button.configure(state="normal", text=t("scrcpy_start"))
        self._set_scrcpy_status(message, COLOR_ERR)

    def choose_checksum_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Выберите файл прошивки",
            filetypes=[("Файлы прошивок", "*.zip *.img"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        self._checksum_path = path
        self._set_entry_text(self.hash_file_entry, path)
        self._set_entry_text(self.md5_entry, "")
        self._set_entry_text(self.sha_entry, "")
        try:
            size_mb = os.path.getsize(path) / 1048576
            self.log(f"Выбран файл: {path} ({size_mb:.1f} МБ)", "muted")
        except OSError:
            self.log(f"Выбран файл: {path}", "muted")

    def compute_checksums(self) -> None:
        path = self._checksum_path
        if not path or not os.path.isfile(path):
            messagebox.showwarning(
                APP_NAME,
                "Сначала выберите файл прошивки кнопкой «Выбрать файл».",
                parent=self,
            )
            return
        self._run_task(lambda: self._checksum_worker(path))

    def _checksum_worker(self, path: str) -> None:
        self.log(f"=== Проверка файла: {os.path.basename(path)} ===", "section")
        try:
            size = os.path.getsize(path)
        except OSError as exc:
            self.log(f"Не удалось открыть файл: {exc}", "error")
            return
        self.log(f"Размер файла: {size / 1048576:.1f} МБ", "info")

        md5 = hashlib.md5()
        sha = hashlib.sha256()
        done = 0
        last_log = 0.0
        try:
            with open(path, "rb") as handle:
                while True:
                    chunk = handle.read(1024 * 1024)
                    if not chunk:
                        break
                    md5.update(chunk)
                    sha.update(chunk)
                    done += len(chunk)
                    now = time.time()
                    if size and (now - last_log > 0.8 or done >= size):
                        last_log = now
                        self.log(f"  проверено {done * 100 / size:.0f}%", "muted")
        except OSError as exc:
            self.log(f"Ошибка чтения файла: {exc}", "error")
            return

        md5_hex = md5.hexdigest()
        sha_hex = sha.hexdigest()
        self.log(f"MD5: {md5_hex}", "ok")
        self.log(f"SHA256: {sha_hex}", "ok")

        def apply() -> None:
            self._set_entry_text(self.md5_entry, md5_hex)
            self._set_entry_text(self.sha_entry, sha_hex)

        self.after(0, apply)

    def compare_checksums(self) -> None:
        expected = self.expected_entry.get().strip().lower()
        md5_value = self.md5_entry.get().strip().lower()
        sha_value = self.sha_entry.get().strip().lower()

        if not md5_value and not sha_value:
            messagebox.showwarning(
                APP_NAME,
                "Сначала нажмите «Посчитать хеши», чтобы программа проверила файл.",
                parent=self,
            )
            return
        if not expected:
            messagebox.showwarning(
                APP_NAME,
                "Вставьте хеш со страницы загрузки прошивки в поле «Хеш с сайта».",
                parent=self,
            )
            return

        if expected in (md5_value, sha_value):
            self.log("Хеш совпадает — файл скачан полностью и без ошибок.", "ok")
            messagebox.showinfo(
                "Хеш совпадает ✅",
                "Отлично! Файл скачан полностью и без ошибок.\n\n"
                "Его можно использовать для установки прошивки.",
                parent=self,
            )
        else:
            self.log("Хеш НЕ совпадает — файл повреждён или скачан не полностью.", "error")
            messagebox.showwarning(
                "Хеш не совпадает ❌",
                "Файл не совпадает с хешем с сайта.\n\n"
                "Скорее всего, загрузка прервалась или файл повреждён. Удалите его и "
                "скачайте прошивку заново. Не устанавливайте такой файл!",
                parent=self,
            )

    # ------------------------------ Управление ------------------------------
    def _build_manage_page(self) -> ctk.CTkScrollableFrame:
        page = self._make_scroll_page()

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(
            header,
            text="🔄 Управление телефоном",
            font=ui_font(size=22, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Проверка связи, заряда батареи и перезагрузка в нужный режим",
            font=ui_font(size=12),
            text_color=COLOR_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        self._build_hint(
            page,
            1,
            "Здесь программа показывает, видит ли она телефон, сколько у него заряда "
            "и готов ли он к установке прошивки. Кнопки перезагрузки помогают перевести "
            "телефон в обычный режим, режим восстановления или режим загрузчика. "
            "Для новичка достаточно кнопки «Проверить телефон».",
        )

        # --- Состояние ---
        status_card = ctk.CTkFrame(page, fg_color=COLOR_CARD, corner_radius=14,
                                   border_width=1, border_color=COLOR_BORDER)
        status_card.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        status_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            status_card,
            text="Состояние телефона",
            font=ui_font(size=15, weight="bold"),
            text_color=COLOR_TEXT,
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 6))

        self.manage_status_label = ctk.CTkLabel(
            status_card,
            text=t("status_connection_none"),
            font=ui_font(size=13, weight="bold"),
            text_color=COLOR_MUTED,
        )
        self.manage_status_label.grid(row=1, column=0, sticky="w", padx=18, pady=2)

        self.battery_label = ctk.CTkLabel(
            status_card,
            text=t("status_battery_none"),
            font=ui_font(size=13, weight="bold"),
            text_color=COLOR_MUTED,
        )
        self.battery_label.grid(row=2, column=0, sticky="w", padx=18, pady=2)

        self.bootloader_label = ctk.CTkLabel(
            status_card,
            text=t("status_bootloader_none"),
            font=ui_font(size=13, weight="bold"),
            text_color=COLOR_MUTED,
        )
        self.bootloader_label.grid(row=3, column=0, sticky="w", padx=18, pady=(2, 10))

        status_buttons = ctk.CTkFrame(status_card, fg_color="transparent")
        status_buttons.grid(row=4, column=0, sticky="w", padx=18, pady=(0, 16))

        self.refresh_button = ctk.CTkButton(
            status_buttons,
            text="Проверить телефон",
            width=220,
            height=38,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ui_font(size=13, weight="bold"),
            command=self.refresh_status,
        )
        self.refresh_button.pack(side="left", padx=(0, 10))
        self._action_widgets.append(self.refresh_button)

        self.bootloader_button = ctk.CTkButton(
            status_buttons,
            text="Проверить загрузчик",
            width=220,
            height=38,
            corner_radius=10,
            fg_color=COLOR_CARD_HOVER,
            hover_color="#2A2D35",
            font=ui_font(size=13, weight="bold"),
            command=self.check_bootloader,
        )
        self.bootloader_button.pack(side="left")
        self._action_widgets.append(self.bootloader_button)

        # --- Перезагрузка ---
        reboot_card = ctk.CTkFrame(page, fg_color=COLOR_CARD, corner_radius=14,
                                   border_width=1, border_color=COLOR_BORDER)
        reboot_card.grid(row=3, column=0, sticky="ew")
        reboot_card.grid_columnconfigure(0, weight=1)
        reboot_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            reboot_card,
            text="Перезагрузка телефона",
            font=ui_font(size=15, weight="bold"),
            text_color=COLOR_TEXT,
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 10))

        reboot_buttons = [
            ("Обычная перезагрузка", "adb_reboot_system"),
            ("Режим восстановления", "adb_reboot_recovery"),
            ("Режим загрузчика", "adb_reboot_bootloader"),
            ("Включить телефон", "fastboot_reboot"),
        ]
        for index, (label, action) in enumerate(reboot_buttons):
            button = ctk.CTkButton(
                reboot_card,
                text=label,
                height=44,
                corner_radius=10,
                fg_color=COLOR_CARD_HOVER if index < 3 else COLOR_ACCENT,
                hover_color="#2A2D35" if index < 3 else COLOR_ACCENT_HOVER,
                font=ui_font(size=13, weight="bold"),
                command=lambda key=action: self.do_reboot(key),
            )
            row = 1 + index // 2
            column = index % 2
            button.grid(
                row=row,
                column=column,
                sticky="ew",
                padx=(18, 8) if column == 0 else (8, 18),
                pady=6,
            )
            self._action_widgets.append(button)

        ctk.CTkLabel(
            reboot_card,
            text=("«Режим загрузчика» и «Включить телефон» работают, когда телефон уже "
                  "в режиме загрузчика. «Обычная перезагрузка» и «Режим восстановления» "
                  "нужны, когда телефон включён и подключён по кабелю."),
            font=ui_font(size=11),
            text_color=COLOR_MUTED,
            wraplength=820,
            justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=18, pady=(10, 16))

        # --- Быстрый бэкап перед прошивкой/очисткой ---
        backup_card = ctk.CTkFrame(
            page,
            fg_color=COLOR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        backup_card.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        backup_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            backup_card,
            text="Резервная копия перед прошивкой",
            font=ui_font(size=15, weight="bold"),
            text_color=COLOR_TEXT,
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 4))

        ctk.CTkLabel(
            backup_card,
            text=("Сохраняет фото и видео (DCIM), документы и список установленных "
                  "приложений на компьютер. Делайте бэкап до прошивки или очистки — "
                  "так данные точно не потеряются."),
            font=ui_font(size=11),
            text_color=COLOR_MUTED,
            wraplength=820,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 10))

        self._backup_button = ctk.CTkButton(
            backup_card,
            text="💾 Быстрый бэкап (Фото и список приложений)",
            width=420,
            height=44,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ui_font(size=13, weight="bold"),
            command=self.quick_backup,
        )
        self._backup_button.grid(row=2, column=0, sticky="w", padx=18, pady=(0, 10))
        self._action_widgets.append(self._backup_button)

        self._backup_progress = ctk.CTkProgressBar(
            backup_card,
            height=8,
            corner_radius=4,
            progress_color=COLOR_ACCENT,
            fg_color="#2A2D35",
        )
        self._backup_progress.grid(row=3, column=0, sticky="ew", padx=18)
        self._backup_progress.set(0)

        self._backup_status = ctk.CTkLabel(
            backup_card,
            text="Готово к созданию резервной копии.",
            font=ui_font(size=11),
            text_color=COLOR_MUTED,
            anchor="w",
            wraplength=820,
            justify="left",
        )
        self._backup_status.grid(row=4, column=0, sticky="w", padx=18, pady=(6, 16))

        return page

    # ------------------------------ Здоровье и железо ------------------------------
    def _build_hardware_page(self) -> ctk.CTkScrollableFrame:
        page = self._make_scroll_page()

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(
            header,
            text="📊 Здоровье и железо",
            font=ui_font(size=22, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Реальные показатели телефона: батарея, память, процессор и безопасность",
            font=ui_font(size=12),
            text_color=COLOR_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        self._build_hint(
            page,
            1,
            "Подключите телефон по USB, включите «Отладку по USB» и нажмите "
            "«Сканировать устройство». Программа прочитает данные прямо из системы "
            "телефона: заряд и температуру батареи, остаточную ёмкость и циклы, модель, "
            "процессор, память, версию Android и состояние защиты. Это только чтение — "
            "телефон ничего не меняется.",
        )

        scan_card = ctk.CTkFrame(
            page,
            fg_color=COLOR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        scan_card.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        scan_card.grid_columnconfigure(0, weight=1)

        self.hw_scan_button = ctk.CTkButton(
            scan_card,
            text="Сканировать устройство",
            height=46,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ui_font(size=14, weight="bold"),
            command=self.scan_hardware,
        )
        self.hw_scan_button.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        self._action_widgets.append(self.hw_scan_button)

        self.hw_status = ctk.CTkLabel(
            scan_card,
            text=tr("Телефон ещё не сканировали."),
            font=ui_font(size=12),
            text_color=COLOR_MUTED,
            anchor="w",
            wraplength=780,
            justify="left",
        )
        self.hw_status.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 16))

        self.hw_results = ctk.CTkFrame(page, fg_color="transparent")
        self.hw_results.grid(row=3, column=0, sticky="ew")
        self.hw_results.grid_columnconfigure(0, weight=1)
        self.hw_results.grid_columnconfigure(1, weight=1)

        return page

    def _set_hw_status(self, text: str, color: str) -> None:
        self.hw_status.configure(text=text, text_color=color)

    def scan_hardware(self) -> None:
        self._set_hw_status(t("hw_scanning"), COLOR_MUTED)
        self._run_task(self._scan_hardware_worker)

    def _scan_hardware_worker(self) -> None:
        self.log("=== Сканирование здоровья и железа ===", "section")
        code, output = self._capture(
            [ADB, "shell", "getprop", "ro.product.model"], timeout=15.0
        )
        if code != 0 or not output.strip():
            self.log("Телефон не найден: проверьте кабель и «Отладку по USB».", "error")
            self.after(0, lambda: self._set_hw_status(
                t("hw_phone_not_found"), COLOR_ERR
            ))
            return

        props: dict[str, str] = {}
        for prop in (
            "ro.product.model",
            "ro.product.device",
            "ro.product.brand",
            "ro.build.version.release",
            "ro.build.version.security_patch",
            "ro.board.platform",
            "ro.hardware",
            "ro.build.type",
            "ro.debuggable",
            "ro.boot.flash.locked",
            "ro.boot.verifiedbootstate",
        ):
            _, prop_out = self._capture([ADB, "shell", "getprop", prop], timeout=10.0)
            props[prop] = prop_out.strip().splitlines()[-1].strip() if prop_out.strip() else ""

        _, battery_out = self._capture([ADB, "shell", "dumpsys", "battery"], timeout=15.0)
        battery = self._parse_battery(battery_out)
        self.log(f"Батарея: {battery.get('level', '?')}% • "
                 f"{battery.get('temperature', '?')} °C • "
                 f"{battery.get('voltage', '?')} мВ", "info")

        _, meminfo_out = self._capture(
            [ADB, "shell", "cat", "/proc/meminfo"], timeout=15.0
        )
        memory = self._parse_memory(meminfo_out)

        _, df_out = self._capture([ADB, "shell", "df", "-h", "/data"], timeout=15.0)
        storage = self._parse_storage(df_out)

        root = self._detect_root()
        self.log(f"Root: {'обнаружен' if root else 'не обнаружен'}.", "warn" if root else "ok")

        result = {
            "props": props,
            "battery": battery,
            "memory": memory,
            "storage": storage,
            "root": root,
        }
        self.after(0, lambda: self._render_hardware(result))

    @staticmethod
    def _parse_battery(output: str) -> dict:
        values: dict[str, str] = {}
        for line in output.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            values[key.strip().lower().replace(" ", "_")] = value.strip()

        def to_int(key: str) -> int | None:
            try:
                return int(float(values[key]))
            except (KeyError, ValueError):
                return None

        level = to_int("level")
        scale = to_int("scale") or 100
        percent = round(level * 100 / scale) if level is not None else None

        temperature_raw = to_int("temperature")
        temperature = round(temperature_raw / 10, 1) if temperature_raw is not None else None

        charge_counter = to_int("charge_counter")
        full_capacity = to_int("full_capacity") or to_int("charge_full")
        cycles = to_int("cycle_count")

        capacity_mah = None
        if charge_counter:
            capacity_mah = round(charge_counter / 1000) if charge_counter > 20000 else charge_counter
        full_mah = None
        if full_capacity:
            full_mah = round(full_capacity / 1000) if full_capacity > 20000 else full_capacity

        return {
            "level": percent,
            "temperature": temperature,
            "voltage": to_int("voltage"),
            "capacity": capacity_mah,
            "full_capacity": full_mah,
            "cycles": cycles,
        }

    @staticmethod
    def _parse_memory(output: str) -> dict:
        values: dict[str, int] = {}
        for line in output.splitlines():
            if ":" not in line:
                continue
            key, rest = line.split(":", 1)
            parts = rest.strip().split()
            if parts and parts[0].isdigit():
                values[key.strip()] = int(parts[0])

        total_kb = values.get("MemTotal")
        available_kb = values.get("MemAvailable") or values.get("MemFree")
        return {
            "total_gb": round(total_kb / 1048576, 1) if total_kb else None,
            "available_gb": round(available_kb / 1048576, 1) if available_kb else None,
        }

    @staticmethod
    def _parse_storage(output: str) -> dict:
        lines = [line for line in output.splitlines() if line.strip()]
        if len(lines) < 2:
            return {}
        header = lines[0].split()
        try:
            size_index = header.index("Size")
            used_index = header.index("Used")
            avail_index = header.index("Avail")
        except ValueError:
            return {}
        row = lines[-1].split()
        if len(row) <= max(size_index, used_index, avail_index):
            return {}
        return {
            "total": row[size_index],
            "used": row[used_index],
            "free": row[avail_index],
        }

    def _detect_root(self) -> bool:
        for args, marker in ((["which", "su"], "su"), (["which", "magisk"], "magisk")):
            _, out = self._capture([ADB, "shell"] + args, timeout=10.0)
            text = out.strip().lower()
            if marker in text and "not found" not in text:
                return True
        return False

    @staticmethod
    def _battery_health(cycles: int | None, capacity: int | None,
                        full_capacity: int | None) -> tuple[str, str]:
        ratio = None
        if capacity and full_capacity:
            ratio = capacity / full_capacity
        if (cycles is not None and cycles >= 800) or (ratio is not None and ratio < 0.70):
            return t("health_replace"), COLOR_ERR
        if (cycles is not None and cycles >= 400) or (ratio is not None and ratio < 0.85):
            return t("health_good"), "#C9B458"
        if cycles is None and ratio is None:
            return t("health_good"), COLOR_OK
        return t("health_excellent"), COLOR_OK

    def _hw_card(self, parent: ctk.CTkFrame, title: str, row: int, column: int,
                 columnspan: int = 1) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent,
            fg_color=COLOR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        card.grid(row=row, column=column, columnspan=columnspan, sticky="nsew",
                  padx=4, pady=4)
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            card,
            text=title,
            font=ui_font(size=15, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 4))
        return card

    @staticmethod
    def _hw_row(card: ctk.CTkFrame, row: int, label: str, value: str,
                color: str = COLOR_TEXT) -> None:
        ctk.CTkLabel(
            card,
            text=label,
            font=ui_font(size=12),
            text_color=COLOR_MUTED,
            anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=(18, 8), pady=3)
        ctk.CTkLabel(
            card,
            text=value,
            font=ui_font(size=12, weight="bold"),
            text_color=color,
            anchor="w",
            wraplength=320,
            justify="left",
        ).grid(row=row, column=1, sticky="w", padx=(0, 18), pady=3)

    def _render_hardware(self, result: dict) -> None:
        for child in self.hw_results.winfo_children():
            child.destroy()

        props = result["props"]
        battery = result["battery"]
        memory = result["memory"]
        storage = result["storage"]

        level = battery.get("level")
        temperature = battery.get("temperature")
        voltage = battery.get("voltage")
        capacity = battery.get("capacity")
        full_capacity = battery.get("full_capacity")
        cycles = battery.get("cycles")
        health, health_color = self._battery_health(cycles, capacity, full_capacity)

        battery_card = self._hw_card(self.hw_results, "🔋 Аккумулятор", 0, 0,
                                     columnspan=2)
        ctk.CTkLabel(
            battery_card,
            text=f"{level}%" if level is not None else "—",
            font=ui_font(size=34, weight="bold"),
            text_color=COLOR_ACCENT,
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(2, 0))
        ctk.CTkLabel(
            battery_card,
            text=t("battery_state", health=health),
            font=ui_font(size=14, weight="bold"),
            text_color=health_color,
        ).grid(row=1, column=1, sticky="e", padx=18, pady=(2, 0))

        self._hw_row(battery_card, 2, "Температура",
                     f"{temperature} °C" if temperature is not None else "нет данных")
        self._hw_row(battery_card, 3, "Напряжение",
                     f"{voltage} мВ" if voltage else "нет данных")
        self._hw_row(battery_card, 4, "Остаточная ёмкость",
                     f"{capacity} мА·ч" if capacity else "система не отдаёт")
        self._hw_row(battery_card, 5, "Полная ёмкость",
                     f"{full_capacity} мА·ч" if full_capacity else "система не отдаёт")
        self._hw_row(battery_card, 6, "Циклы зарядки",
                     str(cycles) if cycles is not None else "система не отдаёт")
        ctk.CTkFrame(battery_card, fg_color="transparent", height=8).grid(row=7, column=0)

        system_card = self._hw_card(self.hw_results, "⚙ Система и железо", 1, 0)
        cpu = props.get("ro.board.platform") or props.get("ro.hardware") or "—"
        ram_total = memory.get("total_gb")
        ram_free = memory.get("available_gb")
        ram_text = f"{ram_total} ГБ" if ram_total else "нет данных"
        if ram_free is not None:
            ram_text += f" • свободно {ram_free} ГБ"
        storage_text = "нет данных"
        if storage:
            storage_text = (f"{storage['used']} из {storage['total']}, "
                            f"свободно {storage['free']}")

        self._hw_row(system_card, 1, "Модель", props.get("ro.product.model") or "—")
        self._hw_row(system_card, 2, "Кодовое имя", props.get("ro.product.device") or "—")
        self._hw_row(system_card, 3, "Бренд", props.get("ro.product.brand") or "—")
        self._hw_row(system_card, 4, "Android", props.get("ro.build.version.release") or "—")
        self._hw_row(system_card, 5, "Патч безопасности",
                     props.get("ro.build.version.security_patch") or "—")
        self._hw_row(system_card, 6, "Процессор", cpu)
        self._hw_row(system_card, 7, "ОЗУ", ram_text)
        self._hw_row(system_card, 8, "Накопитель /data", storage_text)
        ctk.CTkFrame(system_card, fg_color="transparent", height=8).grid(row=9, column=0)

        security_card = self._hw_card(self.hw_results, "🛡 Безопасность", 1, 1)
        debuggable = props.get("ro.debuggable") == "1"
        root = result["root"]
        locked = props.get("ro.boot.flash.locked")
        if locked == "1":
            boot_text, boot_color = "заблокирован", COLOR_OK
        elif locked == "0":
            boot_text, boot_color = "разблокирован", COLOR_WARN
        else:
            state = props.get("ro.boot.verifiedbootstate", "").lower()
            if state == "green":
                boot_text, boot_color = "заблокирован", COLOR_OK
            elif state == "orange":
                boot_text, boot_color = "разблокирован", COLOR_WARN
            else:
                boot_text, boot_color = "неизвестно", COLOR_MUTED

        self._hw_row(security_card, 1, "Отладка по USB",
                     "включена" if debuggable else "выключена",
                     COLOR_WARN if debuggable else COLOR_OK)
        self._hw_row(security_card, 2, "Root",
                     "обнаружен" if root else "не обнаружен",
                     COLOR_WARN if root else COLOR_OK)
        self._hw_row(security_card, 3, "Загрузчик", boot_text, boot_color)
        self._hw_row(security_card, 4, "Тип сборки", props.get("ro.build.type") or "—")
        ctk.CTkFrame(security_card, fg_color="transparent", height=8).grid(row=5, column=0)

        self._set_hw_status(t("hw_done"), COLOR_OK)

    # ------------------------------ Инструкция ------------------------------
    def _build_guide_page(self) -> ctk.CTkScrollableFrame:
        page = self._make_scroll_page()

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(
            header,
            text="📖 Инструкция: как пользоваться",
            font=ui_font(size=22, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Простое пошаговое руководство — как для школьника",
            font=ui_font(size=12),
            text_color=COLOR_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        self._build_hint(
            page,
            1,
            "Не нужно знать сложных слов. Просто выполняй шаги по порядку: сначала "
            "подготовь телефон, потом проверь связь, затем выбери нужное действие. "
            "Если что-то непонятно — открой последний шаг «Если что-то пошло не так».",
        )

        self.guide_frame = ctk.CTkFrame(page, fg_color="transparent")
        self.guide_frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        intro = ctk.CTkFrame(self.guide_frame, fg_color="#2B2620", corner_radius=12)
        intro.pack(fill="x", padx=4, pady=(0, 8))
        ctk.CTkLabel(
            intro,
            text=("Перед началом: заряди телефон минимум до 50% и сохрани фото и "
                  "контакты. Программа сама не начнёт прошивку или очистку при заряде "
                  "ниже 30% — это защита от поломки."),
            font=ui_font(size=13),
            text_color="#B57C38",
            wraplength=780,
            justify="left",
        ).pack(anchor="w", padx=16, pady=12)

        for index, step in enumerate(GUIDE_STEPS, 1):
            self._build_guide_step(index, step)

        return page

    def _build_guide_step(self, index: int, step: dict) -> None:
        card = ctk.CTkFrame(
            self.guide_frame,
            fg_color=COLOR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        card.pack(fill="x", padx=4, pady=8)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(16, 6))
        ctk.CTkLabel(
            top,
            text=str(index),
            width=36,
            height=36,
            corner_radius=18,
            fg_color=COLOR_ACCENT,
            text_color="#ffffff",
            font=ui_font(size=15, weight="bold"),
        ).pack(side="left", padx=(0, 12))
        ctk.CTkLabel(
            top,
            text=step.get("title", ""),
            font=ui_font(size=16, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(side="left")

        for paragraph in step.get("paragraphs", []):
            ctk.CTkLabel(
                card,
                text=paragraph,
                font=ui_font(size=13),
                text_color="#C9D1D9",
                wraplength=780,
                justify="left",
            ).pack(anchor="w", padx=18, pady=3)

        bullets = step.get("bullets") or []
        if bullets:
            bullet_text = "\n".join(f"•  {item}" for item in bullets)
            ctk.CTkLabel(
                card,
                text=bullet_text,
                font=ui_font(size=13),
                text_color="#C9D1D9",
                wraplength=780,
                justify="left",
            ).pack(anchor="w", padx=18, pady=(6, 4))

        warnings = step.get("warnings") or []
        if warnings:
            warning_frame = ctk.CTkFrame(card, fg_color="#2B2620", corner_radius=10)
            warning_frame.pack(fill="x", padx=18, pady=(8, 16))
            ctk.CTkLabel(
                warning_frame,
                text="\n".join(f"⚠  {item}" for item in warnings),
                font=ui_font(size=12),
                text_color="#B57C38",
                wraplength=760,
                justify="left",
            ).pack(anchor="w", padx=14, pady=10)
        else:
            ctk.CTkFrame(card, fg_color="transparent", height=6).pack(fill="x")

    # ------------------------------ Поддержка и идеи ------------------------------
    def _build_support_page(self) -> ctk.CTkScrollableFrame:
        page = self._make_scroll_page()

        header = ctk.CTkFrame(page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(
            header,
            text="💬 Поддержка и идеи",
            font=ui_font(size=22, weight="bold"),
            text_color=COLOR_TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text=("Напишите разработчику: какую модель добавить, что исправить "
                  "или улучшить"),
            font=ui_font(size=12),
            text_color=COLOR_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        self._build_hint(
            page,
            1,
            "Это прямая связь с разработчиком. Выберите тему, укажите модель телефона "
            "и опишите просьбу своими словами. Заявка уходит в таблицу Formspree, "
            "поэтому её увидит только разработчик. Контакт указывать не обязательно, "
            "но если оставите почту или Telegram, мы сможем ответить.",
        )

        form = ctk.CTkFrame(
            page,
            fg_color=COLOR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        form.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            form,
            text="Тема обращения",
            font=ui_font(size=12, weight="bold"),
            text_color=COLOR_MUTED,
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 4))

        self.support_topic_menu = ctk.CTkOptionMenu(
            form,
            values=support_topics(),
            height=40,
            corner_radius=10,
            fg_color=COLOR_CARD_HOVER,
            button_color=COLOR_ACCENT,
            button_hover_color=COLOR_ACCENT_HOVER,
            dropdown_fg_color=COLOR_CARD,
            dropdown_hover_color=COLOR_CARD_HOVER,
            font=ui_font(size=13),
            dropdown_font=ui_font(size=13),
        )
        self.support_topic_menu.set(support_topics()[0])
        self.support_topic_menu.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))

        ctk.CTkLabel(
            form,
            text="Модель телефона",
            font=ui_font(size=12, weight="bold"),
            text_color=COLOR_MUTED,
        ).grid(row=2, column=0, sticky="w", padx=18, pady=(0, 4))

        model_row = ctk.CTkFrame(form, fg_color="transparent")
        model_row.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 12))
        model_row.grid_columnconfigure(0, weight=1)

        self.support_model_entry = ctk.CTkEntry(
            model_row,
            height=40,
            corner_radius=10,
            fg_color=COLOR_BG,
            border_color=COLOR_BORDER,
            placeholder_text="Например, Xiaomi 14 или Redmi Note 13 Pro",
            font=ui_font(size=13),
            text_color=COLOR_TEXT,
        )
        self.support_model_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.support_model_button = ctk.CTkButton(
            model_row,
            text="Определить по USB",
            width=180,
            height=40,
            corner_radius=10,
            fg_color=COLOR_CARD_HOVER,
            hover_color="#2A2D35",
            font=ui_font(size=12, weight="bold"),
            command=self._autofill_support_model,
        )
        self.support_model_button.grid(row=0, column=1)

        ctk.CTkLabel(
            form,
            text="Что добавить или поправить",
            font=ui_font(size=12, weight="bold"),
            text_color=COLOR_MUTED,
        ).grid(row=4, column=0, sticky="w", padx=18, pady=(0, 4))

        self.support_message = ctk.CTkTextbox(
            form,
            height=150,
            corner_radius=10,
            fg_color=COLOR_BG,
            border_width=1,
            border_color=COLOR_BORDER,
            font=ui_font(size=13),
            text_color=COLOR_MUTED,
            wrap="word",
        )
        self.support_message.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.support_message.insert("1.0", t("support_message_placeholder"))
        self.support_message.bind("<FocusIn>", self._clear_support_placeholder)
        self.support_message.bind("<FocusOut>", self._restore_support_placeholder)

        ctk.CTkLabel(
            form,
            text="Ваш контакт для ответа (необязательно)",
            font=ui_font(size=12, weight="bold"),
            text_color=COLOR_MUTED,
        ).grid(row=6, column=0, sticky="w", padx=18, pady=(0, 4))

        self.support_contact_entry = ctk.CTkEntry(
            form,
            height=40,
            corner_radius=10,
            fg_color=COLOR_BG,
            border_color=COLOR_BORDER,
            placeholder_text="Почта или Telegram — как вам удобнее",
            font=ui_font(size=13),
            text_color=COLOR_TEXT,
        )
        self.support_contact_entry.grid(row=7, column=0, sticky="ew", padx=18,
                                        pady=(0, 14))

        self.support_send_button = ctk.CTkButton(
            form,
            text=t("support_send"),
            height=46,
            corner_radius=10,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ui_font(size=14, weight="bold"),
            command=self._send_support_request,
        )
        self.support_send_button.grid(row=8, column=0, sticky="ew", padx=18,
                                      pady=(0, 10))

        self.support_status = ctk.CTkLabel(
            form,
            text="",
            font=ui_font(size=12, weight="bold"),
            text_color=COLOR_MUTED,
            wraplength=780,
            justify="left",
            anchor="w",
        )
        self.support_status.grid(row=9, column=0, sticky="w", padx=18, pady=(0, 16))

        return page

    def _set_support_status(self, text: str, color: str) -> None:
        self.support_status.configure(text=text, text_color=color)

    def _clear_support_placeholder(self, _event=None) -> None:
        content = self.support_message.get("1.0", "end-1c")
        if content.strip() == t("support_message_placeholder"):
            self.support_message.delete("1.0", "end")
            self.support_message.configure(text_color=COLOR_TEXT)

    def _restore_support_placeholder(self, _event=None) -> None:
        if not self._support_message_text():
            self.support_message.configure(text_color=COLOR_MUTED)
            self.support_message.insert("1.0", t("support_message_placeholder"))

    def _support_message_text(self) -> str:
        content = self.support_message.get("1.0", "end-1c").strip()
        if content == t("support_message_placeholder"):
            return ""
        return content

    def _autofill_support_model(self) -> None:
        self.support_model_button.configure(state="disabled", text=t("support_searching"))
        self._set_support_status(t("support_searching_status"), COLOR_MUTED)
        threading.Thread(target=self._autofill_support_model_worker, daemon=True).start()

    def _autofill_support_model_worker(self) -> None:
        code, output = self._capture(
            [ADB, "shell", "getprop", "ro.product.model"], timeout=15.0
        )
        model = output.strip().splitlines()[-1].strip() if output.strip() else ""
        if code == 0 and model:
            self.after(0, lambda: self._apply_support_model(model))
        else:
            self.after(0, self._support_model_not_found)

    def _apply_support_model(self, model: str) -> None:
        self.support_model_entry.delete(0, "end")
        self.support_model_entry.insert(0, model)
        self.support_model_button.configure(
            state="normal", text=tr("Определить по USB")
        )
        self._set_support_status(t("support_model_filled", model=model), COLOR_OK)
        self.log(f"Модель для заявки: {model}", "ok")

    def _support_model_not_found(self) -> None:
        self.support_model_button.configure(
            state="normal", text=tr("Определить по USB")
        )
        self.log("Модель не определена: телефон не подключён или отладка выключена.", "warn")
        self._set_support_status(t("support_model_not_found"), COLOR_WARN)

    def _send_support_request(self) -> None:
        topic = self.support_topic_menu.get()
        model = self.support_model_entry.get().strip()
        message = self._support_message_text()
        contact = self.support_contact_entry.get().strip()

        if not message:
            self._set_support_status(t("support_message_required"), COLOR_WARN)
            self.support_message.focus_set()
            return

        self.support_send_button.configure(state="disabled", text=t("support_sending"))
        self._set_support_status(t("support_sending_status"), COLOR_MUTED)
        self.log(f"Отправка заявки в Formspree: {topic}", "info")
        threading.Thread(
            target=self._send_support_worker,
            args=(topic, model, message, contact),
            daemon=True,
        ).start()

    def _send_support_worker(self, topic: str, model: str, message: str,
                             contact: str) -> None:
        payload = {
            "topic": topic,
            "model": model,
            "message": message,
            "contact": contact,
            "app_version": APP_VERSION,
            "_subject": f"KitagawaUtilits v{APP_VERSION}: {topic}",
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            FORMSPREE_URL,
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                status = getattr(response, "status", 200)
                response.read()
            if status >= 400:
                raise RuntimeError(f"сервер ответил кодом {status}")
        except urllib.error.HTTPError as exc:
            self.log(f"Formspree отклонил заявку: HTTP {exc.code}.", "error")
            self.after(0, lambda: self._support_send_failed(
                t("support_http_error", code=exc.code)
            ))
            return
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            self.log(f"Нет связи с Formspree: {reason}", "error")
            self.after(0, lambda: self._support_send_failed(t("support_no_internet")))
            return
        except Exception as exc:  # noqa: BLE001
            self.log(f"Ошибка отправки заявки: {exc}", "error")
            self.after(0, lambda: self._support_send_failed(t("support_generic_error")))
            return

        self.log("Заявка успешно отправлена в таблицу разработчика.", "ok")
        self.after(0, self._support_send_succeeded)

    def _support_send_succeeded(self) -> None:
        self.support_send_button.configure(state="normal", text=t("support_send"))
        self._set_support_status(t("support_sent"), COLOR_OK)
        self.support_message.delete("1.0", "end")
        self.support_message.configure(text_color=COLOR_MUTED)
        self.support_message.insert("1.0", t("support_message_placeholder"))

    def _support_send_failed(self, message: str) -> None:
        self.support_send_button.configure(state="normal", text=t("support_send"))
        self._set_support_status(message, COLOR_ERR)

    # ------------------------------ Журнал ------------------------------
    def _build_log_panel(self) -> None:
        panel = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=14,
                             border_width=1, border_color=COLOR_BORDER)
        panel.grid(row=1, column=0, sticky="ew", padx=18, pady=(8, 18))
        panel.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(panel, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 4))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Журнал выполнения",
            font=ui_font(size=13, weight="bold"),
            text_color=COLOR_TEXT,
        ).grid(row=0, column=0, sticky="w")

        self.log_toggle_button = ctk.CTkButton(
            header,
            text="Свернуть",
            width=90,
            height=26,
            corner_radius=8,
            fg_color=COLOR_CARD_HOVER,
            hover_color="#2A2D35",
            font=ui_font(size=11),
            command=self._toggle_log,
        )
        self.log_toggle_button.grid(row=0, column=1, sticky="e", padx=(0, 8))

        ctk.CTkButton(
            header,
            text="Очистить",
            width=90,
            height=26,
            corner_radius=8,
            fg_color=COLOR_CARD_HOVER,
            hover_color="#2A2D35",
            font=ui_font(size=11),
            command=self.clear_log,
        ).grid(row=0, column=2, sticky="e")

        self.log_box = ctk.CTkTextbox(
            panel,
            height=150,
            fg_color="#0E0F12",
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=10,
            font=ui_font(family="Consolas", size=12),
            text_color=COLOR_TEXT,
            wrap="word",
        )
        self.log_box.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))

    def _toggle_log(self) -> None:
        self._log_collapsed = not self._log_collapsed
        if self._log_collapsed:
            self.log_box.grid_remove()
            self.log_toggle_button.configure(text=t("expand"))
        else:
            self.log_box.grid()
            self.log_toggle_button.configure(text=t("collapse"))

    # ------------------------------------------------------------------
    # Логирование
    # ------------------------------------------------------------------
    def _log_widget(self):
        return getattr(self.log_box, "_textbox", self.log_box)

    def _configure_log_tags(self) -> None:
        widget = self._log_widget()
        widget.tag_config("info", foreground=COLOR_TEXT)
        widget.tag_config("muted", foreground=COLOR_MUTED)
        widget.tag_config("cmd", foreground="#D98A8A")
        widget.tag_config("ok", foreground="#8FD3B6")
        widget.tag_config("error", foreground="#D98A8A")
        widget.tag_config("warn", foreground="#C99A5B")
        widget.tag_config("section", foreground="#D98A8A")

    def log(self, message: str, tag: str = "info") -> None:
        self._log_queue.put((message, tag))

    def _drain_log_queue(self) -> None:
        widget = self._log_widget()
        had_messages = False
        while True:
            try:
                message, tag = self._log_queue.get_nowait()
            except queue.Empty:
                break
            had_messages = True
            widget.configure(state="normal")
            widget.insert("end", message + "\n", tag)
            widget.configure(state="disabled")
        if had_messages:
            widget.see("end")
        self.after(100, self._drain_log_queue)

    def clear_log(self) -> None:
        widget = self._log_widget()
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.configure(state="disabled")

    # ------------------------------------------------------------------
    # Состояние занятости
    # ------------------------------------------------------------------
    def _start_task(self) -> None:
        with self._busy_lock:
            self._busy += 1
        self.after(0, self._update_action_state)

    def _finish_task(self) -> None:
        with self._busy_lock:
            self._busy = max(0, self._busy - 1)
        self.after(0, self._update_action_state)

    def _update_action_state(self) -> None:
        state = "disabled" if self._busy > 0 else "normal"
        for widget in self._action_widgets:
            try:
                widget.configure(state=state)
            except Exception:  # noqa: BLE001
                pass

    def _run_task(self, target) -> None:
        if self._busy > 0:
            self.log("Дождитесь завершения текущей операции.", "warn")
            return

        self._start_task()

        def wrapper() -> None:
            try:
                target()
            except Exception as exc:  # noqa: BLE001
                self.log(f"Ошибка: {exc}", "error")
            finally:
                self._finish_task()

        threading.Thread(target=wrapper, daemon=True).start()

    # ------------------------------------------------------------------
    # Работа с процессами
    # ------------------------------------------------------------------
    def _stream_process(self, args: list[str]) -> int:
        self.log("$ " + " ".join(args), "cmd")
        try:
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=0,
                creationflags=popen_flags(),
                cwd=TOOLS_DIR,
            )
        except FileNotFoundError:
            self.log(f"Не найден файл: {args[0]}", "error")
            return -1
        except OSError as exc:
            self.log(f"Не удалось запустить команду: {exc}", "error")
            return -1

        assert process.stdout is not None
        buffer = ""
        while True:
            char = process.stdout.read(1)
            if not char:
                break
            if char in ("\r", "\n"):
                line = buffer.strip()
                buffer = ""
                if line:
                    self._log_command_line(line)
            else:
                buffer += char
        if buffer.strip():
            self._log_command_line(buffer.strip())

        return process.wait()

    def _log_command_line(self, line: str) -> None:
        lowered = line.lower()
        if "failed" in lowered or "error" in lowered or "cannot" in lowered:
            tag = "error"
        elif "okay" in lowered or "finished" in lowered or "success" in lowered:
            tag = "ok"
        else:
            tag = "info"
        self.log(line, tag)

    def _capture(self, args: list[str], timeout: float = 20.0) -> tuple[int, str]:
        try:
            result = subprocess.run(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=popen_flags(),
                cwd=TOOLS_DIR,
            )
        except subprocess.TimeoutExpired:
            return -1, "Таймаут выполнения команды"
        except FileNotFoundError:
            return -1, f"Не найден файл: {args[0]}"
        except OSError as exc:
            return -1, f"Ошибка запуска: {exc}"
        return result.returncode, (result.stdout or "").strip()

    # ------------------------------------------------------------------
    # Заряд батареи и защита от «окирпичивания»
    # ------------------------------------------------------------------
    def _read_battery_level(self) -> int | None:
        code, output = self._capture([ADB, "shell", "dumpsys", "battery"], timeout=8.0)
        if code != 0 or not output:
            return None
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("level:"):
                try:
                    return int(stripped.split(":", 1)[1].strip())
                except ValueError:
                    return None
        return None

    def _ensure_battery(self, action: str) -> bool:
        """Проверяет заряд телефона перед рискованным действием."""
        level = self._read_battery_level()
        if level is None:
            self.log("Не удалось узнать заряд батареи. Если телефон в режиме загрузчика — "
                     "это нормально.", "warn")
            return True
        if level < 30:
            self.log(f"Заряд телефона {level}% — меньше 30%. Действие остановлено.", "warn")
            messagebox.showwarning(
                "Сначала зарядите телефон",
                f"Сейчас заряд телефона всего {level}%.\n\n"
                f"Если начать {action} при низком заряде, телефон может выключиться "
                "посередине, и тогда он перестанет включаться.\n\n"
                "Поставьте телефон на зарядку, дождитесь хотя бы 30% (лучше 50%) и "
                "попробуйте снова.",
                parent=self,
            )
            return False
        self.log(f"Заряд телефона: {level}% — достаточно для {action}.", "ok")
        return True

    # ------------------------------------------------------------------
    # Проверка инструментов и статуса
    # ------------------------------------------------------------------
    def _check_tools(self) -> None:
        missing = [path for path in (ADB, FASTBOOT) if not os.path.isfile(path)]
        if missing:
            self.log("Не найдены программы для работы с телефоном:", "error")
            for path in missing:
                self.log(f"  {path}", "error")
            self.log("Поместите adb.exe и fastboot.exe в папку tools.", "warn")
        else:
            self.log("Программы для работы с телефоном найдены в папке tools.", "ok")

    # ------------------------------------------------------------------
    # Индикатор подключения в реальном времени
    # ------------------------------------------------------------------
    def _start_connection_watch(self) -> None:
        if self._watch_started:
            return
        self._watch_started = True
        threading.Thread(target=self._connection_watch_loop, daemon=True).start()

    def _connection_watch_loop(self) -> None:
        while True:
            try:
                if self._busy == 0:
                    self._update_connection_badge(self._detect_connection())
            except Exception:  # noqa: BLE001
                pass
            time.sleep(5)

    def _detect_connection(self) -> bool:
        _, adb_out = self._capture([ADB, "devices"], timeout=6.0)
        if self._parse_adb_devices(adb_out):
            return True
        _, fastboot_out = self._capture([FASTBOOT, "devices"], timeout=6.0)
        return any(line.strip() for line in fastboot_out.splitlines())

    def _update_connection_badge(self, connected: bool) -> None:
        if connected == self._last_connection_state:
            return
        self._last_connection_state = connected

        def apply() -> None:
            if connected:
                self.connection_badge.configure(
                    text=t("conn_connected"),
                    fg_color="#233A31",
                    text_color="#8FD3B6",
                )
            else:
                self.connection_badge.configure(
                    text=t("conn_waiting"),
                    fg_color=COLOR_CARD_HOVER,
                    text_color=COLOR_MUTED,
                )

        self.after(0, apply)

    def refresh_status(self) -> None:
        if self._status_thread and self._status_thread.is_alive():
            self.log("Проверка уже выполняется.", "warn")
            return

        self._set_status(t("status_checking"), COLOR_WARN)
        self._start_task()

        def worker() -> None:
            try:
                self._refresh_status_worker()
            except Exception as exc:  # noqa: BLE001
                self.log(f"Ошибка проверки: {exc}", "error")
                self._set_status(t("status_check_error"), COLOR_ERR)
            finally:
                self._finish_task()

        self._status_thread = threading.Thread(target=worker, daemon=True)
        self._status_thread.start()

    def _refresh_status_worker(self) -> None:
        self.log("=== Проверка подключённых телефонов ===", "section")

        adb_code, adb_out = self._capture([ADB, "devices", "-l"])
        self.log("$ adb devices -l", "cmd")
        self.log(adb_out or "(пусто)", "info")
        adb_devices = self._parse_adb_devices(adb_out)

        fb_code, fb_out = self._capture([FASTBOOT, "devices"], timeout=15.0)
        self.log("$ fastboot devices", "cmd")
        self.log(fb_out or "(пусто)", "info")
        fastboot_devices = [line for line in fb_out.splitlines() if line.strip()]

        if adb_devices:
            self._set_status(t("status_phone_found", count=len(adb_devices)), COLOR_OK)
            self.log(f"Телефонов в обычном режиме: {len(adb_devices)}", "ok")
            for device in adb_devices:
                self.log(f"  • {device}", "ok")

            level = self._read_battery_level()
            if level is not None:
                color = COLOR_OK if level >= 30 else COLOR_WARN
                self.log(f"Заряд батареи телефона: {level}%", "ok" if level >= 30 else "warn")
                self._set_battery(t("battery_level", level=level), color)
            else:
                self._set_battery(t("battery_unknown"), COLOR_MUTED)
        elif fastboot_devices:
            self._set_status(
                t("status_bootloader_mode", count=len(fastboot_devices)), COLOR_OK
            )
            self.log(f"Телефонов в режиме загрузчика: {len(fastboot_devices)}", "ok")
            for device in fastboot_devices:
                self.log(f"  • {device}", "ok")
            self._set_battery(t("battery_bootloader"), COLOR_MUTED)
        else:
            self._set_status(t("status_phone_not_found"), COLOR_ERR)
            self._set_battery(t("battery_not_connected"), COLOR_MUTED)
            self.log("Подключённые телефоны не обнаружены.", "warn")
            self.log("Проверьте кабель, «Отладку по USB» и разрешение на экране телефона.",
                     "muted")

        if fastboot_devices:
            self.log("$ fastboot getvar unlocked", "cmd")
            _, unlocked_out = self._capture([FASTBOOT, "getvar", "unlocked"], timeout=15.0)
            self.log(unlocked_out or "(нет вывода)", "info")
            value = self._parse_unlocked(unlocked_out)
            if value is None:
                self._set_bootloader(t("bootloader_unknown"), COLOR_WARN)
            elif value:
                self._set_bootloader(t("bootloader_unlocked"), COLOR_OK)
                self.log("Загрузчик разблокирован — установка прошивки разрешена.", "ok")
            else:
                self._set_bootloader(t("bootloader_locked"), COLOR_WARN)
                self.log("Загрузчик заблокирован — прошивка через режим загрузчика недоступна.",
                         "warn")

        self.log(f"Проверка завершена (обычный режим: {adb_code}, загрузчик: {fb_code}).",
                 "muted")

    @staticmethod
    def _parse_adb_devices(output: str) -> list[str]:
        devices: list[str] = []
        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith("List of devices") or line.startswith("*"):
                continue
            if "\tdevice" in line or " device " in line:
                devices.append(line.replace("\t", " "))
        return devices

    @staticmethod
    def _parse_unlocked(output: str) -> bool | None:
        for line in output.splitlines():
            line = line.strip().lower()
            if line.startswith("unlocked:"):
                value = line.split(":", 1)[1].strip()
                if value.startswith("yes") or value.startswith("true"):
                    return True
                if value.startswith("no") or value.startswith("false"):
                    return False
        return None

    def _set_status(self, text: str, color: str) -> None:
        def apply() -> None:
            self.manage_status_label.configure(
                text=t("status_connection_prefix", text=text), text_color=color
            )

        self.after(0, apply)

    def _set_battery(self, text: str, color: str) -> None:
        self.after(0, lambda: self.battery_label.configure(text=text, text_color=color))

    def _set_bootloader(self, text: str, color: str) -> None:
        self.after(0, lambda: self.bootloader_label.configure(text=text, text_color=color))

    def check_bootloader(self) -> None:
        def worker() -> None:
            self.log("=== Проверка загрузчика ===", "section")
            _, fb_out = self._capture([FASTBOOT, "devices"], timeout=15.0)
            devices = [line for line in fb_out.splitlines() if line.strip()]
            if not devices:
                self.log("Телефон в режиме загрузчика не найден.", "warn")
                self._set_bootloader(t("bootloader_not_in_mode"), COLOR_WARN)
                return

            _, unlocked_out = self._capture([FASTBOOT, "getvar", "unlocked"], timeout=15.0)
            self.log(unlocked_out or "(нет вывода)", "info")
            value = self._parse_unlocked(unlocked_out)
            if value is None:
                self.log("Не удалось определить состояние загрузчика.", "warn")
                self._set_bootloader(t("bootloader_unknown"), COLOR_WARN)
            elif value:
                self.log("Загрузчик разблокирован.", "ok")
                self._set_bootloader(t("bootloader_unlocked"), COLOR_OK)
            else:
                self.log("Загрузчик заблокирован.", "warn")
                self._set_bootloader(t("bootloader_locked"), COLOR_WARN)

        self._run_task(worker)

    # ------------------------------------------------------------------
    # Автоопределение устройства
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", (text or "").lower())

    def detect_device(self) -> None:
        self._run_task(self._detect_worker)

    def _detect_worker(self) -> None:
        self.log("=== Определение подключенного телефона ===", "section")

        code, model_out = self._capture([ADB, "shell", "getprop", "ro.product.model"])
        model = model_out.strip().splitlines()[-1].strip() if model_out.strip() else ""
        if code != 0 or not model:
            self.log("Телефон не найден или отладка по USB выключена.", "error")
            self.log("Включите «Отладку по USB» и подтвердите доступ на экране телефона.",
                     "warn")
            self._set_status(t("status_phone_not_found"), COLOR_ERR)
            return

        _, device_out = self._capture([ADB, "shell", "getprop", "ro.product.device"])
        codename = device_out.strip().splitlines()[-1].strip() if device_out.strip() else ""
        _, brand_out = self._capture([ADB, "shell", "getprop", "ro.product.brand"])
        brand = brand_out.strip().splitlines()[-1].strip() if brand_out.strip() else ""

        self.log(f"Модель: {model}", "ok")
        self.log(f"Код устройства: {codename or 'неизвестно'}", "info")
        self.log(f"Бренд: {brand or 'неизвестно'}", "info")
        self._set_status(f"телефон {model}", COLOR_OK)

        level = self._read_battery_level()
        if level is not None:
            self.log(f"Заряд батареи: {level}%", "ok" if level >= 30 else "warn")
            self._set_battery(t("battery_level", level=level),
                              COLOR_OK if level >= 30 else COLOR_WARN)

        match = self._find_firmware_for_device(model, codename)
        if not match:
            self.log(f"Телефон «{model}» ({codename}) не найден в каталоге прошивок.", "warn")
            return

        target_brand = match.get("brand", "")
        target_model = match.get("model", "")
        self.log(f"Найдено совпадение в каталоге: {target_brand} {target_model}.", "ok")

        def apply() -> None:
            if target_brand in self.brands:
                self.brand_menu.set(target_brand)
                self._on_brand_change(target_brand)
            if target_model in self._models_for_brand(target_brand):
                self.model_menu.set(target_model)
                self._rebuild_cards()
            self.show_page("catalog")

        self.after(0, apply)

    def _find_firmware_for_device(self, model: str, codename: str) -> dict | None:
        codename_l = (codename or "").strip().lower()
        if codename_l:
            for firmware in self.firmwares:
                if str(firmware.get("codename", "")).strip().lower() == codename_l:
                    return firmware

        norm_model = self._normalize(model)
        if norm_model:
            for firmware in self.firmwares:
                if self._normalize(str(firmware.get("model", ""))) == norm_model:
                    return firmware
            for firmware in self.firmwares:
                firmware_model = self._normalize(str(firmware.get("model", "")))
                if firmware_model and (firmware_model in norm_model or norm_model in firmware_model):
                    return firmware
        return None

    # ------------------------------------------------------------------
    # Переход к прошивке из каталога
    # ------------------------------------------------------------------
    def _goto_flash(self, firmware: dict) -> None:
        install_type = firmware.get("install_type", "fastboot")
        self.show_page("manual")
        self.log(f"Как установить: {firmware.get('os')} "
                 f"{firmware.get('os_version', '')}".strip(), "section")

        if install_type == "fastboot":
            self.log("Этот способ прошивает телефон через режим загрузчика. Выберите "
                     "скачанный файл .img ниже. Нужен разблокированный загрузчик.", "muted")
            self._highlight_card(self.fastboot_card)
        elif install_type == "adb_sideload":
            self.log("Этот способ устанавливает прошивку через кабель. Выберите "
                     "ZIP-архив ниже и нажмите «Установить прошивку через кабель».", "muted")
            self._highlight_card(self.sideload_card)
        else:
            self.log("Эта прошивка ставится обычным обновлением в настройках телефона. "
                     "Загрузчик трогать не нужно — используйте официальное обновление.", "warn")
            self._highlight_card(self.sideload_card)

    def _highlight_card(self, card: ctk.CTkFrame) -> None:
        try:
            card.configure(border_color=COLOR_ACCENT)
        except Exception:  # noqa: BLE001
            return

        def reset() -> None:
            try:
                card.configure(border_color=COLOR_BORDER)
            except Exception:  # noqa: BLE001
                pass

        self.after(2500, reset)

    # ------------------------------------------------------------------
    # Скачивание архивов
    # ------------------------------------------------------------------
    @staticmethod
    def _cancel_download(state: dict) -> None:
        downloader = state.get("downloader")
        if downloader is not None:
            downloader.cancel()

    def _start_download(self, firmware: dict, button: ctk.CTkButton,
                        cancel_button: ctk.CTkButton, progress: ctk.CTkProgressBar,
                        frame: ctk.CTkFrame, status: ctk.CTkLabel,
                        state: dict) -> None:
        downloader = state.get("downloader")
        if downloader is not None and downloader.is_running():
            return

        url = firmware.get("download_url") or firmware.get("page_url") or ""
        frame.grid()
        progress.stop()
        progress.configure(mode="determinate")
        progress.set(0)
        status.configure(text=t("dl_resolving"), text_color=COLOR_MUTED)
        button.configure(state="disabled", text=t("dl_downloading"))
        cancel_button.configure(state="normal")
        cancel_button.grid()
        state["determinate"] = False
        state["indeterminate"] = False
        state["path"] = ""

        self.log(f"=== Загрузка: {firmware.get('os')} {firmware.get('os_version', '')}".strip(),
                 "section")
        if url:
            self.log(f"URL: {url}", "cmd")

        def on_status(kind: str, detail: str = "") -> None:
            try:
                if kind == "resolving":
                    status.configure(text=t("dl_resolving"), text_color=COLOR_MUTED)
                elif kind == "resolved":
                    status.configure(text=t("dl_direct_found"), text_color=COLOR_OK)
                    if detail:
                        self.log(f"Прямая ссылка: {detail}", "muted")
                else:
                    status.configure(text=t("dl_connecting"), text_color=COLOR_MUTED)
            except Exception:  # noqa: BLE001
                pass

        def on_progress(downloaded: int, total: int, speed: float) -> None:
            try:
                if total and total > 0:
                    if not state.get("determinate"):
                        progress.stop()
                        progress.configure(mode="determinate")
                        state["determinate"] = True
                    progress.set(min(downloaded / total, 1.0))
                    percent = int(downloaded * 100 / max(total, 1))
                    text = (f"{percent}%  •  {format_size(downloaded)} / "
                            f"{format_size(total)}  •  {format_size(speed)}/с")
                else:
                    if not state.get("indeterminate"):
                        progress.stop()
                        progress.configure(mode="indeterminate")
                        progress.start()
                        state["indeterminate"] = True
                    text = f"{format_size(downloaded)}  •  {format_size(speed)}/с"
                status.configure(text=text, text_color=COLOR_MUTED)
            except Exception:  # noqa: BLE001
                pass

        def on_done(path: str) -> None:
            state["downloader"] = None
            state["path"] = path
            try:
                progress.stop()
                progress.configure(mode="determinate")
                progress.set(1)
                status.configure(
                    text=t("dl_done", name=os.path.basename(path)),
                    text_color=COLOR_OK,
                )
                cancel_button.grid_remove()
                button.configure(state="normal", text=t("dl_goto_install"))
                button.configure(
                    command=lambda fw=firmware, p=path: self._install_downloaded(fw, p)
                )
            except Exception:  # noqa: BLE001
                pass
            self.log(f"Прошивка скачана: {path}", "ok")
            self.log(t("dl_saved_hint"), "muted")

        def on_fallback(page_url: str, reason: str = "") -> None:
            state["downloader"] = None
            reason_text = reason or "сайт не отдал прямую ссылку на файл"
            try:
                progress.stop()
                progress.configure(mode="determinate")
                progress.set(0)
                cancel_button.grid_remove()
                button.configure(state="normal", text=t("dl_download"))
                status.configure(
                    text=f"Браузер: {reason_text}", text_color=COLOR_WARN
                )
            except Exception:  # noqa: BLE001
                pass
            self.log(t("dl_fallback"), "warn")
            self.log(f"Причина: {reason_text}.", "warn")
            if page_url:
                self.log(f"Страница загрузки: {page_url}", "muted")
                try:
                    webbrowser.open(page_url)
                except Exception:  # noqa: BLE001
                    pass
                try:
                    messagebox.showwarning(
                        "Открываю браузер",
                        "Прямую ссылку на файл получить не удалось.\n\n"
                        f"Причина: {reason_text}.\n\n"
                        "Страница загрузки открыта в браузере — скачайте файл там, "
                        "а затем выберите его во вкладке «Установка прошивки».",
                        parent=self,
                    )
                except Exception:  # noqa: BLE001
                    pass

        def on_error(message: str) -> None:
            state["downloader"] = None
            try:
                progress.stop()
                progress.configure(mode="determinate")
                progress.set(0)
                cancel_button.grid_remove()
                button.configure(state="normal", text=t("dl_download"))
                status.configure(text=t("dl_error", error=message), text_color=COLOR_ERR)
            except Exception:  # noqa: BLE001
                pass
            self.log(f"Ошибка загрузки: {message}", "error")

        def on_cancel() -> None:
            state["downloader"] = None
            try:
                progress.stop()
                progress.configure(mode="determinate")
                progress.set(0)
                cancel_button.grid_remove()
                button.configure(state="normal", text=t("dl_download"))
                status.configure(text=t("dl_cancelled"), text_color=COLOR_WARN)
            except Exception:  # noqa: BLE001
                pass
            self.log(t("dl_cancelled"), "warn")

        downloader = FirmwareDownloader(
            self,
            firmware,
            on_progress=on_progress,
            on_status=on_status,
            on_done=on_done,
            on_fallback=on_fallback,
            on_error=on_error,
            on_cancel=on_cancel,
        )
        state["downloader"] = downloader
        downloader.start()

    def _install_downloaded(self, firmware: dict, path: str) -> None:
        """Переход во вкладку установки с уже подставленным файлом."""
        if not path or not os.path.isfile(path):
            messagebox.showwarning(APP_NAME, t("dl_file_missing"), parent=self)
            return

        if os.path.splitext(path)[1].lower() == ".img":
            self._img_path = path
            self._set_entry_text(self.img_entry, path)
            self.log(f"Образ подставлен для прошивки: {path}", "ok")
        else:
            self._zip_path = path
            self._set_entry_text(self.zip_entry, path)
            self.log(f"Архив подставлен для установки: {path}", "ok")

        self._goto_flash(firmware)

    # ------------------------------------------------------------------
    # Выбор файлов
    # ------------------------------------------------------------------
    @staticmethod
    def _set_entry_text(entry: ctk.CTkEntry, text: str) -> None:
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, text)
        entry.configure(state="readonly")

    def choose_img(self) -> None:
        path = filedialog.askopenfilename(
            title="Выберите файл образа (.img)",
            filetypes=[("Образы разделов", "*.img"), ("Все файлы", "*.*")],
        )
        if path:
            self._img_path = path
            self._set_entry_text(self.img_entry, path)
            self.log(f"Выбран образ: {path}", "muted")

    def choose_zip(self) -> None:
        path = filedialog.askopenfilename(
            title="Выберите ZIP-архив с прошивкой",
            filetypes=[("ZIP-архивы", "*.zip"), ("Все файлы", "*.*")],
        )
        if path:
            self._zip_path = path
            self._set_entry_text(self.zip_entry, path)
            self.log(f"Выбран архив: {path}", "muted")

    # ------------------------------------------------------------------
    # Прошивка через Fastboot
    # ------------------------------------------------------------------
    def start_flash(self) -> None:
        partition = self.partition_menu.get()
        image = self._img_path

        if not image or not os.path.isfile(image):
            messagebox.showwarning(APP_NAME, "Сначала выберите файл .img для прошивки.",
                                   parent=self)
            return

        if not self._ensure_battery("прошивки"):
            return

        confirmed = messagebox.askyesno(
            "Подтверждение прошивки",
            f"Прошить раздел «{partition}»?\n\n"
            f"Файл: {os.path.basename(image)}\n"
            f"Путь: {image}\n\n"
            "Телефон должен быть в режиме загрузчика, а загрузчик — разблокирован. "
            "Не выдёргивайте кабель до завершения.",
            icon="warning",
            parent=self,
        )
        if not confirmed:
            self.log("Прошивка отменена пользователем.", "warn")
            return

        def worker() -> None:
            self.log(f"=== Прошивка раздела {partition} ===", "section")
            code = self._stream_process([FASTBOOT, "flash", partition, image])
            if code == 0:
                self.log(f"Раздел «{partition}» успешно прошит.", "ok")
            else:
                self.log(f"Прошивка раздела «{partition}» завершилась с ошибкой "
                         f"(код {code}).", "error")

        self._run_task(worker)

    # ------------------------------------------------------------------
    # Sideload
    # ------------------------------------------------------------------
    def start_sideload(self) -> None:
        archive = self._zip_path
        if not archive or not os.path.isfile(archive):
            messagebox.showwarning(APP_NAME, "Сначала выберите ZIP-архив с прошивкой.",
                                   parent=self)
            return

        if not self._ensure_battery("установки прошивки"):
            return

        confirmed = messagebox.askyesno(
            "Подтверждение установки",
            f"Установить прошивку через кабель?\n\n"
            f"Файл: {os.path.basename(archive)}\n"
            f"Путь: {archive}\n\n"
            "На телефоне должно быть выбрано «Применить обновление из ADB». "
            "Не выдёргивайте кабель до завершения.",
            icon="warning",
            parent=self,
        )
        if not confirmed:
            self.log("Установка отменена пользователем.", "warn")
            return

        def worker() -> None:
            self.log("=== Установка прошивки через кабель ===", "section")
            code = self._stream_process([ADB, "sideload", archive])
            if code == 0:
                self.log("Прошивка успешно установлена.", "ok")
            else:
                self.log(f"Установка завершилась с ошибкой (код {code}).", "error")

        self._run_task(worker)

    # ------------------------------------------------------------------
    # Быстрый бэкап: фото, документы и список приложений
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_folder_name(value: str) -> str:
        name = re.sub(r'[<>:"/\\|?*]', "_", (value or "").strip())
        name = re.sub(r"\s+", "_", name).strip("._")
        return name or "device"

    def _set_backup_progress(self, value: float, text: str,
                             color: str = COLOR_MUTED) -> None:
        def apply() -> None:
            try:
                if self._backup_progress is not None:
                    self._backup_progress.set(max(0.0, min(1.0, value)))
                if self._backup_status is not None:
                    self._backup_status.configure(text=text, text_color=color)
            except Exception:  # noqa: BLE001
                pass

        try:
            self.after(0, apply)
        except Exception:  # noqa: BLE001
            pass

    def quick_backup(self) -> None:
        """Кнопка «💾 Быстрый бэкап (Фото и список приложений)»."""
        if self._busy > 0:
            self.log("Дождитесь завершения текущей операции.", "warn")
            return
        self._set_backup_progress(0.0, "Проверяю подключение телефона...")
        self._run_task(self._quick_backup_worker)

    def _quick_backup_worker(self) -> None:
        self.log("=== Быстрый бэкап: фото и список приложений ===", "section")
        code, model_out = self._capture(
            [ADB, "shell", "getprop", "ro.product.model"], timeout=15.0
        )
        model = model_out.strip().splitlines()[-1].strip() if model_out.strip() else ""
        if code != 0 or not model:
            self._set_backup_progress(
                0.0, "Телефон не найден — включите отладку по USB.", COLOR_ERR
            )
            self.log(
                "Бэкап не начат: телефон не найден или отладка по USB выключена.",
                "error",
            )
            return

        _, code_out = self._capture(
            [ADB, "shell", "getprop", "ro.product.device"], timeout=15.0
        )
        codename = code_out.strip().splitlines()[-1].strip() if code_out.strip() else ""
        date = time.strftime("%Y-%m-%d_%H-%M")
        folder = os.path.join(
            BACKUP_ROOT, f"{self._safe_folder_name(model)}_{date}"
        )
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as exc:
            self._set_backup_progress(0.0, f"Не удалось создать папку: {exc}", COLOR_ERR)
            self.log(f"Не удалось создать папку бэкапа: {exc}", "error")
            return

        self.log(f"Папка бэкапа: {folder}", "info")
        self.log(f"Модель: {model} ({codename or '—'})", "ok")

        steps = (
            ("фото и видео (DCIM)", "/sdcard/DCIM", "DCIM"),
            ("документы", "/sdcard/Documents", "Documents"),
        )
        total = len(steps) + 1
        done = 0
        for label, remote, sub in steps:
            self._set_backup_progress(
                0.1 + 0.6 * done / total, f"Копирую {label}..."
            )
            code, output = self._capture(
                [ADB, "pull", remote, os.path.join(folder, sub)], timeout=3600.0
            )
            if code == 0:
                self.log(f"{label.capitalize()}: сохранено.", "ok")
            else:
                self.log(
                    f"{label.capitalize()}: папка пуста или недоступна "
                    f"({output.strip()[:160]}).",
                    "warn",
                )
            done += 1

        self._set_backup_progress(0.75, "Сохраняю список приложений...")
        code, packages = self._capture(
            [ADB, "shell", "pm", "list", "packages", "-f"], timeout=120.0
        )
        if code != 0:
            code, packages = self._capture(
                [ADB, "shell", "pm", "list", "packages"], timeout=120.0
            )
        packages_path = os.path.join(folder, "packages.txt")
        try:
            with open(packages_path, "w", encoding="utf-8") as handle:
                handle.write(f"# {model} ({codename}) — {date}\n")
                handle.write(packages or "")
                handle.write("\n")
        except OSError as exc:
            self.log(f"Не удалось сохранить список приложений: {exc}", "error")
        else:
            count = len([line for line in packages.splitlines() if line.strip()])
            self.log(
                f"Список приложений: {count} пакетов -> {packages_path}", "ok"
            )

        try:
            with open(os.path.join(folder, "info.txt"), "w", encoding="utf-8") as handle:
                handle.write(
                    f"Модель: {model}\nКод устройства: {codename}\nДата: {date}\n"
                )
        except OSError:
            pass

        self._set_backup_progress(1.0, f"Бэкап готов: {folder}", COLOR_OK)
        self.log(f"Бэкап завершён: {folder}", "ok")
        self.after(
            0,
            lambda: messagebox.showinfo(
                "Бэкап готов",
                f"Резервная копия сохранена:\n{folder}\n\n"
                "Внутри: папки DCIM и Documents (если были на телефоне) "
                "и список приложений packages.txt.",
                parent=self,
            ),
        )

    # ------------------------------------------------------------------
    # Перезагрузка
    # ------------------------------------------------------------------
    def do_reboot(self, action: str) -> None:
        commands = {
            "adb_reboot_system": ([ADB, "reboot"], "Обычная перезагрузка"),
            "adb_reboot_recovery": ([ADB, "reboot", "recovery"],
                                    "Перезагрузка в режим восстановления"),
            "adb_reboot_bootloader": ([ADB, "reboot", "bootloader"],
                                      "Перезагрузка в режим загрузчика"),
            "fastboot_reboot": ([FASTBOOT, "reboot"],
                                "Включение телефона из режима загрузчика"),
        }
        command, description = commands[action]

        def worker() -> None:
            self.log(f"=== {description} ===", "section")
            code = self._stream_process(command)
            if code == 0:
                self.log("Команда перезагрузки выполнена.", "ok")
            else:
                self.log(f"Не удалось выполнить перезагрузку (код {code}).", "error")

        self._run_task(worker)


def main() -> None:
    app = KitagawaUtilitsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
