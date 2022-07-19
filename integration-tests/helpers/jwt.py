from environs import Env
from jose import jwt as jose_jwt


def get_system_token() -> str:
    env: Env = Env()
    hs_issuer: str = env.str("HS_ISSUER")
    hs_key: str = env.str("HS_KEY")
    proxy_url: str = env.str("PROXY_URL")

    return jose_jwt.encode(
        {
            "metadata": {"system_id": "dhos-robot", "can_edit_spo2_scale": True},
            "iss": hs_issuer,
            "aud": proxy_url + "/",
            "scope": env.str("SYSTEM_JWT_SCOPE"),
            "exp": 9_999_999_999,
        },
        key=hs_key,
        algorithm="HS512",
    )
