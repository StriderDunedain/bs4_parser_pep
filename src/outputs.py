import csv
import datetime as dt
import logging

from prettytable import PrettyTable

from constants import BASE_DIR, DATETIME_FORMAT


def file_output(results, cli_args):
    """Creates a file using data from main.py."""
    results_dir = BASE_DIR / 'results'
    results_dir.mkdir(exist_ok=True)

    parser_mode = cli_args.mode
    now = dt.datetime.now()
    formatted_time = now.strftime(DATETIME_FORMAT)

    file_name = f'{parser_mode}_{formatted_time}.csv'
    file_path = results_dir / file_name

    with open(file_path, 'w', encoding='utf-8') as file:
        writer = csv.writer(file, dialect='unix')

        status = results[0]
        counts = results[1]
        for i in range(len(status)):
            row = status[i], counts[i]
            writer.writerow(row)

    logging.info(f'Файл с результатами был сохранён: {file_path}')


def control_output(results, cli_args):
    """Determines data representation: terminal table / csv file"""
    output = cli_args.output
    if output == 'pretty':
        pretty_output(results)
    elif output == 'file':
        file_output(results, cli_args)
    else:
        default_output(results)


def default_output(results):
    """Prints to terminal `as is`"""
    # Печатаем список results построчно.
    for row in results:
        print(*row)


def pretty_output(results):
    """Creates a table using data from main.py."""
    # Инициализируем объект PrettyTable.
    table = PrettyTable()
    # В качестве заголовков устанавливаем первый элемент списка.
    table.field_names = results[0]
    # Добавляем все строки, начиная со второй (с индексом 1).
    table.add_rows(results[1:])
    # Печатаем таблицу.
    print(table)
