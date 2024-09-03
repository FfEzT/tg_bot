import logging
import paramiko
import time

import re, os
from dotenv import load_dotenv

from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

import psycopg2
from psycopg2 import Error

from pathlib import Path

load_dotenv()
TOKEN =    os.getenv('TOKEN')

host =     os.getenv('RM_HOST')
port =     os.getenv('RM_PORT')
username = os.getenv('RM_USER')
password = os.getenv('RM_PASSWORD')

DB_HOST          = os.getenv('DB_HOST')
DB_USER          = os.getenv('DB_USER')
DB_PASSWORD      = os.getenv('DB_PASSWORD')
DB_PORT         = os.getenv('DB_PORT')
DB_DATABASE = os.getenv('DB_DATABASE')


client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())


foundedPhones = None
foundedEmails = None


# Подключаем логирование
logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.CRITICAL
)

logger = logging.getLogger(__name__)

def splitMessage(update: Update, text: str, max_length=4096, delay=0.5):
    parts = [text[i:i+max_length] for i in range(0, len(text), max_length)]
    for part in parts:
        update.message.reply_text(part)
        time.sleep(delay)

def db_request(req):
    connection = None
    res = None

    try:
        connection = psycopg2.connect(user=DB_USER,
                                      password=DB_PASSWORD,
                                      host=DB_HOST,
                                      port=DB_PORT,
                                      database=DB_DATABASE)

        cursor = connection.cursor()
        cursor.execute(req)
        res = cursor.fetchall()

    except (Exception, Error) as error:
        logging.error("Ошибка при работе с PostgreSQL: %s", error)
    finally:
        if connection is not None:
            cursor.close()
            connection.close()
            return res
        return False


def db_insert(req):
    connection = None
    res = None

    try:
        connection = psycopg2.connect(user=DB_USER,
                                      password=DB_PASSWORD,
                                      host=DB_HOST,
                                      port=DB_PORT,
                                      database=DB_DATABASE)

        cursor = connection.cursor()
        cursor.execute(req)
        connection.commit()

    except (Exception, Error) as error:
        logging.error("Ошибка при работе с PostgreSQL: %s", error)
    finally:
        if connection is not None:
            cursor.close()
            connection.close()
            return True
        return False

def start(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f'Привет {user.full_name}!')


def helpCommand(update: Update, context):
    update.message.reply_text('Help!')


def findPhoneNumbersCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска телефонных номеров: ')

    return 'findPhoneNumbers'

def findPhoneNumbers(update: Update, context):
    global foundedPhones
    user_input = update.message.text

    phoneNumRegexs = [
        re.compile(r'8 \(\d{3}\) \d{3}-\d{2}-\d{2}'),   # формат 8 (000) 000-00-00
        re.compile(r'\+7 \(\d{3}\) \d{3}-\d{2}-\d{2}'),   # формат 8 (000) 000-00-00
        re.compile(r'8\d{10}'),                         # формат 80000000000
        re.compile(r'\+7\d{10}'),                         # формат 80000000000
        re.compile(r'8\(\d{3}\)\d{7}'),                 # формат 8(000)0000000
        re.compile(r'\+7\(\d{3}\)\d{7}'),                 # формат 8(000)0000000
        re.compile(r'8 \d{3} \d{3} \d{2} \d{2}'),       # формат 8 000 000 00 00
        re.compile(r'\+7 \d{3} \d{3} \d{2} \d{2}'),       # формат 8 000 000 00 00
        re.compile(r'8 \(\d{3}\) \d{3} \d{2} \d{2}'),   # формат 8 (000) 000 00 00
        re.compile(r'\+7 \(\d{3}\) \d{3} \d{2} \d{2}'),   # формат 8 (000) 000 00 00
        re.compile(r'8-\d{3}-\d{3}-\d{2}-\d{2}'),       # формат 8-000-000-00-00
        re.compile(r'\+7-\d{3}-\d{3}-\d{2}-\d{2}'),       # формат 8-000-000-00-00
    ]

    phoneNumberList = [] # Ищем номера телефонов
    for i in phoneNumRegexs:
        phoneNumberList.extend(i.findall(user_input))
    if not phoneNumberList:
        update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END

    phoneNumbers = ''
    for i in range(len(phoneNumberList)):
        phoneNumbers += f'{i+1}. {phoneNumberList[i]}\n'

    update.message.reply_text(phoneNumbers)
    foundedPhones = phoneNumberList
    update.message.reply_text("Я могу их записать в базу данных. Напишите 'y', чтобы записать")

    return 'addPhone'

def addPhone(update: Update, context):
    user_input = update.message.text
    if user_input == 'y':
        res = ''
        for i in foundedPhones:
            res += "('" + i + "')" + ','
        res = res[:-1:]

        # ! vuln
        if db_insert('insert into phones (phone_number) values ' + res + ';'):
            update.message.reply_text("Данные записаны")
        else: update.message.reply_text("Данные не записаны(Error)")
    else:
        update.message.reply_text("Данные не записаны")

    return ConversationHandler.END


def findEmailCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска адреса почты: ')

    return 'findEmail'

def findEmail(update: Update, context):
    global foundedEmails

    user_input = update.message.text

    emailRegex = re.compile(r'[\w\.]{3,40}@\w{1,15}\.\w{1,5}') # aga.re@gmail.com

    emailList = emailRegex.findall(user_input)
    if not emailList:
        update.message.reply_text('Email адреса не найдены')
        return ConversationHandler.END

    email = ''
    for i in range(len(emailList)):
        email += f'{i+1}. {emailList[i]}\n'

    update.message.reply_text(email)
    foundedEmails = emailList
    update.message.reply_text("Я могу их записать в базу данных. Напишите 'y', чтобы записать")

    return 'addEmail'

def addEmail(update: Update, context):
    user_input = update.message.text
    if user_input == 'y':
        res = ''
        for i in foundedEmails:
            res += "('" + i + "')" + ','
        res = res[:-1:]

        # ! vuln
        if db_insert('insert into emails (email) values ' + res + ';'):
            update.message.reply_text("Данные записаны")
        else: update.message.reply_text("Данные не записаны(Error)")
    else:
        update.message.reply_text("Данные не записаны")

    return ConversationHandler.END


def get_apt_list_command(update: Update, context):
    update.message.reply_text('Введите "y", чтобы вывести все пакеты\nИли введите название пакета: ')

    return 'get_apt_list'

def get_apt_list(update: Update, context):
    command = 'apt list '
    # ! vuln
    user_input = update.message.text

    if user_input == 'y':
        update.message.reply_text(RCE(command + ' | head -n10', host, port, username, password))
    else:
        update.message.reply_text(RCE(command + user_input + ' | head -n10', host, port, username, password))
    return ConversationHandler.END


def verify_password_command(update: Update, context):
    update.message.reply_text('Введите текст проверки пароля: ')

    return 'verify_password'

def verify_password(update: Update, context):
    user_input = update.message.text

    regExps = [
        re.compile(r'\S{8,}'),
        re.compile(r'[A-Z]'),
        re.compile(r'[a-z]'),
        re.compile(r'\d'),
        re.compile(r'[\!\@\#\$\%\^\&\*\(\)\.]')
    ]
    for i in regExps:
        if not i.search(user_input):
            update.message.reply_text('Пароль простой')
            return ConversationHandler.END
    update.message.reply_text('Пароль сложный')
    return ConversationHandler.END


def echo(update: Update, context):
    update.message.reply_text(update.message.text)

def RCE(command, host, port, username, password):
    client.connect(hostname=host, username=username, password=password, port=port)
    stdin, stdout, stderr = client.exec_command(command)
    data = stdout.read() + stderr.read()
    data = data.decode('utf-8')
    client.close()
    data = str(data).replace('\\n', '\n').replace('\\t', '\t')[2:-1]
    return data

def get_release(update: Update, context):
    update.message.reply_text(RCE('uname -r', host, port, username, password))

def get_uname(update: Update, context):
    update.message.reply_text(RCE('uname -a', host, port, username, password))

def get_uptime(update: Update, context):
    update.message.reply_text(RCE('uptime', host, port, username, password))

def get_df(update: Update, context):
    update.message.reply_text(RCE('df -h', host, port, username, password))

def get_free(update: Update, context):
    update.message.reply_text(RCE('free -h', host, port, username, password))

def get_mpstat(update: Update, context):
    update.message.reply_text(RCE('mpstat', host, port, username, password))

def get_w(update: Update, context):
    update.message.reply_text(RCE('w', host, port, username, password))

def get_auths(update: Update, context):
    update.message.reply_text(RCE('last | head -n10', host, port, username, password))

def get_critical(update: Update, context):
    update.message.reply_text(RCE('journalctl -p crit | head -n5', host, port, username, password))

def get_ss(update: Update, context):
    update.message.reply_text(RCE('netstat -lntu', host, port, username, password))

def get_ps(update: Update, context):
    update.message.reply_text(RCE('ps aux | head -n10', host, port, username, password))

# def get_apt_list(update: Update, context):
#     command = 'apt list '
#     args = update.message.text.split(' ')[1::]
#     for arg in args:
#         command += arg
#         command += ' '

#     update.message.reply_text(RCE(command + ' | head -n10'))

def get_services(update: Update, context):
    update.message.reply_text(RCE('systemctl list-units --type=service | head -n10', host, port, username, password))

def get_repl_logs(update: Update, context):
    log_dir = Path('/app/logs')
    log_file_path = log_dir / 'postgresql.log'

    try:
        if log_file_path.exists():
            res = ""
            with open(log_file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    lowerLine = line.casefold()
                    if ('repl' in lowerLine) or ('репл' in lowerLine):
                        res += line.rstrip() + "\n"

            if res:
                splitMessage(update, res)
            else:
                update.message.reply_text("No logs")
                logging.info("No logs")
        else:
            update.message.reply_text("File for log didn't find")
            logging.error("File for log didn't find")
    except Exception as e:
        update.message.reply_text(f"Error log: {str(e)}")
        logging.error(f"Error log: {str(e)}")

def get_emails(update: Update, context):
    res = db_request("SELECT * FROM emails;")
    for row in res:
        update.message.reply_text(row)

    if not res:
        update.message.reply_text("Пусто")

def get_phone_numbers(update: Update, context):
    res = db_request("SELECT * FROM phones;")
    for row in res:
        update.message.reply_text(row)

    if not res:
        update.message.reply_text("Пусто")


def main():
    updater = Updater(TOKEN, use_context=True)

    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher


    # Обработчик диалога
    convHandlerFindPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('findPhoneNumbers', findPhoneNumbersCommand)],
        states={
            'findPhoneNumbers': [MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
            'addPhone': [MessageHandler(Filters.text & ~Filters.command, addPhone)],
        },
        fallbacks=[]
    )
    convHandlerFindEmail = ConversationHandler(
        entry_points=[CommandHandler('findEmail', findEmailCommand)],
        states={
            'findEmail': [MessageHandler(Filters.text & ~Filters.command, findEmail)],
            'addEmail' : [MessageHandler(Filters.text & ~Filters.command, addEmail)]
        },
        fallbacks=[]
    )
    convHandlerCheckPassword = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verify_password_command)],
        states={
            'verify_password': [MessageHandler(Filters.text & ~Filters.command, verify_password)],
        },
        fallbacks=[]
    )
    convHandlerCheckApt = ConversationHandler(
        entry_points=[CommandHandler('get_apt_list', get_apt_list_command)],
        states={
            'get_apt_list': [MessageHandler(Filters.text & ~Filters.command, get_apt_list)],
        },
        fallbacks=[]
    )

    # Регистрируем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", helpCommand))

    dp.add_handler(CommandHandler("get_release", get_release))
    dp.add_handler(CommandHandler("get_uname", get_uname))
    dp.add_handler(CommandHandler("get_uptime", get_uptime))
    dp.add_handler(CommandHandler("get_df", get_df))
    dp.add_handler(CommandHandler("get_free", get_free))
    dp.add_handler(CommandHandler("get_mpstat", get_mpstat))
    dp.add_handler(CommandHandler("get_w", get_w))
    dp.add_handler(CommandHandler("get_auths", get_auths))
    dp.add_handler(CommandHandler("get_critical", get_critical))
    dp.add_handler(CommandHandler("get_ps", get_ps))
    dp.add_handler(CommandHandler("get_ss", get_ss))
    # dp.add_handler(CommandHandler("get_apt_list", get_apt_list))
    dp.add_handler(CommandHandler("get_services", get_services))
    dp.add_handler(CommandHandler("get_repl_logs", get_repl_logs))

    dp.add_handler(CommandHandler("get_emails", get_emails))
    dp.add_handler(CommandHandler("get_phone_numbers", get_phone_numbers))

    dp.add_handler(convHandlerFindPhoneNumbers)
    dp.add_handler(convHandlerFindEmail)
    dp.add_handler(convHandlerCheckPassword)
    dp.add_handler(convHandlerCheckApt)


    # Регистрируем обработчик текстовых сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))


    # Запускаем бота
    updater.start_polling()


    # Останавливаем бота при нажатии Ctrl+C
    updater.idle()


if __name__ == '__main__':
    main()
