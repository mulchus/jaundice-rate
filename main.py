import aiohttp
import anyio
import asyncio

from adapters.inosmi_ru import sanitize, ArticleNotFound
from text_tools import calculate_jaundice_rate, split_by_words, pymorphy2
from async_timeout import timeout


TEST_ARTICLES = [
    'https://inosmi.ru/20231212/diplomatiya-267037596.html',
    'https://inosmi.ru/20231212/zelenskiy--267038091.html',
    'https://inosmi.ru/20231212/zelenskiy-267038799.html',
    'https://inosmi.ru/20231212/ssha-267035917.html',
    'https://lenta.ru/brief/2021/08/26/afg_terror/',
    'https://inosmi.ru/20231212/ssha-267035917.html--',
]


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def process_article(session, morph, charged_words, url, title, results):
    parsing_status = ''
    jaundice_rate, len_words = None, None
    try:
        async with timeout(.7):
            html = await fetch(session, url)
            clean_plaintext = sanitize(html, plaintext=True)
            words = split_by_words(morph, clean_plaintext)
            len_words = len(words)
            jaundice_rate = calculate_jaundice_rate(words, charged_words)
            parsing_status = 'Ok'
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
        results.append(
            f'URL: {url}\n'
            f'Статус: {parsing_status}\n'
            f'Рейтинг: {jaundice_rate}\n'
            f'Слов в статье: {len_words}\n'
        )


async def main():
    morph = pymorphy2.MorphAnalyzer()
    with open('negative_words.txt', encoding="utf-8") as file:
        charged_words = [word.replace('\n', '') for word in file.readlines()]
    title = ''
    results = []
    async with aiohttp.ClientSession() as session:
        # try:
        async with anyio.create_task_group() as task_group:
            for url in TEST_ARTICLES:
                task_group.start_soon(process_article, session, morph, charged_words, url, title, results)
        # except* Exception as excgroup:
        #     for _ in excgroup.exceptions:
        #         task_group.cancel_scope.cancel()

    for result in results:
        print(result)


if __name__ == "__main__":
    anyio.run(main)
