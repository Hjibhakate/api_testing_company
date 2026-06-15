import requests


class APIClient:
    def post(self, endpoint, payload, headers=None, timeout=60):
        print(f"[HTTP POST] {endpoint}")
        if payload is None:
            print("[HTTP POST] payload: None")
        else:
            if isinstance(payload, dict):
                print(f"[HTTP POST] payload keys: {list(payload.keys())}")
            else:
                print("[HTTP POST] payload: <non-dict>")

        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=timeout,
        )

        text = response.text
        if text and len(text) > 1500:
            text = text[:1500] + "...<truncated>"

        print(f"[HTTP POST] status: {response.status_code}")
        print(f"[HTTP POST] response: {text}")
        return response

    def get(self, endpoint, headers=None, timeout=60):
        print(f"[HTTP GET] {endpoint}")

        response = requests.get(
            endpoint,
            headers=headers,
            timeout=timeout,
        )

<<<<<<< HEAD
        return response

###
=======
        text = response.text
        if text and len(text) > 1500:
            text = text[:1500] + "...<truncated>"

        print(f"[HTTP GET] status: {response.status_code}")
        print(f"[HTTP GET] response: {text}")
        return response

    def patch(self, endpoint, payload, headers=None, timeout=60):
        print(f"[HTTP PATCH] {endpoint}")
        if payload is None:
            print("[HTTP PATCH] payload: None")
        else:
            if isinstance(payload, dict):
                print(f"[HTTP PATCH] payload keys: {list(payload.keys())}")
            else:
                print("[HTTP PATCH] payload: <non-dict>")

        response = requests.patch(
            endpoint,
            json=payload,
            headers=headers,
            timeout=timeout,
        )

        text = response.text
        if text and len(text) > 1500:
            text = text[:1500] + "...<truncated>"

        print(f"[HTTP PATCH] status: {response.status_code}")
        print(f"[HTTP PATCH] response: {text}")
        return response

>>>>>>> d25cd948e1928e01c19b0bb226decd08b03816be
