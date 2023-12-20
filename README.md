# Фильтр желтушных новостей

Проект предназначен для определения желтушности новости путем анализа наличия в тексте ключевых слов и их количества относительно размера статьи.

Пока поддерживается только один новостной сайт - [ИНОСМИ.РУ](https://inosmi.ru/).
Для него разработан специальный адаптер, умеющий выделять текст статьи на фоне остальной HTML разметки.

Для других новостных сайтов потребуются новые адаптеры, все они будут находиться в каталоге `adapters`.
Туда же помещен код для сайта ИНОСМИ.РУ: `adapters/inosmi_ru.py`.

В перспективе можно создать универсальный адаптер, подходящий для всех сайтов, но его разработка будет сложной и потребует дополнительных времени и сил.


## Установка

[Установите Python](https://www.python.org/), если этого ещё не сделали.

Проверьте, что `python` установлен и корректно настроен.
Запустите его в командной строке:
```sh
python --version
```

Скачайте код командой
```shell
git clone https://github.com/mulchus/jaundice-rate.git
```

В каталоге проекта создайте виртуальное окружение:
```sh
python -m venv venv
```

Активируйте его. На разных операционных системах это делается разными командами:
- Windows: `.\venv\Scripts\activate`
- MacOS/Linux: `source venv/bin/activate`

Установите зависимости командой
```shell
pip install -r requirements.txt
```

При работе с Python 3.11 возможно возникновение [ошибки](https://ru.stackoverflow.com/questions/1479188/Почему-не-работает-пакет-pymorphy2-на-python-3-11), исправить которую можно как [здесь](https://github.com/pymorphy2/pymorphy2/pull/161/commits/66c4649e00419ad71b8af441ed56edd1a9ad8e1a)


## Настройки

Настроки могут браться как из отдельного файла, так и из аргументов командной строки при запуске скрипта (вторые имеют больший приоритет).
Чтобы их определить, создайте файл `.env` в корне проекта и запишите туда данные в таком формате `ПЕРЕМЕННАЯ=значение`:

- `HOST` - хост сервера, по умолчанию `127.0.0.1`
- `PORT` - порт на хосте подключаемого сервера для чтения переписки, по умолчанию `80`
- `DURATION` - продолжительность максимального ожидания парсинга, по умолчанию `10 сек`
- `FILENAME` - относительный путь к файлу плохих слов, включая имя файла, по умолчанию `negative_words.txt`

или аналогичные переменные в командной строке (высокий приоритет):
- --host [HOST]
- --port [PORT]
- --duration [DURATION]
- --filename [FILENAME]


## Запуск

Запустите скрипт командой
```shell
python main.py [настройки командной строки]
```
например:
```shell
python3 main.py --duration .1 --port 8080 --filename yellow/1.txt
```

Введите в браузер ссылки на статьи, например:
```shell
http://127.0.0.1:8080/?urls=https://inosmi.ru/20231212/zelenskiy--267038091.html,https://ya.ru,https://google.com,post?sasdf,87897
```
Результат выполнения в браузере
```shell
{"status": "Ok", "url": "https://inosmi.ru/20231212/zelenskiy--267038091.html", "score": 0.54, "words_count": 1112}
{"status": "PARSING_ERROR", "url": "https://ya.ru", "score": "null", "words_count": "null"}
{"status": "PARSING_ERROR", "url": "https://google.com", "score": "null", "words_count": "null"}
{"status": "WRONG URL!", "url": "post?sasdf", "score": "null", "words_count": "null"}
{"status": "WRONG URL!", "url": "87897", "score": "null", "words_count": "null"}
```


## Как запустить тесты

Для тестирования используется [pytest](https://docs.pytest.org/en/latest/), тестами покрыты фрагменты кода сложные в отладке: сервер, text_tools.py, адаптеры. Команды для запуска тестов:
```
python -m pytest adapters/inosmi_ru.py
```
```
python -m pytest text_tools.py
```
```
python -m pytest server.py
```
Результат выполнения  `python3 -m pytest text_tools.py server.py adapters/inosmi_ru.py`
```
======================================================================== test session starts ========================================================================
platform linux -- Python 3.11.7, pytest-7.4.3, pluggy-1.3.0
rootdir: /mnt/d/Python/jaundice-rate
plugins: asyncio-0.23.2, anyio-4.1.0
asyncio: mode=Mode.STRICT
collected 5 item

text_tools.py ..                                                                                                                                              [ 40%]
server.py .                                                                                                                                                   [ 60%]
adapters/inosmi_ru.py ..                                                                                                                                      [100%]
=================================================================== 5 passed in 3.73s ===============================================================================
```


## Цели проекта

Код написан в учебных целях. Это урок из курса по веб-разработке — [Девман](https://dvmn.org).
