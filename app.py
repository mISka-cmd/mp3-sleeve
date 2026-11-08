"""Вписывает обложку в файлы MP3, не меняя звук."""

import ctypes
import io
import os
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog

from mutagen.id3 import APIC, Encoding, PictureType, TALB, TIT2, TPE1
from mutagen.mp3 import HeaderNotFoundError, MP3
from PIL import Image, ImageOps, ImageTk, UnidentifiedImageError

MAX_SIDE = 1400
JPEG_QUALITY = 90
COVER = 320
ROW_H = 36

BG = "#fafafa"
CARD = "#ffffff"
RAISED = "#f4f4f5"
LINE = "#e7e7e7"
TEXT = "#171717"
SECONDARY = "#525252"
MUTED = "#737373"
ACCENT = "#9a3412"
INK = "#171717"
ON_INK = "#fafafa"
DANGER = "#dc2626"
HOVER_INK = "#2a2a2a"


def enable_dpi() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def default_music_dir() -> str:
    music = os.path.join(os.path.expanduser("~"), "Music")
    if os.path.isdir(music):
        return music
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.path.isdir(desktop):
        return desktop
    return os.path.expanduser("~")


def explain(exc: BaseException) -> str:
    current: BaseException | None = exc
    seen: list[int] = []
    while current is not None and id(current) not in seen:
        seen.append(id(current))
        if isinstance(current, PermissionError):
            return "файл занят или нет прав на запись"
        if isinstance(current, FileNotFoundError):
            return "файл не найден"
        if isinstance(current, HeaderNotFoundError):
            return "это не MP3"
        current = current.__cause__ or current.__context__
    text = str(exc).strip()
    low = text.lower()
    if "permission" in low or "access is denied" in low or "отказано" in low:
        return "файл занят или нет прав на запись"
    if "can't sync" in low or "invalid header" in low or "header not found" in low:
        return "это не MP3"
    return text or "неизвестная ошибка"


def cover_to_jpeg(path: str) -> bytes:
    """Любая картинка становится JPEG. Длинная сторона не больше 1400 пикселей."""
    try:
        with Image.open(path) as source:
            source.seek(0)
            image = ImageOps.exif_transpose(source) or source
            if image.mode in ("RGBA", "LA") or (
                image.mode == "P" and "transparency" in image.info
            ):
                rgba = image.convert("RGBA")
                # В JPEG нет прозрачности, поэтому кладём картинку на белый фон.
                flat = Image.new("RGB", rgba.size, (255, 255, 255))
                flat.paste(rgba, mask=rgba.getchannel("A"))
                image = flat
            else:
                image = image.convert("RGB")
            image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            return buffer.getvalue()
    except UnidentifiedImageError:
        raise ValueError("это не картинка") from None
    except Image.DecompressionBombError:
        raise ValueError("картинка слишком большая") from None


def read_cover(path: str) -> bytes | None:
    audio = MP3(path)
    tags = audio.tags
    if tags is None:
        return None
    pictures = tags.getall("APIC")
    if not pictures:
        return None
    for picture in pictures:
        if int(picture.type) == int(PictureType.COVER_FRONT):
            return bytes(picture.data)
    return bytes(pictures[0].data)


def write_cover(path: str, jpeg: bytes) -> None:
    audio = MP3(path)
    if audio.tags is None:
        audio.add_tags()
    audio.tags.delall("APIC")
    audio.tags.add(
        APIC(
            encoding=Encoding.LATIN1,
            mime="image/jpeg",
            type=PictureType.COVER_FRONT,
            desc="Cover",
            data=jpeg,
        )
    )
    # В файле остаётся ID3v2.3: его читают Проводник и обычные плееры.
    audio.tags.update_to_v23()
    audio.save(v1=1, v2_version=3)


def remove_cover(path: str) -> None:
    audio = MP3(path)
    if audio.tags is None:
        return
    audio.tags.delall("APIC")
    audio.tags.update_to_v23()
    audio.save(v1=1, v2_version=3)


TEXT_TAGS = (
    ("title", "TIT2", TIT2),
    ("artist", "TPE1", TPE1),
    ("album", "TALB", TALB),
)


def _frame_text(tags, frame_id: str) -> str:
    if tags is None:
        return ""
    frames = tags.getall(frame_id)
    if not frames:
        return ""
    parts = [str(part) for part in frames[0].text if str(part)]
    return " / ".join(parts)


def read_info(path: str) -> dict[str, str]:
    tags = MP3(path).tags
    return {key: _frame_text(tags, frame_id) for key, frame_id, _frame in TEXT_TAGS}


def write_info(path: str, values: dict[str, str]) -> None:
    audio = MP3(path)
    if audio.tags is None:
        audio.add_tags()
    for key, frame_id, frame_cls in TEXT_TAGS:
        if key not in values:
            continue
        audio.tags.delall(frame_id)
        text = values[key].strip()
        if text:
            audio.tags.add(frame_cls(encoding=Encoding.UTF16, text=[text]))
    audio.tags.update_to_v23()
    audio.save(v1=1, v2_version=3)


def track_word(count: int) -> str:
    mod = count % 100
    if 11 <= mod <= 14:
        return "треков"
    last = count % 10
    if last == 1:
        return "трек"
    if 2 <= last <= 4:
        return "трека"
    return "треков"


def ellipsis(text: str, width: int, font: tkfont.Font) -> str:
    if width <= 0:
        return ""
    if font.measure(text) <= width:
        return text
    mark = "…"
    trimmed = text
    while trimmed and font.measure(trimmed + mark) > width:
        trimmed = trimmed[:-1]
    return (trimmed + mark) if trimmed else mark


def row_parts(paths: list[str]) -> list[tuple[str, str]]:
    names = [os.path.basename(path) for path in paths]
    counts: dict[str, int] = {}
    for name in names:
        counts[name] = counts.get(name, 0) + 1
    parts: list[tuple[str, str]] = []
    for path, name in zip(paths, names):
        folder = os.path.basename(os.path.dirname(path)) if counts[name] > 1 else ""
        parts.append((name, folder))
    return parts


class TextField(tk.Frame):
    def __init__(self, master: tk.Misc, title: str) -> None:
        super().__init__(master, bg=BG)
        self.base = title
        self.label = tk.Label(
            self, text=title, bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w"
        )
        self.label.pack(anchor="w", pady=(0, 4))
        self.box = tk.Frame(
            self,
            bg=CARD,
            height=36,
            highlightthickness=1,
            highlightbackground=LINE,
            highlightcolor=TEXT,
            bd=0,
        )
        self.box.pack(fill="x")
        self.box.pack_propagate(False)
        self.entry = tk.Entry(
            self.box,
            relief="flat",
            bd=0,
            bg=CARD,
            fg=TEXT,
            insertbackground=TEXT,
            font=("Segoe UI", 10),
            highlightthickness=0,
        )
        self.entry.pack(fill="both", expand=True, padx=8, pady=6)
        self.entry.bind("<FocusIn>", lambda _event: self.box.configure(highlightbackground=TEXT))
        self.entry.bind("<FocusOut>", lambda _event: self.box.configure(highlightbackground=LINE))

    def set_mixed(self, mixed: bool) -> None:
        self.label.configure(text=f"{self.base} · разные" if mixed else self.base)

    def get(self) -> str:
        return self.entry.get().strip()

    def set(self, value: str) -> None:
        self.entry.delete(0, "end")
        if value:
            self.entry.insert(0, value)


class QuietButton(tk.Label):
    def __init__(self, master: tk.Misc, text: str, command) -> None:
        super().__init__(
            master,
            text=text,
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10),
            cursor="hand2",
            padx=0,
            pady=8,
        )
        self.command = command
        self._inside = False
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", self._click)
        self.bind("<Return>", self._key)
        self.bind("<space>", self._key)
        self.configure(takefocus=True)

    def _enter(self, _event: tk.Event) -> None:
        self._inside = True
        self.configure(fg=TEXT)

    def _leave(self, _event: tk.Event) -> None:
        self._inside = False
        self.configure(fg=MUTED)

    def _click(self, _event: tk.Event) -> None:
        self.command()

    def _key(self, _event: tk.Event) -> str:
        self.command()
        return "break"


class FillButton(tk.Frame):
    def __init__(self, master: tk.Misc, text: str, command, kind: str) -> None:
        self.kind = kind
        self.command = command
        self._inside = False
        self._down = False
        line = LINE if kind == "secondary" else INK
        super().__init__(
            master,
            bg=self._fill("normal"),
            height=ROW_H,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=line,
            highlightcolor=TEXT,
            bd=0,
            takefocus=True,
        )
        self.pack_propagate(False)
        self.label = tk.Label(
            self,
            text=text,
            bg=self._fill("normal"),
            fg=ON_INK if kind == "primary" else TEXT,
            font=("Segoe UI", 10),
            cursor="hand2",
        )
        self.label.place(relx=0.5, rely=0.5, anchor="center")
        for widget in (self, self.label):
            widget.bind("<Enter>", self._enter)
            widget.bind("<Leave>", self._leave)
            widget.bind("<Button-1>", self._press)
            widget.bind("<ButtonRelease-1>", self._release)
        self.bind("<Return>", self._key)
        self.bind("<space>", self._key)
        self.bind("<FocusIn>", lambda _event: self._paint())
        self.bind("<FocusOut>", lambda _event: self._paint())

    def _fill(self, mode: str) -> str:
        if self.kind == "primary":
            if mode == "down":
                return "#000000"
            if mode == "hover":
                return HOVER_INK
            return INK
        if mode in ("hover", "down"):
            return RAISED
        return CARD

    def _mode(self) -> str:
        if self._down:
            return "down"
        if self._inside:
            return "hover"
        return "normal"

    def _paint(self) -> None:
        fill = self._fill(self._mode())
        self.configure(bg=fill)
        self.label.configure(bg=fill)

    def _enter(self, _event: tk.Event) -> None:
        self._inside = True
        self._paint()

    def _leave(self, _event: tk.Event) -> None:
        self._inside = False
        self._down = False
        self._paint()

    def _press(self, _event: tk.Event) -> None:
        self._down = True
        self.focus_set()
        self._paint()

    def _release(self, _event: tk.Event) -> None:
        armed = self._down and self._inside
        self._down = False
        self._paint()
        if armed:
            self.command()

    def _key(self, _event: tk.Event) -> str:
        self.command()
        return "break"


class TrackPane(tk.Frame):
    def __init__(self, master: tk.Misc, on_click) -> None:
        super().__init__(
            master,
            bg=CARD,
            highlightthickness=1,
            highlightbackground=LINE,
            highlightcolor=LINE,
            bd=0,
        )
        self.on_click = on_click
        self.font_body = tkfont.Font(family="Segoe UI", size=10)
        self.font_meta = tkfont.Font(family="Segoe UI", size=9)
        self.font_num = tkfont.Font(family="Consolas", size=10)
        self.entries: list[tuple[str, str]] = []
        self.rows: list[tk.Frame] = []
        self.selected: set[int] = set()
        self.hover: int | None = None

        self.empty = tk.Label(
            self,
            text="Добавьте файлы или папку",
            bg=CARD,
            fg=MUTED,
            font=self.font_body,
        )
        self.canvas = tk.Canvas(self, bg=CARD, highlightthickness=0, bd=0)
        self.inner = tk.Frame(self.canvas, bg=CARD)
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.scroll = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview, width=12)
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.inner.bind("<Configure>", self._on_inner)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)
        self.empty.place(relx=0.5, rely=0.5, anchor="center")

    def _bind_wheel(self, _event: tk.Event) -> None:
        self.canvas.bind_all("<MouseWheel>", self._wheel)

    def _unbind_wheel(self, _event: tk.Event) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _wheel(self, event: tk.Event) -> None:
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def _on_scroll(self, first: str, last: str) -> None:
        self.scroll.set(first, last)
        self._toggle_scroll()

    def _on_inner(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._toggle_scroll()

    def _on_canvas(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.window_id, width=event.width)
        self._fit(event.width)
        self._toggle_scroll()

    def _toggle_scroll(self) -> None:
        bbox = self.canvas.bbox("all")
        needed = bool(bbox) and bbox[3] > self.canvas.winfo_height() + 1 and self.entries
        if needed:
            if not self.scroll.winfo_ismapped():
                self.scroll.pack(side="right", fill="y")
        elif self.scroll.winfo_ismapped():
            self.scroll.pack_forget()

    def set_entries(self, entries: list[tuple[str, str]], selected: set[int]) -> None:
        self.selected = set(selected)
        self.hover = None
        if entries == self.entries and len(self.rows) == len(entries):
            self._paint()
            return
        self.entries = list(entries)
        for child in self.inner.winfo_children():
            child.destroy()
        self.rows = []
        if not entries:
            self.canvas.pack_forget()
            self.scroll.pack_forget()
            self.empty.place(relx=0.5, rely=0.5, anchor="center")
            return
        self.empty.place_forget()
        self.canvas.pack(side="left", fill="both", expand=True)
        for index, (name, folder) in enumerate(entries):
            self.rows.append(self._build_row(index, name, folder))
        self._paint()
        self.canvas.update_idletasks()
        self._fit(self.canvas.winfo_width())
        self._on_inner(tk.Event())

    def paint(self, selected: set[int]) -> None:
        self.selected = set(selected)
        self._paint()

    def _build_row(self, index: int, name: str, folder: str) -> tk.Frame:
        row = tk.Frame(self.inner, bg=CARD, height=ROW_H)
        row.pack(fill="x")
        row.pack_propagate(False)
        row.name_full = name
        row.folder_full = folder
        number = tk.Label(
            row,
            text=f"{index + 1:02d}",
            bg=CARD,
            fg=MUTED,
            font=self.font_num,
            width=3,
            anchor="e",
        )
        number.pack(side="left", padx=(16, 8))
        title = tk.Label(row, text=name, bg=CARD, fg=TEXT, font=self.font_body, anchor="w")
        title.pack(side="left")
        folder_label = tk.Label(row, text=folder, bg=CARD, fg=MUTED, font=self.font_meta, anchor="w")
        if folder:
            folder_label.pack(side="left", padx=(8, 0))
        row.number = number
        row.title = title
        row.folder_label = folder_label
        widgets = (row, number, title, folder_label)

        def click(event: tk.Event, row_index: int = index) -> None:
            self.on_click(row_index, event)

        def enter(_event: tk.Event, row_index: int = index) -> None:
            self.hover = row_index
            self._paint()

        def leave(_event: tk.Event, row_index: int = index) -> None:
            if self.hover == row_index:
                self.hover = None
                self._paint()

        for widget in widgets:
            widget.bind("<Button-1>", click)
            widget.bind("<Enter>", enter)
            widget.bind("<Leave>", leave)
        return row

    def _paint(self) -> None:
        for index, row in enumerate(self.rows):
            chosen = index in self.selected
            hot = self.hover == index and not chosen
            fill = RAISED if chosen or hot else CARD
            number = ACCENT if chosen else MUTED
            for widget in (row, row.number, row.title, row.folder_label):
                widget.configure(bg=fill)
            row.number.configure(fg=number)
            row.title.configure(fg=TEXT)
            row.folder_label.configure(fg=MUTED)

    def _fit(self, width: int) -> None:
        if width <= 1:
            return
        for row in self.rows:
            folder = row.folder_full
            folder_width = 0
            if folder:
                folder_width = min(self.font_meta.measure(folder), max(48, int(width * 0.28)))
                row.folder_label.configure(text=ellipsis(folder, folder_width, self.font_meta))
                folder_width += 8
            name_width = max(32, width - 16 - 36 - 8 - folder_width - 16)
            row.title.configure(text=ellipsis(row.name_full, name_width, self.font_body))

    def reveal(self, index: int) -> None:
        if not self.rows:
            return
        top = index * ROW_H
        bottom = top + ROW_H
        height = max(self.canvas.winfo_height(), 1)
        first = self.canvas.canvasy(0)
        last = first + height
        if top < first:
            self.canvas.yview_moveto(top / max(len(self.rows) * ROW_H, 1))
        elif bottom > last:
            self.canvas.yview_moveto(max(bottom - height, 0) / max(len(self.rows) * ROW_H, 1))


class App(tk.Tk):
    def __init__(self) -> None:
        enable_dpi()
        super().__init__()
        self.title("Sleeve")
        self.minsize(800, 760)
        self.geometry("980x820")
        self.configure(bg=BG)

        self.paths: list[str] = []
        self.selected: set[int] = set()
        self.anchor: int | None = None
        self.cover_jpeg: bytes | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.image_item: int | None = None
        self.last_audio_dir = default_music_dir()
        self.last_image_dir = self.last_audio_dir

        self._build()
        self.bind("<Delete>", self._remove_selected)
        self.bind("<Up>", lambda _event: self._move(-1))
        self.bind("<Down>", lambda _event: self._move(1))
        self.bind("<Configure>", self._wrap_status, add="+")

    def _build(self) -> None:
        header = tk.Frame(self, bg=BG, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="Sleeve", bg=BG, fg=TEXT, font=("Segoe UI", 13)).place(
            x=24, rely=0.5, anchor="w"
        )
        self.count_label = tk.Label(
            header, text="0 треков", bg=BG, fg=MUTED, font=("Consolas", 9)
        )
        self.count_label.place(relx=1, x=-24, rely=0.5, anchor="e")

        tk.Frame(self, bg=LINE, height=1).pack(fill="x")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=24)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, minsize=COVER)
        body.rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 24))
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        self.tracks = TrackPane(left, self._click_row)
        self.tracks.grid(row=0, column=0, sticky="nsew")

        form = tk.Frame(left, bg=BG)
        form.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        self.fields: dict[str, TextField] = {}
        self.mixed = {"title": False, "artist": False, "album": False}
        for index, (key, title) in enumerate(
            (("title", "Название"), ("artist", "Исполнитель"), ("album", "Альбом"))
        ):
            field = TextField(form, title)
            field.pack(fill="x", pady=(8 if index else 0, 0))
            self.fields[key] = field
        info_button = FillButton(form, "Записать сведения", self._write_info, "secondary")
        info_button.configure(width=220)
        info_button.pack(anchor="w", pady=(16, 0))

        actions = tk.Frame(left, bg=BG)
        actions.grid(row=2, column=0, sticky="w", pady=(16, 0))
        QuietButton(actions, "Добавить файлы", self._add_files).pack(side="left", padx=(0, 16))
        QuietButton(actions, "Добавить папку", self._add_folder).pack(side="left", padx=(0, 16))
        QuietButton(actions, "Убрать из списка", self._remove_selected).pack(side="left")

        right = tk.Frame(body, bg=BG, width=COVER)
        right.grid(row=0, column=1, sticky="nw")
        right.columnconfigure(0, minsize=COVER)

        self.sleeve = tk.Canvas(
            right, width=COVER, height=COVER, bg=CARD, highlightthickness=0, bd=0, cursor="hand2"
        )
        self.frame_id = self.sleeve.create_rectangle(1, 1, COVER - 2, COVER - 2, outline=LINE)
        self.empty_id = self.sleeve.create_text(
            COVER // 2,
            COVER // 2,
            text="Нет обложки",
            fill=MUTED,
            font=("Segoe UI", 10),
        )
        self.sleeve.grid(row=0, column=0, sticky="w")
        self.sleeve.bind("<Button-1>", lambda _event: self._choose_cover())
        self.sleeve.bind("<Return>", lambda _event: self._choose_cover())
        self.sleeve.bind("<Enter>", self._sleeve_enter)
        self.sleeve.bind("<Leave>", self._sleeve_leave)
        self.sleeve.configure(takefocus=True)

        self.view_caption = tk.StringVar(value="")
        self.view_label = tk.Label(
            right,
            textvariable=self.view_caption,
            bg=BG,
            fg=SECONDARY,
            font=("Segoe UI", 10),
            anchor="w",
            height=1,
        )
        self.view_label.grid(row=1, column=0, sticky="ew", pady=(12, 0))

        self.chosen_caption = tk.StringVar(value="К записи · не выбрана")
        self.chosen_label = tk.Label(
            right,
            textvariable=self.chosen_caption,
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9),
            anchor="w",
        )
        self.chosen_label.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self.view_label.grid_remove()

        QuietButton(right, "Выбрать обложку", self._choose_cover).grid(
            row=3, column=0, sticky="w", pady=(12, 0)
        )
        FillButton(right, "Вписать в выбранные", self._write_selected, "primary").grid(
            row=4, column=0, sticky="ew", pady=(16, 0)
        )
        FillButton(right, "Вписать во все", self._write_all, "secondary").grid(
            row=5, column=0, sticky="ew", pady=(8, 0)
        )
        QuietButton(right, "Удалить обложку", self._remove_covers).grid(
            row=6, column=0, sticky="w", pady=(16, 0)
        )

        tk.Frame(self, bg=LINE, height=1).pack(fill="x")
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x")
        self.status = tk.StringVar(value="Добавьте MP3 и выберите обложку")
        self.status_label = tk.Label(
            bar,
            textvariable=self.status,
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=860,
        )
        self.status_label.pack(fill="x", padx=24, pady=12)

    def _sleeve_enter(self, _event: tk.Event) -> None:
        self.sleeve.itemconfigure(self.frame_id, outline="#d4d4d4")

    def _sleeve_leave(self, _event: tk.Event) -> None:
        self.sleeve.itemconfigure(self.frame_id, outline=LINE)

    def _wrap_status(self, event: tk.Event) -> None:
        if event.widget is self:
            self.status_label.configure(wraplength=max(200, event.width - 48))

    def _set_status(self, text: str, bad: bool = False) -> None:
        self.status.set(text)
        self.status_label.configure(fg=DANGER if bad else MUTED)

    def _same_path(self, left: str, right: str) -> bool:
        return os.path.normcase(os.path.abspath(left)) == os.path.normcase(
            os.path.abspath(right)
        )

    def _refresh_tracks(self) -> None:
        self.count_label.configure(text=f"{len(self.paths)} {track_word(len(self.paths))}")
        self.tracks.set_entries(row_parts(self.paths), self.selected)

    def _add_paths(self, paths: list[str]) -> None:
        added = 0
        for path in paths:
            if any(self._same_path(path, old) for old in self.paths):
                continue
            self.paths.append(path)
            added += 1
        self._refresh_tracks()
        if added:
            self._set_status(f"Добавлено файлов: {added}")
        else:
            self._set_status("Новых MP3 нет")

    def _add_files(self) -> None:
        picked = filedialog.askopenfilenames(
            parent=self,
            title="Выберите MP3",
            initialdir=self.last_audio_dir,
            filetypes=[("MP3", "*.mp3"), ("Все файлы", "*.*")],
        )
        if not picked:
            return
        if isinstance(picked, str):
            picked = (picked,)
        self.last_audio_dir = os.path.dirname(picked[0])
        self._add_paths(list(picked))

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(
            parent=self,
            title="Папка с MP3",
            initialdir=self.last_audio_dir,
        )
        if not folder:
            return
        self.last_audio_dir = folder
        found: list[str] = []
        try:
            names = sorted(os.listdir(folder), key=str.lower)
        except OSError as exc:
            self._set_status(f"Папка не открылась: {explain(exc)}", bad=True)
            return
        for name in names:
            if not name.lower().endswith(".mp3"):
                continue
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                found.append(path)
        if not found:
            self._set_status("В этой папке нет MP3")
            return
        self._add_paths(found)

    def _click_row(self, index: int, event: tk.Event) -> None:
        shift = bool(event.state & 0x0001)
        ctrl = bool(event.state & 0x0004)
        if shift and self.anchor is not None:
            start, end = sorted((self.anchor, index))
            self.selected = set(range(start, end + 1))
        elif ctrl:
            if index in self.selected:
                self.selected.discard(index)
            else:
                self.selected.add(index)
            self.anchor = index
        else:
            self.selected = {index}
            self.anchor = index
        self.tracks.paint(self.selected)
        self._preview_selection()
        self._load_fields()

    def _typing(self) -> bool:
        return isinstance(self.focus_get(), tk.Entry)

    def _move(self, delta: int) -> str:
        if self._typing():
            return "break"
        if not self.paths:
            return "break"
        if self.anchor is None:
            target = 0 if delta > 0 else len(self.paths) - 1
        else:
            target = min(max(self.anchor + delta, 0), len(self.paths) - 1)
        self.selected = {target}
        self.anchor = target
        self.tracks.paint(self.selected)
        self.tracks.reveal(target)
        self._preview_selection()
        self._load_fields()
        return "break"

    def _remove_selected(self, event: tk.Event | None = None) -> str:
        if event is not None and self._typing():
            return "break"
        if not self.selected:
            self._set_status("Выберите треки в списке")
            return "break"
        removed = len(self.selected)
        for index in sorted(self.selected, reverse=True):
            del self.paths[index]
        self.selected.clear()
        self.anchor = None
        self._refresh_tracks()
        self._set_status(f"Убрано из списка: {removed}")
        self._preview_selection()
        self._load_fields()
        return "break"

    def _load_fields(self) -> None:
        paths = self._selected_paths()
        if not paths:
            for key, field in self.fields.items():
                field.set("")
                field.set_mixed(False)
                self.mixed[key] = False
            return
        found: list[dict[str, str]] = []
        for path in paths:
            try:
                found.append(read_info(path))
            except Exception as exc:
                self._set_status(f"{os.path.basename(path)}: {explain(exc)}", bad=True)
        if not found:
            return
        for key, field in self.fields.items():
            values = {item[key] for item in found}
            mixed = len(values) > 1
            self.mixed[key] = mixed
            field.set_mixed(mixed)
            field.set("" if mixed else next(iter(values)))

    def _write_info(self) -> None:
        paths = self._selected_paths()
        if not paths:
            self._set_status("Выберите треки в списке")
            return
        values: dict[str, str] = {}
        for key, field in self.fields.items():
            text = field.get()
            if self.mixed[key] and not text:
                continue
            values[key] = text
        if not values:
            self._set_status("Пустое поле не меняет разные значения")
            return
        done = 0
        errors: list[str] = []
        total = len(paths)
        for index, path in enumerate(paths, start=1):
            name = os.path.basename(path)
            self._set_status(f"{index} из {total}: {name}")
            self.update_idletasks()
            try:
                write_info(path, values)
                done += 1
            except Exception as exc:
                errors.append(f"{name}: {explain(exc)}")
        summary = f"Сведения записаны: {done} из {total}"
        if errors:
            shown = errors[:3]
            if len(errors) > 3:
                shown.append(f"и ещё {len(errors) - 3}")
            summary += "  Ошибки: " + "; ".join(shown)
        self._set_status(summary, bad=bool(errors))
        self._load_fields()

    def _selected_paths(self) -> list[str]:
        return [self.paths[index] for index in sorted(self.selected) if index < len(self.paths)]

    def _set_view_caption(self, caption: str) -> None:
        text = caption.strip()
        if not text:
            self.view_caption.set("")
            self.view_label.grid_remove()
            self.chosen_label.grid_configure(pady=(12, 0))
            return
        self.view_caption.set(text)
        self.view_label.grid()
        self.chosen_label.grid_configure(pady=(4, 0))

    def _show_preview(self, data: bytes | None, caption: str) -> None:
        self._set_view_caption(caption)
        if not data:
            if self.image_item is not None:
                self.sleeve.itemconfigure(self.image_item, state="hidden")
            self.sleeve.itemconfigure(self.empty_id, state="normal")
            return
        try:
            with Image.open(io.BytesIO(data)) as image:
                image = image.convert("RGBA")
                flat = Image.new("RGB", image.size, (255, 255, 255))
                flat.paste(image, mask=image.getchannel("A"))
                flat.thumbnail((COVER - 2, COVER - 2), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(flat)
        except Exception:
            if self.image_item is not None:
                self.sleeve.itemconfigure(self.image_item, state="hidden")
            self.sleeve.itemconfigure(self.empty_id, state="normal", text="Не удалось показать")
            return
        self.sleeve.itemconfigure(self.empty_id, state="hidden", text="Нет обложки")
        if self.image_item is None:
            self.image_item = self.sleeve.create_image(COVER // 2, COVER // 2, image=photo)
        else:
            self.sleeve.itemconfigure(self.image_item, image=photo, state="normal")
        self.preview_photo = photo
        self.sleeve.tag_raise(self.frame_id)

    def _preview_selection(self) -> None:
        if not self.selected:
            if self.cover_jpeg is not None:
                self._show_preview(self.cover_jpeg, "Новая обложка")
            else:
                self._show_preview(None, " ")
            return
        path = self.paths[min(self.selected)]
        name = os.path.basename(path)
        try:
            data = read_cover(path)
        except Exception as exc:
            self._show_preview(None, name)
            self._set_status(f"{name}: {explain(exc)}", bad=True)
            return
        if data:
            self._show_preview(data, "Сейчас в файле")
        else:
            self._show_preview(None, "В файле нет обложки")

    def _choose_cover(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Выберите обложку",
            initialdir=self.last_image_dir,
            filetypes=[
                ("Картинки", "*.jpg;*.jpeg;*.png;*.webp;*.bmp;*.gif"),
                ("Все файлы", "*.*"),
            ],
        )
        if not path:
            return
        self.last_image_dir = os.path.dirname(path)
        try:
            jpeg = cover_to_jpeg(path)
        except Exception as exc:
            self._set_status(f"Не удалось открыть картинку: {explain(exc)}", bad=True)
            return
        self.cover_jpeg = jpeg
        name = os.path.basename(path)
        self.chosen_caption.set(f"К записи · {name}")
        self._show_preview(jpeg, "Новая обложка")
        self._set_status(f"Обложка выбрана: {name}")

    def _write_selected(self) -> None:
        self._apply(self._selected_paths(), "write", empty="Выберите треки в списке")

    def _write_all(self) -> None:
        self._apply(list(self.paths), "write", empty="Список треков пуст")

    def _remove_covers(self) -> None:
        self._apply(self._selected_paths(), "remove", empty="Выберите треки в списке")

    def _apply(self, paths: list[str], action: str, empty: str) -> None:
        if not paths:
            self._set_status(empty)
            return
        if action == "write" and not self.cover_jpeg:
            self._set_status("Сначала выберите обложку")
            return
        done = 0
        errors: list[str] = []
        total = len(paths)
        for index, path in enumerate(paths, start=1):
            name = os.path.basename(path)
            self._set_status(f"{index} из {total}: {name}")
            self.update_idletasks()
            try:
                if action == "write":
                    write_cover(path, self.cover_jpeg or b"")
                else:
                    remove_cover(path)
                done += 1
            except Exception as exc:
                errors.append(f"{name}: {explain(exc)}")
        if action == "write":
            summary = f"Записано: {done} из {total}"
        else:
            summary = f"Обложка убрана: {done} из {total}"
        if errors:
            shown = errors[:3]
            if len(errors) > 3:
                shown.append(f"и ещё {len(errors) - 3}")
            summary += "  Ошибки: " + "; ".join(shown)
        self._set_status(summary, bad=bool(errors))
        self._preview_selection()


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
