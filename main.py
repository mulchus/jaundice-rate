import anyio
import logging
import sys
import functools
import server
import argparse

from environs import Env
from pathlib import Path

# ссылки на статьи для проверок
# 'https://inosmi.ru/20231212/diplomatiya-267037596.html',
# 'https://inosmi.ru/20231212/zelenskiy--267038091.html',
# 'https://inosmi.ru/20231212/zelenskiy-267038799.html',
# 'https://inosmi.ru/20231212/ssha-267035917.html',
# 'https://lenta.ru/brief/2021/08/26/afg_terror/',
# 'https://inosmi.ru/20231212/ssha-267035917.html--',
# 'https://dvmn.org/filer/canonical/1561832205/162/',


time_logger = logging.getLogger()


def configuring_logging():
    time_logger.setLevel(logging.INFO)
    logger_handler = logging.StreamHandler(sys.stdout)
    logger_formatter = logging.Formatter(
        '%(levelname)s:%(name)s:%(message)s',
        datefmt='%d-%m-%Y %H:%M:%S'
    )
    logger_handler.setFormatter(logger_formatter)
    time_logger.addHandler(logger_handler)


def get_args(environ):
    parser = argparse.ArgumentParser(description='Скрипт проверки статей сайтов на желтушность')
    parser.add_argument(
        '--host',
        nargs='?',
        type=str,
        help='хост сервера'
    )
    parser.add_argument(
        '--port',
        nargs='?',
        type=int,
        help='порт сервера'
    )
    parser.add_argument(
        '--duration',
        nargs='?',
        type=float,
        help='продолжительность максимального ожидания парсинга'
    )
    parser.add_argument(
        '--filename',
        nargs='?',
        type=str,
        help='относительный путь к файлу плохих слов'
    )

    host = parser.parse_args().host if parser.parse_args().host else environ('HOST', '127.0.0.1')
    port = parser.parse_args().port if parser.parse_args().port else int(environ('PORT', 80))
    duration = parser.parse_args().duration if parser.parse_args().duration else int(environ('DURATION', 10))
    filename = parser.parse_args().filename if parser.parse_args().filename else environ('FILENAME',
                                                                                         'negative_words.txt')
    return host, port, duration, filename


async def main():
    configuring_logging()
    
    host, port, duration, filename = get_args(env)
    
    filepath = Path.joinpath(Path.cwd(), filename)
    if not Path.is_file(filepath):
        time_logger.error(' Не найден файл плохих слов. Проверьте путь и имя файла.')
        exit()
    
    with open(filepath, encoding="utf-8") as file:
        charged_words = [word.replace('\n', '') for word in file.readlines()]

        try:
            async with anyio.create_task_group() as task_group:
                task_group.start_soon(functools.partial(server.server, charged_words, host, port, duration))

        except* Exception as excgroup:
            for _ in excgroup.exceptions:
                task_group.cancel_scope.cancel()


if __name__ == "__main__":
    env = Env()
    env.read_env()
    anyio.run(main)
