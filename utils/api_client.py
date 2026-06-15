import requests

class APIClient:

    def post(self, endpoint, payload, headers=None):

        response = requests.post(
            endpoint,
            json=payload,
            headers=headers
        )

        return response

    def get(self, endpoint, headers=None):

        response = requests.get(
            endpoint,
            headers=headers
        )

        return response