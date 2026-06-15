from fastapi.testclient import TestClient
import asyncio
from app.main import app

client = TestClient(app)

# We can't really test db integration without mock, but let's test if route exists and schema matches
response = client.post("/auth/google", json={"credential": "dummy_token"})
print("Status Code:", response.status_code)
print("Response Body:", response.json())
