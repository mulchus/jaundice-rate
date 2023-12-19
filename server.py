import json
import asyncio
import ndjson
import aiohttp
import pytest


from aiohttp import web
from adapters.inosmi_ru import sanitize, ArticleNotFound
from async_timeout import timeout
from time import monotonic
from contextlib import contextmanager
from text_tools import calculate_jaundice_rate, split_by_words, pymorphy2


pytest_plugins = ('pytest_asyncio',)


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def process_article(session, parsing_duration, morph, charged_words, url):
    @contextmanager
    def counter():
        nonlocal current_time
        yield
        current_time = monotonic()

    parsing_status = 'Ok'
    time_delta, jaundice_rate, words = 0.0, 0, []
    try:
        async with timeout(parsing_duration):
            html = await fetch(session, url)
            start_time = current_time = monotonic()
            with counter():
                clean_plaintext = sanitize(html, plaintext=True)
                words = await split_by_words(morph, clean_plaintext)
                jaundice_rate = calculate_jaundice_rate(words, charged_words)
            time_delta = current_time - start_time  # здесь current_time = значению уже после выполнения блока под with
            await asyncio.sleep(0.1)  # это чек-поинт окончания блока для asyncio.timeout(!=0)
    except (aiohttp.client_exceptions.ClientResponseError, aiohttp.client_exceptions.InvalidURL):
        parsing_status = 'WRONG URL!'
    except ArticleNotFound:
        parsing_status = 'PARSING_ERROR'
    except TimeoutError:
        parsing_status = 'TIMEOUT'
    finally:
        article_result = {
            'status': parsing_status,
            'url': url,
            'score': 'null',
            'words_count': 'null',
        }
        if time_delta:
            article_result['score'] = jaundice_rate
            article_result['words_count'] = len(words)
    return article_result


async def handle(request, morph, charged_words):
    async with aiohttp.ClientSession() as session:
        parsing_result = []
        parsing_duration = 10
        urls = dict(request.query)['urls'].split(",")
        if urls.__len__() > 10:
            raise web.HTTPBadRequest(reason='{"error": "too many urls in request, should be 10 or less"}')
        for url in urls:
            parsing_result.append(await process_article(session, parsing_duration, morph, charged_words, url))
        return web.json_response(json.loads(str(parsing_result).replace("'", '"')), dumps=ndjson.dumps)


async def server(charged_words):
    morph = pymorphy2.MorphAnalyzer()
    app = web.Application()
    app.add_routes([web.get('/', lambda request: handle(request, morph, charged_words))])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 80)
    await site.start()
    while True:
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_process_article():
    morph = pymorphy2.MorphAnalyzer()
    with open('negative_words.txt', encoding="utf-8") as file:
        charged_words = [word.replace('\n', '') for word in file.readlines()]
    
    async def call_process_article(parsing_duration, url):
        async with aiohttp.ClientSession() as session:
            return await process_article(session, parsing_duration, morph, charged_words, url)
    
    assert (await call_process_article(10, 'https://inosmi.ru/20231212/diplomatiya-267037596.html'))['status'] == 'Ok'

    assert (await call_process_article(10,
                                       'https://inosmi.ru/20231212/ssha-267035917.html--'))['status'] == 'WRONG URL!'

    assert (await call_process_article(10,
                                       'https://dvmn.org/filer/canonical/1561832205/162/'))['status'] == 'PARSING_ERROR'

    assert (await call_process_article(.10,
                                       'https://inosmi.ru/20231212/diplomatiya-267037596.html'))['status'] == 'TIMEOUT'
