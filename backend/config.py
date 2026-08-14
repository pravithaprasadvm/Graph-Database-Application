import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    COGNO_URI: str = os.getenv("COGNO_URI", "bolt+s://demo-instance.databases.cognodb.cloud")
    COGNO_USER: str = os.getenv("COGNO_USER", "cognodb")
    COGNO_PASSWORD: str = os.getenv("COGNO_PASSWORD", "demo_password")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    @classmethod
    def is_configured(cls) -> bool:
        return (
            bool(cls.COGNO_URI) and 
            "demo-instance" not in cls.COGNO_URI and 
            "your-instance-id" not in cls.COGNO_URI and
            bool(cls.COGNO_PASSWORD) and 
            "your_cognodb_password" not in cls.COGNO_PASSWORD
        )

config = Config()
