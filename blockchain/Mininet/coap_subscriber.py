# coap_subscriber.py

import asyncio
from aiocoap import *

async def main():
    context = await Context.create_client_context()

    while True:
        request = Message(code=GET, uri="coap://10.0.0.1/iot/dev1")

        try:
            response = await context.request(request).response
        except Exception as e:
            print(f"[SUBSCRIBER] Failed to fetch: {e}")
        else:
            print(f"[SUBSCRIBER] Received: {response.payload.decode()}")

        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())

