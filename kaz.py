# public version of poopyscript
import time
import telebot
from loguru import logger
from system.lib import minescript
from collections import OrderedDict

# logging (optional)
logger.remove()
logger.add(r"path to logs",
           rotation="20:00", compression="gz", level="INFO", retention="5 days")

bot = telebot.TeleBot("tg bot token")

# queues
payment_queue = OrderedDict()
message_queue = OrderedDict()
last_pay_time = 0
last_msg_time = 0
DELAY = 8

# temp bans
temp_bans = {}
spam_counter = {}
SPAM_LIMIT = 5
SPAM_WINDOW = 25
BAN_DURATION = 120

with minescript.EventQueue() as events:
    events.register_chat_listener()

    while True:
        try:
            event = events.get(timeout=1)

            if event and event.type == minescript.EventType.CHAT:
                try:
                    original_text = event.message.encode('cp1251').decode('utf-8')
                except:
                    original_text = event.message

                clean_text = original_text.encode('utf-16', 'surrogatepass').decode('utf-16', 'ignore')

                # Проверка входящего перевода
                if clean_text.startswith("[$]") and clean_text.endswith("$") and "отправлено" not in clean_text:
                    logger.info(f"Pay detected: {clean_text}")

                    summ_str = clean_text.split()[-1]
                    start = 14
                    rest = clean_text[start:]
                    end = rest.find(' ')
                    player = rest[:end] if end != -1 else rest

                    if player in temp_bans:
                        if time.monotonic() < temp_bans[player]:
                            logger.info(f"{player} is banned")
                            continue
                        else:
                            del temp_bans[player]
                            spam_counter.pop(player, None)

                    current_time = time.monotonic()
                    if player not in spam_counter:
                        spam_counter[player] = {"count": 1, "first_time": current_time}
                    else:
                        spam_counter[player]["count"] += 1

                        time_passed = current_time - spam_counter[player]["first_time"]
                        if time_passed <= SPAM_WINDOW and spam_counter[player]["count"] >= SPAM_LIMIT:
                            unban_time = current_time + BAN_DURATION
                            temp_bans[player] = unban_time

                            ban_msg = f"Spam-защита: вы забанены на {BAN_DURATION} secs за слишком often переводы "
                            if player not in message_queue:
                                message_queue[player] = ban_msg
                            else:
                                message_queue[player] += ban_msg

                            logger.warning(f"{player} is banned for {BAN_DURATION} sec cause of spam")
                            continue

                    m = bot.send_message("chat id", f"Игрок {player} отправил {summ_str}", message_thread_id=12232)

                    try:
                        to_send = int(summ_str[:-1].replace(",", ""))
                    except ValueError:
                        continue

                    if 1000 <= to_send <= 1000000:
                        mm = bot.send_dice(chat_id="chat id", message_thread_id=12232, emoji="🎲",
                                           reply_to_message_id=m.message_id)

                        dice_val = mm.dice.value
                        win_multiplier = 0

                        if dice_val == 6:
                            win_multiplier = 2
                        elif dice_val == 5:
                            win_multiplier = 1.5
                        elif dice_val == 2:
                            win_multiplier = 1
                        else:
                            if player not in message_queue:
                                message_queue[player] = f"Тебе выпало {dice_val} :( sorry. "
                            else:
                                message_queue[player] += f"Тебе выпало {dice_val} :( sorry. "
                            continue

                        # Победа
                        final_amount = int(to_send * win_multiplier)

                        # Добавляем уведомление в очередь сообщений
                        if player not in message_queue:
                            message_queue[player] = f"You выпало {dice_val}! Ты won {final_amount}. "
                        else:
                            message_queue[player] += f"You выпало {dice_val}! Ты won {final_amount}. "

                        # Добавляем деньги в очередь выплат
                        if player in payment_queue:
                            payment_queue[player] += final_amount
                        else:
                            payment_queue[player] = final_amount

        except Exception as e:
            pass

        current_time = time.monotonic()

        if message_queue and (current_time - last_msg_time >= DELAY):
            msg_command = message_queue.popitem(last=False)
            try:
                minescript.execute(f"/m {msg_command[0]} {msg_command[1]}")
                logger.info(f"Msg: /m {msg_command[0]} {msg_command[1]}")

            except Exception as e:
                logger.error(f"An error occured while /m: {e}")
            last_msg_time = current_time

        if payment_queue and (current_time - last_pay_time >= DELAY):
            item = payment_queue.popitem(last=False)
            summa = item[1]
            playera = item[0]
            try:
                minescript.execute(f"/pay {playera} {summa}")
                if summa > 100000:
                    minescript.execute(f"/pay {playera} {summa}")
                logger.info(f"Pay:: {playera}: {summa}")
            except Exception as e:
                logger.error(f"An error occured while /pay: {e}")
            last_msg_time = current_time

