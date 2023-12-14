import aiohttp
import anyio
import asyncio
import logging
import time
import sys

from adapters.inosmi_ru import sanitize, ArticleNotFound
from text_tools import calculate_jaundice_rate, split_by_words, pymorphy2
from async_timeout import timeout
from time import monotonic
from contextlib import contextmanager


TEST_ARTICLES = [
    'https://inosmi.ru/20231212/diplomatiya-267037596.html',
    'https://inosmi.ru/20231212/zelenskiy--267038091.html',
    'https://inosmi.ru/20231212/zelenskiy-267038799.html',
    'https://inosmi.ru/20231212/ssha-267035917.html',
    'https://lenta.ru/brief/2021/08/26/afg_terror/',
    'https://inosmi.ru/20231212/ssha-267035917.html--',
    'https://dvmn.org/filer/canonical/1561832205/162/',
]


time_logger = logging.getLogger()


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


# @contextmanager
# def counter(*args, **kwds):
#     # Code to acquire resource, e.g.:
#     start_time = monotonic()
#     # resource = acquire_resource(*args, **kwds)
#     try:
#         yield start_time
#     finally:
#         # Code to release resource, e.g.:
#         return monotonic() - start_time
#         # release_resource(resource)


class Timer:
    def __int__(self):
        self.elapsed_time = None
        return self

    def __enter__(self):
        self.start_time = monotonic()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed_time = monotonic() - self.start_time
        return self


async def process_article(session, morph, charged_words, url, title):
    parsing_status = ''
    time_delta = 0
    jaundice_rate, len_words = None, None
    try:
        async with timeout(10):
            html = await fetch(session, url)
            with Timer() as timer:
                clean_plaintext = sanitize(html, plaintext=True)
                words = split_by_words(morph, clean_plaintext)
                jaundice_rate = calculate_jaundice_rate(words, charged_words)
                len_words = len(words)
                parsing_status = 'Ok'
            time_delta = timer.elapsed_time
    except aiohttp.client_exceptions.ClientResponseError:
        parsing_status = 'WRONG URL!'
        return
    except ArticleNotFound:
        parsing_status = 'PARSING_ERROR'
        return
    except asyncio.TimeoutError:
        parsing_status = 'TIMEOUT'
        return
    finally:
        print(
            f'URL: {url}\n'
            f'Статус: {parsing_status}\n'
            f'Рейтинг: {jaundice_rate}\n'
            f'Слов в статье: {len_words}'
        )
        time_logger.info(f'Анализ закончен за {round(time_delta, 3)} сек'),
        print()


def configuring_logging():
    time_logger.setLevel(logging.INFO)
    logger_handler = logging.StreamHandler(sys.stdout)
    logger_formatter = logging.Formatter(
        '%(levelname)s:%(name)s:%(message)s',
        datefmt='%d-%m-%Y %H:%M:%S'
    )
    logger_handler.setFormatter(logger_formatter)
    time_logger.addHandler(logger_handler)


async def main():
    configuring_logging()
    morph = pymorphy2.MorphAnalyzer()
    with open('negative_words.txt', encoding="utf-8") as file:
        charged_words = [word.replace('\n', '') for word in file.readlines()]
    title = ''
    async with aiohttp.ClientSession() as session:
        try:
            async with anyio.create_task_group() as task_group:
                for url in TEST_ARTICLES:
                    task_group.start_soon(process_article, session, morph, charged_words, url, title)
        except* Exception as excgroup:
            for _ in excgroup.exceptions:
                task_group.cancel_scope.cancel()


if __name__ == "__main__":
    anyio.run(main)
