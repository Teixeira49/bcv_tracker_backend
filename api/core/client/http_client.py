import requests

class HttpClient:
    def __init__(self):
        pass

    async def get(self, url, params=None, headers=None):
        try:
            response = requests.get(url=url, params=params, headers=headers)
            if response.status_code != 200:
                raise Exception
            return response.json()
        except Exception as e:
            raise e

    async def get_content(self, url, params=None, headers=None, verify=None):
        try:
            response = requests.get(url=url, params=params, headers=headers, verify=verify)
            if response.status_code != 200:
                raise Exception
            return response.content
        except Exception as e:
            raise e      
        
    async def post(self, url, data=None, headers=None):
        try:
            response = requests.post(url=url, data=data, headers=headers,)
            if response.status_code != 200:
                raise Exception
            return response.json()
        except Exception as e:
            raise e
        
    async def put(self, url, data=None, headers=None):
        try:
            response = requests.put(url=url, data=data, headers=headers)
            if response.status_code != 200:
                raise Exception
            return response.json()
        except Exception as e:
            raise e
        
    async def delete(self, url, data=None, headers=None):
        try:
            response = requests.delete(url=url, data=data, headers=headers)
            if response.status_code != 200:
                raise Exception
            return response.json()
        except Exception as e:
            raise e
        
    async def patch(self, url, data=None, headers=None):
        try:
            response = requests.patch(url=url, data=data, headers=headers)  
            if response.status_code != 200:
                raise Exception
            return response.json()
        except Exception as e:
            raise e