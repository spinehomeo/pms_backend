from pms_backend.stapi.testclient import TestClient
from pms_backend.lmodel import Session, select

from pms_backend...core.config import settings
from pms_backend...models.models import User


def test_create_user(client: TestClient, db: Session) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/private/users/",
        json={
            "email": "pollo@listo.com",
            "password": "password123",
            "full_name": "Pollo Listo",
        },
    )

    assert r.status_code == 200

    data = r.json()

    user = db.exec(select(User).where(User.id == data["id"])).first()

    assert user
    assert user.email == "pollo@listo.com"
    assert user.full_name == "Pollo Listo"
