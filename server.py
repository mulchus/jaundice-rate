import json
import asyncio
import ndjson
import aiohttp
import pytest
import logging

from aiohttp import web
from adapters.inosmi_ru import sanitize, ArticleNotFound
from async_timeout import timeout
from time import monotonic
from contextlib import contextmanager
from text_tools import calculate_jaundice_rate, split_by_words, pymorphy2


pytest_plugins = ('pytest_asyncio',)

parsing_logger = logging.getLogger('parsing_logger')


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


@contextmanager
def register_time_delta():
    start_time = monotonic()
    yield
    parsing_logger.info(f' Анализ закончен за {monotonic() - start_time} сек,')


async def process_article(session, parsing_duration, morph, charged_words, url):
    parsing_status = 'Ok'
    try:
        with register_time_delta():
            async with timeout(parsing_duration):
                html = await fetch(session, url)
                clean_plaintext = sanitize(html, plaintext=True)
                words = await split_by_words(morph, clean_plaintext)
                jaundice_rate = calculate_jaundice_rate(words, charged_words)
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
        if parsing_status == 'Ok':
            article_result['score'] = jaundice_rate
            article_result['words_count'] = len(words)
            parsing_logger.info(article_result)
        else:
            parsing_logger.error(article_result)
    return article_result


async def handle(request, morph, charged_words, duration):
    async with aiohttp.ClientSession() as session:
        parsing_result = []
        urls = dict(request.query)['urls'].split(",")
        if urls.__len__() > 10:
            raise web.HTTPBadRequest(reason='{"error": "too many urls in request, should be 10 or less"}')
        for url in urls:
            parsing_result.append(await process_article(session, duration, morph, charged_words, url))
        return web.json_response(json.loads(str(parsing_result).replace("'", '"')), dumps=ndjson.dumps)


async def server(charged_words, host, port, duration):
    morph = pymorphy2.MorphAnalyzer()
    app = web.Application()
    app.add_routes([web.get('/', lambda request: handle(request, morph, charged_words, duration))])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
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
