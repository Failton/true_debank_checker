from loguru import logger
from sys import stderr

BLACK_COLOR = False # поменяйте на True, если неправильно отображается таблица

file_js = 'js/main.js'
file_excel = 'DEBANK.xlsx'
file_wallets = 'wallets.txt'

# LOGGING SETTING
file_log = 'logs/log.log'
logger.remove()
logger.add(stderr, format="<white>{time:HH:mm:ss}</white> | <level>{level: <8}</level> | <cyan>{line}</cyan> - <white>{message}</white>")
logger.add(file_log, format="<white>{time:HH:mm:ss}</white> | <level>{level: <8}</level> | <cyan>{line}</cyan> - <white>{message}</white>")
