"""Constants for Intuis Connect integration."""

DOMAIN = "intuis_connect"

# API Intuis Connect (Muller/Netatmo)
API_BASE_URL = "https://app.muller-intuitiv.net"
API_TOKEN = "/oauth2/token"
API_HOMESDATA = "/api/homesdata"
API_HOMESTATUS = "/syncapi/v1/homestatus"
API_SETTEMP = "/api/setroomthermpoint"

# OAuth2 credentials (public from Muller app)
CLIENT_ID = "59e604948fe283fd4dc7e355"
CLIENT_SECRET = "rAeWu8Y3YqXEPqRJ4BpFzFG98MRXpCcz"

# Update interval
SCAN_INTERVAL = 60  # seconds

# Temperature limits
MIN_TEMP = 7
MAX_TEMP = 30
