import aiohttp
import anyio

from adapters.inosmi_ru import sanitize
from text_tools import calculate_jaundice_rate, split_by_words, pymorphy2


TEST_ARTICLES = [
    'https://inosmi.ru/20231212/diplomatiya-267037596.html',
    'https://inosmi.ru/20231212/zelenskiy--267038091.html',
    'https://inosmi.ru/20231212/zelenskiy-267038799.html',
    'https://inosmi.ru/20231212/ssha-267035917.html',
    'https://inosmi.ru/20231212/farerskie_ostrova-267035597.html',
]


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def process_article(session, morph, charged_words, url, title):
    html = await fetch(session, url)
    clean_plaintext = sanitize(html, plaintext=True)
    words = split_by_words(morph, clean_plaintext)
    jaundice_rate = calculate_jaundice_rate(words, charged_words)
    print(
        f'URL: {url}\n'
        f'Рейтинг: {jaundice_rate}\n'
        f'Слов в статье: {len(words)}\n'
    )


async def main():
    morph = pymorphy2.MorphAnalyzer()
    with open('negative_words.txt', encoding="utf-8") as file:
        charged_words = [word.replace('\n', '') for word in file.readlines()]
    title = ''
    async with aiohttp.ClientSession() as session:
        try:
            async with anyio.create_task_group() as task_group:
                for url in TEST_ARTICLES:
                    task_group.start_soon(process_article, session, morph, charged_words, url, title)
        except* (BaseException, SystemExit) as excgroup:
            for _ in excgroup.exceptions:
                task_group.cancel_scope.cancel()


if __name__ == "__main__":
    anyio.run(main)
