# coap_publisher.py

import asyncio
import random
from aiocoap import *

async def main():
    context = await Context.create_client_context()

    while True:
        temp = random.randint(25, 30)
        hum = random.randint(50, 90)
        payload = f"temp:{temp} hum:{hum}".encode('utf-8')
        request = Message(code=PUT, uri="coap://10.0.0.1/iot/dev1", payload=payload)

        response = await context.request(request).response
        print(f"[PUBLISHER] Sent: {payload.decode()}, Response: {response.code}")
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())

