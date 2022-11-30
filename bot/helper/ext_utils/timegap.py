from time import time

from bot import config_dict, TIME_GAP_STORE
from bot.helper.ext_utils.bot_utils import timeformatter

def timegap_check(message):
  if message.from_user.id in TIME_GAP_STORE:
    if int(time() - TIME_GAP_STORE[message.from_user.id]) < config_dict['TIME_GAP']:
      wtime = timeformatter((int(TIME_GAP_STORE[message.from_user.id]) + config_dict['TIME_GAP'] - int(time())) * 1000)
      #rtime = timeformatter(config_dict['TIME_GAP'])
      text = f"Please wait {wtime}. Normal Users have Time Restriction for {config_dict['TIME_GAP']} sec. "
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
