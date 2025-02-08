from os import environ, getenv

API_ID = int(environ.get("API_ID", "24428727"))
API_HASH = environ.get("API_HASH", "1089a994258b8d77f06a2be5b1a01a31")
BOT_TOKEN = environ.get("BOT_TOKEN", "7946808913:AAGp_Coa3bnCMzVLoGml6xvQ-mr5gG90HI4")
LOG_CHANNEL = int(environ.get("LOG_CHANNEL", "-1002290791025"))
ADMINS = int(environ.get("ADMINS", "1137799257"))
DB_URI = environ.get("DB_URI", "mongodb+srv://bot:bot@cluster0.8vepzds.mongodb.net/?retryWrites=true&w=mmajority")
DB_NAME = environ.get("DB_NAME", "gfgfgfgt")

# forcesub 
FSUB = getenv("FSUB", "@codecbots")
CHID = int(getenv("CHID", "-1002068251462"))
