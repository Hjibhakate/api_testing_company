import requests


class APIClient:
    def post(self, endpoint, payload, headers=None, timeout=60):
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        return response

    def get(self, endpoint, headers=None, timeout=60):
        response = requests.get(
            endpoint,
            headers=headers,
            timeout=timeout,
        )
        return response

    def patch(self, endpoint, payload, headers=None, timeout=60):
        response = requests.patch(
            endpoint,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        return response
