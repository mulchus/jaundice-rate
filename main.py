import aiohttp
import anyio
import asyncio
import logging
import sys
from aiohttp import web
import json
import functools

from adapters.inosmi_ru import sanitize, ArticleNotFound
from text_tools import calculate_jaundice_rate, split_by_words, pymorphy2
from async_timeout import timeout
from time import monotonic
from contextlib import contextmanager


TEST_ARTICLES = [
    # 'https://inosmi.ru/20231212/diplomatiya-267037596.html',
    # 'https://inosmi.ru/20231212/zelenskiy--267038091.html',
    # 'https://inosmi.ru/20231212/zelenskiy-267038799.html',
    # 'https://inosmi.ru/20231212/ssha-267035917.html',
    # 'https://lenta.ru/brief/2021/08/26/afg_terror/',
    # 'https://inosmi.ru/20231212/ssha-267035917.html--',
    # 'https://dvmn.org/filer/canonical/1561832205/162/',
]


time_logger = logging.getLogger()
charged_words = []
morph = pymorphy2.MorphAnalyzer()


def configuring_logging():
    time_logger.setLevel(logging.INFO)
    logger_handler = logging.StreamHandler(sys.stdout)
    logger_formatter = logging.Formatter(
        '%(levelname)s:%(name)s:%(message)s',
        datefmt='%d-%m-%Y %H:%M:%S'
    )
    logger_handler.setFormatter(logger_formatter)
    time_logger.addHandler(logger_handler)
    

async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def process_article(session, url):
    @contextmanager
    def counter():
        nonlocal current_time
        yield
        current_time = monotonic()

    parsing_status = 'Ok'
    time_delta, jaundice_rate, words = 0.0, 0, []
    try:
        async with timeout(10):
            html = await fetch(session, url)
            start_time = current_time = monotonic()
            with counter():
                clean_plaintext = sanitize(html, plaintext=True)
                words = await split_by_words(morph, clean_plaintext)
                jaundice_rate = calculate_jaundice_rate(words, charged_words)
            time_delta = current_time - start_time  # здесь current_time = значению уже после выполнения блока под with
            await asyncio.sleep(0.1)  # это чек-поинт окончания блока для asyncio.timeout(!=0)
    except aiohttp.client_exceptions.ClientResponseError:
        parsing_status = 'WRONG URL!'
    except ArticleNotFound:
        parsing_status = 'PARSING_ERROR'
    except TimeoutError:
        parsing_status = 'TIMEOUT'
    finally:
        article_result = {
            'status': parsing_status,
            'url': url,
            'score': None,
            'words_count': None,
        }
        if time_delta:
            article_result['score'] = jaundice_rate
            article_result['words_count'] = len(words)
    return article_result


async def handle(request):
    parsing_result = []
    urls = dict(request.query)['urls'].split(",")
    for url in urls:
        async with aiohttp.ClientSession() as session:
            parsing_result.append(await process_article(session, url))
    parsing_result = str(parsing_result).replace("'", '"')
    print(parsing_result)
    # return web.Response(text=parsing_result)
    return web.json_response(json.loads(parsing_result), dumps=functools.partial(json.dumps, indent=2))
    # return web.Response(text=str(parsing_result))


async def server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 80)
    await site.start()
    while True:
        await asyncio.sleep(0)


async def main():
    global charged_words
    configuring_logging()
    with open('negative_words.txt', encoding="utf-8") as file:
        charged_words = [word.replace('\n', '') for word in file.readlines()]
        
    # morph = pymorphy2.MorphAnalyzer()
    # with open('negative_words.txt', encoding="utf-8") as file:
    #     charged_words = [word.replace('\n', '') for word in file.readlines()]
    # title = ''
    
    # async with aiohttp.ClientSession() as session:
    # try:
    async with anyio.create_task_group() as task_group:
        task_group.start_soon(server)
            # for url in TEST_ARTICLES:
            #     task_group.start_soon(process_article, session, morph, charged_words, url)  #, title)
                
    # except* Exception as excgroup:
    #     for _ in excgroup.exceptions:
    #         task_group.cancel_scope.cancel()
        

if __name__ == "__main__":
    anyio.run(main)
