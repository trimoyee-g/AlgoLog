import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

# Supabase signs tokens with asymmetric keys (ES256). PyJWKClient fetches and
# caches the public keys from the project's JWKS endpoint.
# verifies ES256/RS256 against JWKS. If Supabase rotates key type again,
# add the new alg to `algorithms` below.
_jwks_client = PyJWKClient(
    f"{settings.SUPABASE_PROJECT_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
)


def require_user(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> str:
    """Verify the Supabase-issued JWT and return the user's id (the `sub` claim).

    Also upserts the user row so the weekly digest knows their email.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization[len("Bearer "):]
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub claim")
    email = payload.get("email", "")

    user = db.get(User, user_id)
    if user is None:
        db.add(User(id=user_id, email=email))
        db.commit()
    elif email and user.email != email:
        user.email = email
        db.commit()

    return user_id
