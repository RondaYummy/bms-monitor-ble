import asyncio
from datetime import datetime
from copy import deepcopy

class DataStore:
    def __init__(self):
        self.cell_info = {}
        self.setting_info = {}
        self.last_cell_info_update = {}
        self.response_buffers = {}
        self.active_tokens = {}
        self.lock = asyncio.Lock()

    async def add_token(self, token: str, device_name: str):
        async with self.lock:
            self.active_tokens[token] = {"device_name": device_name}

    async def remove_token(self, token: str):
        async with self.lock:
            if token in self.active_tokens:
                del self.active_tokens[token]

    async def is_token_valid(self, token: str) -> bool:
        async with self.lock:
            return token in self.active_tokens
        
    async def delete_device_data(self, device_name):
        async with self.lock:
            if device_name in self.cell_info:
                del self.cell_info[device_name]
            if device_name in self.last_cell_info_update:
                del self.last_cell_info_update[device_name]
            if device_name in self.response_buffers:
                del self.response_buffers[device_name]

    async def update_last_cell_info_update(self, device_name):
        async with self.lock:
            self.last_cell_info_update[device_name] = datetime.now()

    async def get_last_cell_info_update(self, device_name):
        async with self.lock:
            return self.last_cell_info_update.get(device_name, None)
        
    async def append_to_buffer(self, device_name, data):
        async with self.lock:
            if device_name not in self.response_buffers:
                self.response_buffers[device_name] = bytearray()
            self.response_buffers[device_name].extend(data)

    async def get_buffer(self, device_name):
        async with self.lock:
            return self.response_buffers.get(device_name, bytearray())

    async def clear_buffer(self, device_name):
        async with self.lock:
            if device_name in self.response_buffers:
                self.response_buffers[device_name].clear()

    async def update_cell_info(self, device_name, info):
        async with self.lock:
            self.cell_info[device_name] = info

    async def get_cell_info(self):
        async with self.lock:
            return deepcopy(self.cell_info)

    async def update_setting_info(self, device_address, info):
        async with self.lock:
            self.setting_info[device_address] = info

    async def get_setting_info(self, device_address):
        async with self.lock:
            print(f"REQUEST ADDRESS: {device_address}")
            print(f"ALL DATA: {self.setting_info}")
            return deepcopy(self.setting_info.get(device_address, {}))

# Initialize the centralized data storage
data_store = DataStore()
