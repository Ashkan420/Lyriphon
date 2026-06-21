import sys
import os

# Add the project root to sys.path so that imports like `from services.x import y` work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Stub config module before anything imports it
import types

config_stub = types.ModuleType("config")
config_stub.BOT_TOKEN = "fake-bot-token"
config_stub.TELEGRAPH_ACCESS_TOKEN = "fake-telegraph-token"
config_stub.DATABASE_URL = "postgresql://fake:fake@localhost/fake"
config_stub.CHANNEL_LINK = "https://t.me/testchannel"
config_stub.DEEZLOAD_BOT = "http://t.me/testbot?start="

sys.modules["config"] = config_stub
