import datetime, inspect
from pathlib import Path

class Logger:
    """
    Logger v2.2
    """

    NOTSET: int = 0
    DEBUG: int = 10
    INFO: int = 20
    WARNING: int = 30
    WARN: int = 30
    ERROR: int = 40
    CRITICAL: int = 50
    FATAL: int = 50

    def __init__(self, file_log:str='log', time_format:str='%Y.%m.%d %H:%M:%S', date_format:str='%Y.%m.%d', print_format:str='[{time}] [{file}]{(" ["+func+"]")*(func!="None")} [{levl}] | {(title+" | ")*(title!="None")}{msg}', print_levl:int=20, logs_in_dirs:bool=False, file_names_format:str='log {date}', logger_data_file_name:str='logger.data', file_extension:str='log', file_encoding:str='utf-8', write_when_init:bool=True) -> None:
        """
        :param file_log: Название/Путь до файла лога (если его нет, он создастся), При logs_in_dirs == True file_log становится Путём до папки логов, defaults to 'log'
        :type file_log: str
        :param time_format: Формат выводимого времени, defaults to '%Y.%m.%d %H:%M:%S'
        :type time_format: str
        :param date_format: Формат выводимой даты, defaults to '%Y.%m.%d'
        :type date_format: str
        :param print_format: Формат вывода лога, defaults to '[{time}] [{file}]{(" ["+func+"]")*(func!="None")} [{levl}] | {(title+" : ")*(title!="None")}{msg}'
        :type print_format: str
        :param print_levl: С какого уровня начинать выводить Лог используя print, defaults to 10
        :type print_levl: int
        :param logs_in_dirs: При True Логи хранятся в папке file_log, но в разных файлах / при False в файле file_log, defaults to False
        :type logs_in_dirs: bool
        :param file_names_format: При logs_in_dirs == True названия файлов будут создоваться по этому формату, defaults to 'log {date}'
        :type file_names_format: str
        :param logger_data_file_name: Название технического файла
        :type logger_data_file_name: str
        :param file_extension: расширение файлов логов, defaults to 'log'
        :type file_extension: str
        :param file_encoding: Кодирование файлов логов, defaults to 'utf-8'
        :type file_encoding: str
        :param write_when_init: Писать строчку '--new run programm--' в лог при создании объекта Logger?
        :type write_when_init: bool

        print_format:
            {time} - Время формата time_format (2000.07.05 20:01:03)\n
            {date} - Дата формата date_format (1851.03.22)\n
            {levl} - Уровень (DEBUG, WARNING)\n
            {levl_num} - Номер уровня (20, 23, 50)\n
            {file} - Название файла, в котором происходит логирование (main.py, logger.py)\n
            {func} - Название функции, в которой происходит логирование (main, test_function)\n
            {title} - Заголовок лога (auth error, connect error, successful authorization)\n
            {msg} - Текст лога (user 123.123.123.123 connected to the server)\n
            {thread} (не реализовано) - Id текущего потока (2540, 8124)\n

        file_names_format:
            {time} - Время формата time_format (2000.07.05 20:01:03)\n
            {date} - Дата формата date_format (1851.03.22)\n
        """
        self.file_log = file_log
        self.time_format = time_format
        self.date_format = date_format
        self.print_format = print_format
        self.print_levl = print_levl
        self.logs_in_dirs = logs_in_dirs
        self.file_names_format = file_names_format
        self.logger_data_file_name = logger_data_file_name
        self.file_extension = file_extension
        self.file_encoding = file_encoding

        self.count_seconds_in_file = 86400
        self.levl_dict = {10: 'DEBUG   ', 20: 'INFO    ', 30: 'WARNING ', 40: 'ERROR   ', 50: 'CRITICAL'}
        self._opened_log_file = None
        self._logger_data_file = self._open_file(file=self.logger_data_file_name, mode='a+')
        self._logger_data_file.seek(0)
        self._len_file_name = 15
        self._len_func_name = 20
        self._last_file_seconds = int(temp) if (temp:=self._logger_data_file.readline()) else -1

        if write_when_init:
            self._write_to_log_file('\n-------------------new run programm-------------------')

    def _get_full_path_log_file(self, file_name=None):
        if self.file_log and self.logs_in_dirs:
            return f'{self.file_log}\\{file_name}.{self.file_extension}'
        return f'{file_name}.{self.file_extension}'

    def _get_path_log_file(self, file_seconds):
        if not self.logs_in_dirs:
            return self._get_full_path_log_file()
        nowtime = datetime.datetime.fromtimestamp(file_seconds)
        time = nowtime.strftime(self.time_format)
        date = nowtime.strftime(self.date_format)
        name_log_file = self.file_names_format.format(time=time, date=date)
        path_log_file = self._get_full_path_log_file(name_log_file)
        if file_seconds != self._last_file_seconds and Path(path_log_file).exists():
            name_log_file = f'{name_log_file}({file_seconds})'
            path_log_file = self._get_full_path_log_file(name_log_file)
        return path_log_file

    def _get_file_seconds(self):
        nowstemp = int(datetime.datetime.now().timestamp())
        if self.count_seconds_in_file:
            return nowstemp // self.count_seconds_in_file * self.count_seconds_in_file
        return nowstemp // 86400 * 86400

    def _get_log_file(self):
        file_seconds = self._get_file_seconds()
        path_file = self._get_path_log_file(file_seconds)
        if not self.logs_in_dirs:
            if not self._opened_log_file:
                self._opened_log_file = self._open_file(file=path_file, mode='a')
            return self._opened_log_file

        if file_seconds == self._last_file_seconds:
            if self._opened_log_file:
                return self._opened_log_file
            self._opened_log_file = self._open_file(file=path_file, mode='a')
            return self._opened_log_file

        self._last_file_seconds = file_seconds

        self._logger_data_file.truncate(0)
        self._logger_data_file.write(str(self._last_file_seconds))
        self._logger_data_file.flush()

        if self._opened_log_file:
            self._opened_log_file.close()
        self._opened_log_file = self._open_file(file=path_file, mode='a')
        return self._opened_log_file

    def _open_file(self, file, mode):
        path = Path(file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_obj = path.open(mode=mode, encoding=self.file_encoding)
        return file_obj

    def _write_to_log_file(self, text):
        file = self._get_log_file()
        file.write(text + '\n')
        file.flush()

    def stop(self):
        if self._opened_log_file:
            self._opened_log_file.close()
        if self._logger_data_file:
            self._logger_data_file.close()

    def log(self, level: int = 0, msg: str = None, title: str = None, stack_num:int=0):
        nowtime = datetime.datetime.now()
        time = nowtime.strftime(self.time_format)
        date = nowtime.strftime(self.date_format)
        levl_num = level
        levl = self.levl_dict.get(levl_num, 'NOTSET')
        file = inspect.stack()[1+stack_num].filename.split("\\")[-1].ljust(self._len_file_name, ' ')
        func = inspect.stack()[1+stack_num][3]
        if func == '<module>':
            func = 'None'
        else:
            func = func.ljust(self._len_func_name, ' ')

        if not msg:
            msg = 'Not set the text'
        if not title:
            title = 'None'
        end_log_text = eval(f'''f"""{self.print_format}"""''')
        self._write_to_log_file(end_log_text)
        if levl_num >= self.print_levl:
            print(end_log_text)

    def debug(self, msg: str = None, title: str = None, stack_num:int=1):
        self.log(level=self.DEBUG, msg=msg, title=title, stack_num=stack_num)

    def info(self, msg: str = None, title: str = None, stack_num:int=1):
        self.log(level=self.INFO, msg=msg, title=title, stack_num=stack_num)

    def warning(self, msg: str = None, title: str = None, stack_num:int=1):
        self.log(level=self.WARNING, msg=msg, title=title, stack_num=stack_num)

    def error(self, msg: str = None, title: str = None, stack_num:int=1):
        self.log(level=self.ERROR, msg=msg, title=title, stack_num=stack_num)

    def critical(self, msg: str = None, title: str = None, stack_num:int=1):
        self.log(level=self.CRITICAL, msg=msg, title=title, stack_num=stack_num)

    warn = warning
    fatal = critical

Log = Logger(file_log='logs', logs_in_dirs=True, logger_data_file_name='logs\\logger.data')

if __name__ == "__main__":
    Log.log(Log.ERROR, 'Какая-то там ошибка', 'Переменная такая-та не найдена')
    Log.log(Log.INFO, 'Администратор вошел в чат')
    Log.log(Log.DEBUG, 'Игрок такой-то нажал туда-то')
    Log.stop()