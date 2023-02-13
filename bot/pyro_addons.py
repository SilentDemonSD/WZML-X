#!/usr/bin/python3
# Based On https://github.com/Ripeey/Conversation-Pyrogram

from collections import OrderedDict
from typing import Union
import pyrogram, asyncio

class Conversation():
	def __init__(self, client : pyrogram.Client):
		client.listen = self
		self.client = client
		self.handlers = {}
		self.hdlr_lock = asyncio.Lock()

	async def __add(self, hdlr, filters = None, id = None, timeout = None):
		_id = id

		if type(_id) in [pyrogram.filters.InvertFilter, pyrogram.filters.OrFilter, pyrogram.filters.AndFilter]:
			raise ValueError('Combined filters are not allowed as unique id .')
		
		if _id and type(_id) not in [pyrogram.filters.user, pyrogram.filters.chat, str]:
			raise TypeError('Unique (id) has to be one of pyrogram\'s filters user/chat or a string.')
		
		if not (_id or filters):
			raise ValueError('Atleast either filters or _id as parameter is required.')

		if str(_id) in self.handlers:
			await self.__remove(str(_id))
			#raise ValueError('Dupicate id provided.')

		# callback handler
		async def dump(_, update):
			await self.__remove(dump._id, update)

		dump._id = str(_id) if _id else hash(dump)
		group = -0x3e7
		event = asyncio.Event()
		filters	= (_id & filters) if _id and filters and not isinstance(_id, str) else filters or (filters if isinstance(_id, str) else _id)
		handler = hdlr(dump, filters)
		
		
		if group not in self.client.dispatcher.groups:
			self.client.dispatcher.groups[group] = []
			self.client.dispatcher.groups = OrderedDict(sorted(self.client.dispatcher.groups.items()))

		async with self.hdlr_lock:
			self.client.dispatcher.groups[group].append(handler)
			self.handlers[dump._id] = (handler, group, event)

		try:
			await asyncio.wait_for(event.wait(), timeout)
		except asyncio.exceptions.TimeoutError:
			await self.__remove(dump._id)
			raise asyncio.exceptions.TimeoutError
		finally:
			result = self.handlers.pop(dump._id, None)
			self.hdlr_lock.release()
		return result

	async def __remove(self, _id, update = None):
		handler, group, event = self.handlers[_id]
		self.client.dispatcher.groups[group].remove(handler)
		await self.hdlr_lock.acquire()
		self.handlers[_id] = update
		event.set()

	async def Cancel(self, _id):
		if str(_id) in self.handlers:
			await self.__remove(str(_id))
			return True
		else:
			return False

	def __getattr__(self, name):
		async def wrapper(*args, **kwargs):
			return await self.__add(getattr(pyrogram.handlers, f'{name}Handler'), *args, **kwargs)
		return wrapper
