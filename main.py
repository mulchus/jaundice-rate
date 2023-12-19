import anyio
import logging
import sys
import functools
import server


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


async def main():
    configuring_logging()

    with open('negative_words.txt', encoding="utf-8") as file:
        charged_words = [word.replace('\n', '') for word in file.readlines()]

        # try:
        async with anyio.create_task_group() as task_group:
            task_group.start_soon(functools.partial(server.server, charged_words))

        # except* Exception as excgroup:
        #     for _ in excgroup.exceptions:
        #         task_group.cancel_scope.cancel()


if __name__ == "__main__":
    anyio.run(main)
