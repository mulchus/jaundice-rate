import json
import asyncio
import ndjson
import aiohttp

from aiohttp import web
from adapters.inosmi_ru import sanitize, ArticleNotFound
from async_timeout import timeout
from time import monotonic
from contextlib import contextmanager
from text_tools import calculate_jaundice_rate, split_by_words, pymorphy2


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def process_article(session, morph, charged_words, url):
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
        urls = dict(request.query)['urls'].split(",")
        if urls.__len__() > 10:
            raise web.HTTPBadRequest(reason='{"error": "too many urls in request, should be 10 or less"}')
        for url in urls:
            parsing_result.append(await process_article(session, morph, charged_words, url))
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
