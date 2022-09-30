import time

from bot import TIME_GAP, TIME_GAP_STORE
from bot.helper.ext_utils.bot_utils import timeformatter

def timegap_check(message):
  if message.from_user.id in TIME_GAP_STORE:
    if int(time.time() - TIME_GAP_STORE[message.from_user.id]) < TIME_GAP:
      wtime = timeformatter((int(TIME_GAP_STORE[message.from_user.id]) + TIME_GAP - int(time.time())) * 1000)
      #rtime = timeformatter(TIME_GAP)
      text = f"Please wait {wtime}. Normal Users have Time Restriction for {TIME_GAP} sec. "
      message.reply_text(
                text=text,
                parse_mode="markdown",
                quote=True
            )
      return True 
    else:
      del TIME_GAP_STORE[message.from_user.id]
      return False
  else:
    return False