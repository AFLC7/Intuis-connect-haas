"""Constants for the Intuis Connect integration."""

DOMAIN = "intuis_connect"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# API endpoints Intuis Connect (API Muller/Netatmo)
API_BASE_URL = "https://app.muller-intuitiv.net"
API_LOGIN = "/oauth2/token"
API_HOMESDATA = "/api/homesdata"
API_HOMESTATUS = "/syncapi/v1/homestatus"
API_SETROOMTHERMPOINT = "/syncapi/v1/setroomthermpoint"

# OAuth credentials (publiques de l'app Muller)
CLIENT_ID = "59e604948fe283fd4dc7e355"
CLIENT_SECRET = "rAeWu8Y3YqXEPqRJ4BpFzFG98MRXpCcz"

# Scan interval
SCAN_INTERVAL_SECONDS = 300  # 5 minutes

# Default values
DEFAULT_MIN_TEMP = 7
DEFAULT_MAX_TEMP = 30
