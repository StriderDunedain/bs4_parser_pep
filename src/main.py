from collections import Counter
import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from requests_cache import CachedSession
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import BASE_DIR, MAIN_DOC_URL, PEP_801_STATUS, PEP_DOC_URL
from exceptions import VersionsNotFoundException
from outputs import control_output
from utils import find_tag, get_response


def whats_new(session: CachedSession) -> list:
    """Fresh news of every python version."""
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    if response is None:
        return

    soup = BeautifulSoup(response.text, features='lxml')

    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_url = find_tag(
        main_div, 'div', attrs={'class': 'toctree-wrapper'}
    )
    sections_by_python = div_with_url.find_all(
        'li', attrs={'class': 'toctree-l1'}
    )

    results = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор')]
    for section in tqdm(sections_by_python):
        version_a_tag = find_tag(section, 'a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        response = get_response(session, whats_new_url)
        if response is None:
            continue
        soup = BeautifulSoup(response.text, features='lxml')
        h1 = find_tag(soup, 'h1')
        results.append((version_link, h1.text))

    return results


def latest_versions(session: CachedSession) -> list:
    """Get links to latest docs of python versions."""
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')

    sidebar = find_tag(soup, 'div', attrs={'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')

    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise VersionsNotFoundException('Ничего не нашлось')

    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'

    for a_tag in a_tags:
        link = a_tag['href']
        match = re.search(pattern, a_tag.text)

        if match is not None:
            version, status = match.groups()
        else:
            version, status = a_tag.text, ''

        results.append(
            (link, version, status)
        )

    return results


def download(session: CachedSession) -> None:
    """Download Python Docs as an archive."""
    download_dir = BASE_DIR / 'downloads'
    download_dir.mkdir(exist_ok=True)

    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')

    response = get_response(session, downloads_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')

    version_table = find_tag(soup, 'table', attrs={'class': 'docutils'})
    pdf_a4_tag = find_tag(
        version_table, 'a', {'href': re.compile(r'.+pdf-a4\.zip$')}
    )
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)

    filename = archive_url.split('/')[-1]
    archive_path = download_dir / filename

    response = session.get(archive_url)

    with open(archive_path, 'wb') as file:
        file.write(response.content)

    logging.info(f'Архив был загружен и сохранён: {archive_path}')


def parse_tables(session: CachedSession) -> list:
    """Helper func. Parses all PEPs and returns their link & status."""
    response = get_response(session, PEP_DOC_URL)
    if response is None:
        return

    soup = BeautifulSoup(response.text, features='lxml')
    tables = soup.find_all(
        'table', attrs={'class': 'pep-zero-table docutils align-default'}
    )
    peps = []
    for table in tables:
        # Находим все ряды в таблице...
        tr_tag = table.tbody.find_all('tr')

        for row in tr_tag:
            # Все находится в первых двух <td> тэгах
            td_tag = row.find_all('td')

            link = td_tag[1].a
            pep_link = PEP_DOC_URL + link['href']
            # Там есть особый PEP...
            status = (
                PEP_801_STATUS if link.text == '801'
                else td_tag[0].abbr['title']
            )

            # Статусы часто повторяются
            data = (pep_link, status)
            if data not in peps:
                peps.append(data)
    return peps


def status_normalizer(status: str) -> list:
    """Helper func. Makes a status covenient."""
    commaless = status.split(',')
    return list((commaless[0], commaless[1].strip()))


def check_status(session: CachedSession, peps: list) -> list:
    """Helper func. Checks and correlates PEP status."""
    # Будет оч полезно для следующей ф-ции
    pep_status_list = []
    # Они 100% будут, поэтому сразу отмечаем в логах
    logging.info('Несовпадающие статусы...')

    # Сравниваем код на главной странице с кодом на личной странице PEP`а
    for pep_link, status_main in tqdm(peps):
        # Завариваем супчик...)
        response = get_response(session, pep_link)
        if response is None:
            return

        soup = BeautifulSoup(response.text, features='lxml')

        # Все находится в <dl> тэге...
        dl_tag = soup.find('dl', attrs={'class': 'rfc2822 field-list simple'})
        # В тэге <abbr>...
        abbr_tag = dl_tag.find_all('abbr')

        status = abbr_tag[0].text
        type = abbr_tag[1].text

        pep_status_list.append(status)

        personal_charater = [type, status]
        if personal_charater != status_normalizer(status_main):
            logging.info(
                f'''
                {pep_link}
                Статус в карточке: {personal_charater}
                Ожидаемые статусы: {status_normalizer(status_main)}
                '''
            )
    return pep_status_list


def table_data_counter(pep_status_list: list) -> Counter:
    """
    Helper func. Counts the number of each status
    and prepares data for a table.
    """
    pep_status_dict = Counter(pep_status_list)

    pep_status_dict['TOTAL'] += sum(pep_status_dict.values())

    return pep_status_dict


def pep(session: CachedSession) -> list:
    """PEP parsing func."""
    # Парсим все PEP`ы и возвращаем их
    peps = parse_tables(session)

    # Проверяем статусы и возвращаем их
    pep_status_list = check_status(session, peps)

    # Составляем данные для таблицы
    table_list = table_data_counter(pep_status_list)

    return table_list


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep
}


def main() -> None:
    """Main func."""
    configure_logging()

    logging.info('Парсер запущен!')

    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()

    logging.info(f'Аргументы командной строки: {args}')

    # Создание кеширующей сессии.
    session = CachedSession()
    # Если был передан ключ '--clear-cache', то args.clear_cache == True.
    if args.clear_cache:
        # Очистка кеша.
        session.cache.clear()

    parser_mode = args.mode
    # С вызовом функции передаётся и сессия.
    results = MODE_TO_FUNCTION[parser_mode](session)
    if results is not None:
        # передаём их в функцию вывода вместе с аргументами командной строки.
        control_output(results, args)

    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
