import aiohttp


class FilmAPI:
    def __init__(self, url: str, headers, params=None) -> None:
        self.url = url
        self.headers = headers
        self.params = params

    async def fetch_data(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url, params=self.params, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_message = await response.text()
                    print(f"ERROR: {response.status}, MESSAGE: {error_message}")
                    return None


