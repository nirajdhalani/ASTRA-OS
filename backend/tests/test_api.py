from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.database import Base, get_db
from app.main import create_app


def test_register_login_and_authenticated_profile(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    app = create_app()
    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        created = client.post("/api/auth/register", json={"email":"operator@example.com","password":"correct-horse-77","locale":"en"})
        assert created.status_code == 201, created.text
        token = created.json()["access_token"]
        me = client.get("/api/auth/me", headers={"Authorization":f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["email"] == "operator@example.com"
        login = client.post("/api/auth/login", json={"email":"operator@example.com","password":"correct-horse-77"})
        assert login.status_code == 200
        from app.api import charts as charts_api
        monkeypatch.setattr(charts_api, "_calculate", lambda payload: (
            {"birth": {}, "planetary_positions": {}, "vimshottari_dasha": None},
            {"place": "Junagadh, India", "latitude": 21.5, "longitude": 70.4, "timezone_name": "Asia/Kolkata"},
        ))
        chart_payload = {
            "label": "Test chart", "birth_date": "1998-06-09", "birth_time": "15:15",
            "place": "Junagadh, India", "latitude": 21.5, "longitude": 70.4,
            "timezone_name": "Asia/Kolkata", "chart_system": "vedic", "ayanamsa": "lahiri",
        }
        for _ in range(3):
            saved = client.post("/api/charts", json=chart_payload, headers={"Authorization": f"Bearer {token}"})
            assert saved.status_code == 201, saved.text
        blocked = client.post("/api/charts", json=chart_payload, headers={"Authorization": f"Bearer {token}"})
        assert blocked.status_code == 402
        assert "Free plan limit reached" in blocked.json()["detail"]
        denied = client.get("/api/auth/me")
        assert denied.status_code == 401
    Base.metadata.drop_all(bind=engine)
