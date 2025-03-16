import sys
import os
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.tapo_controller import get_sensor_data
from utils.calculate import calculate_vpd

app = FastAPI()

# Allow CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "FastAPI is running on port 8001"}


async def fetch_live_vpd_data():
    """Fetches real sensor data and calculates VPD dynamically."""
    while True:
        # Fetch live sensor data
        air_temp, leaf_temp, humidity = await get_sensor_data()

        # Calculate VPD values
        vpd_air, vpd_leaf = calculate_vpd(air_temp, leaf_temp, humidity)

        yield {
            "temperature": air_temp,
            "humidity": humidity,
            "vpd_air": round(vpd_air, 2),
            "vpd_leaf": round(vpd_leaf, 2),
        }

        await asyncio.sleep(5)  # Fetch new data every 5 seconds


@app.websocket("/ws/vpd")
async def websocket_vpd(websocket: WebSocket):
    """Handles WebSocket connections for real-time VPD updates."""
    await websocket.accept()
    print("✅ WebSocket Connected")

    try:
        async for data in fetch_live_vpd_data():
            await websocket.send_text(json.dumps(data))
    except WebSocketDisconnect:
        print("🔌 WebSocket Disconnected. Cleaning up...")
    except RuntimeError as e:
        if "Cannot call 'send' once a close message has been sent." in str(e):
            print("⚠️ Ignoring WebSocket send error due to client disconnection.")
    except Exception as e:
        print(f"⚠️ Unexpected WebSocket Error: {e}")
    finally:
        print("🔄 WebSocket Connection Closed Gracefully")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

