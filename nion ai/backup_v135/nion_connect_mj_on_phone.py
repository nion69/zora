import qrcode
import os
from dotenv import load_dotenv
from livekit import api

load_dotenv()

# Get details from .env
url = os.getenv("LIVEKIT_URL", "NOT FOUND")
api_key = os.getenv("LIVEKIT_API_KEY", "NOT FOUND")
api_secret = os.getenv("LIVEKIT_API_SECRET", "NOT FOUND")

# Generate a Room Token
room_name = "jarvis-room"
token = api.AccessToken(api_key, api_secret) \
    .with_identity("neon-boss") \
    .with_name("Neon Boss") \
    .with_grants(api.VideoGrants(room_join=True, room=room_name)) \
    .to_jwt()

print("\n" + "="*50)
print(" CONNECT MJ TO YOUR PHONE")
print("="*50)
print("\nStep 1: Keep your MJ script running (python agent.py dev)")
print("Step 2: Scan the QR code that just opened on your PC.")
print("Step 3: It will open the LiveKit Playground and connect MJ automatically.")

print(f"\n LiveKit URL    : {url}")
print(f" Access Token   : {token}\n")
print("="*50 + "\n")

# Generate QR for LiveKit Playground directly with the token!
playground_url = f"https://agents-playground.livekit.io/?url={url}&token={token}"
qr = qrcode.QRCode(border=2)
qr.add_data(playground_url)
qr.make(fit=True)

try:
    img = qr.make_image(fill_color="black", back_color="white")
    img.save("phone_qr.png")
    os.startfile("phone_qr.png")
    print("QR Code Image opened! Scan it with your phone.")
except Exception as e:
    print(f"Could not open QR code image: {e}")

print("\nScan the QR code, and it will AUTOMATICALLY fill in the Token for you!")
