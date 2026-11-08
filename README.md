# Sleeve

Программа для Windows. Вписывает обложку и подписи в файлы MP3 и не меняет звук.

A Windows program. It writes a cover and labels into MP3 files and does not change the audio.

## По-русски

Картинка любого формата становится JPEG: длинная сторона не больше 1400 пикселей, качество 90. В файле остаётся одна передняя обложка в теге ID3v2.3, его читают Проводник и обычные плееры. Отдельно записываются название, исполнитель и альбом.

### Чего Sleeve не делает

- Не перекодирует и не обрезает звук.
- Работает только с MP3. FLAC и M4A не открывает.
- Папка добавляется без вложенных папок.

### Запуск

Нужны Windows и Python 3.10 или новее. В папке программы:

```
py -m pip install -r requirements.txt
```

Дальше дважды щёлкните `Запуск.bat` или выполните `py app.py`.

### Как пользоваться

В шапке RU и EN переключают язык окна. Выбор запоминается.

1. Добавьте файлы или папку.
2. Выберите треки в списке. У нескольких треков поле с разными значениями показывает «· разные».
3. Впишите название, исполнителя и альбом и нажмите «Записать сведения». В полях работают Ctrl+C, Ctrl+V и меню по правому щелчку, в том числе при русской раскладке. Пустое поле у нескольких треков не меняет этот тег. Если выбран один трек и поле очищено, тег удаляется.
4. Щёлкните по квадрату обложки, выберите картинку и нажмите «Вписать в выбранные» или «Вписать во все».

«Убрать из списка» и клавиша Delete убирают строки из списка, файл на диске остаётся. Пока курсор в поле ввода, Delete и стрелки список не трогают.

## In English

Any picture becomes a JPEG: the long side is at most 1400 pixels, at quality 90. The file keeps one front cover in an ID3v2.3 tag, which File Explorer and ordinary players can read. Title, artist, and album are saved separately.

### What Sleeve does not do

- It does not re-encode or cut the audio.
- It only opens MP3 files. It does not open FLAC or M4A.
- Adding a folder does not include folders inside it.

### Run

You need Windows and Python 3.10 or newer. In the program folder:

```
py -m pip install -r requirements.txt
```

Then double-click `Запуск.bat`, or run `py app.py`.

### How to use

RU and EN in the header switch the language of the window. The choice is remembered.

1. Add files or a folder.
2. Select tracks in the list. When the selected tracks differ, a field shows "· mixed".
3. Type the title, artist, and album, then press "Save details". The fields accept Ctrl+C and Ctrl+V, and a right-click menu, including with a Russian keyboard layout. An empty field leaves a mixed value unchanged. If one track is selected and a field is cleared, that tag is removed.
4. Click the cover square, choose a picture, and press "Write to selected" or "Write to all".

"Remove from list" and the Delete key remove rows from the list. The file on disk stays. While the cursor is in a text field, Delete and the arrow keys leave the list alone.
