from aiohttp import web
import json
import functools


async def handle(request):
    serialized_urls = '{}'
    for key, value in dict(request.query).items():
        serialized_urls = f'{{"{key}": {value.split(",")}}}'.replace("'", '"')
    return web.json_response(json.loads(serialized_urls), dumps=functools.partial(json.dumps, indent=2))


app = web.Application()
app.add_routes([web.get('/', handle),
                web.get('/{name}', handle)])


if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=80)
