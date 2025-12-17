import asyncio
from spade.agent import Agent
from slixmpp import ClientXMPP

import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

original_connect = ClientXMPP.connect
def patched_connect(self, address=None, **kwargs):
    print(f"DEBUG PATCH: address={address}, kwargs={kwargs}")
    if address:
        host, port = address
        return original_connect(self, host=host, port=port, **kwargs)
    return original_connect(self, **kwargs)
ClientXMPP.connect = patched_connect

class TestAgent(Agent):
    async def setup(self):
        print("Connected successfully!")

async def main():
    jid = "server@localhost"
    pwd = "password"
    print(f"Attempting connect with {jid} / {pwd}")
    agent = TestAgent(jid, pwd)
    try:
        await agent.start(auto_register=False)
        print("Agent start returned.")
        await agent.stop()
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
