# coap_server.py

import asyncio
from aiocoap import resource, Context, Message
import aiocoap

class IoTResource(resource.Resource):
    def __init__(self):
        super().__init__()
        self.content = b'temp:0 hum:0'

    async def render_get(self, request):
        print("[SERVER] GET received")
        return Message(payload=self.content)

    async def render_put(self, request):
        print(f"[SERVER] PUT received: {request.payload.decode()}")
        self.content = request.payload
        return Message(code=aiocoap.CHANGED, payload=b"Updated")

def main():
    # Register CoAP resource
    root = resource.Site()
    root.add_resource(['iot', 'dev1'], IoTResource())

    asyncio.Task(Context.create_server_context(root))
    print("[SERVER] CoAP server running on coap://10.0.0.1/iot/dev1")
    asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    main()

