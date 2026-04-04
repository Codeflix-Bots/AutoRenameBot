import aiohttp
import json

async def get_shortlink(url, api, link):
    try:
        async with aiohttp.ClientSession() as session:
            request_url = f"https://{url}/api?api={api}&url={link}"
            async with session.get(request_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("shortenedUrl")
    except Exception as e:
        print(f"Error getting shortlink: {e}")
    return link
