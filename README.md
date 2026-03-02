# URL Auto Opener

PyQt6-приложение для работы с группами сайтов, категориями и `path`, ориентированное на быстрые переходы и проверки ссылок при поддержке MODX-проектов.

## Возможности

- список сайтов с категориями
- поиск и фильтрация по категориям
- индивидуальные `Path` для каждого сайта
- общие `Path` для всей категории
- импорт и экспорт JSON-базы
- проверка HTTP-статусов для `Path`
- сборка в `.exe`

## Требования

- Windows
- Python 3.13+

## Установка

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Запуск

```powershell
python main.py
```

## Сборка `.exe`

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

После сборки:

- основной `.exe` будет в `dist\url-auto-opener.exe`
- готовая релизная папка будет в `release\url-auto-opener\`

## Перенос на другой ПК

Через git:

```powershell
git clone https://github.com/MRcrecs/a-little-new.git
cd a-little-new
git checkout stable
```

Если нужна локальная база сайтов, перенеси отдельно файл `sites.json`.

## JSON

Приложение сохраняет данные в `sites.json`.

Структура:

```json
{
  "sites": [
    {
      "name": "Example",
      "category": "MODX Revo",
      "base_url": "https://example.com/",
      "manager_url": "https://example.com/manager/",
      "paths": [
        "catalog",
        "contacts"
      ]
    }
  ],
  "common_paths": [
    "robots.txt",
    "sitemap.xml"
  ]
}
```
