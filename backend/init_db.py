import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from app.models.user import User, UserTier
from app.models.history import Verification, AnalysisMetrics, CacheRegistry

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def init_db():
    if not DATABASE_URL:
        print("DATABASE_URL not set in .env")
        return

    print(f"Connecting to {DATABASE_URL}...")
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    from app.core.database import Base
    
    try:
        async with engine.begin() as conn:
            print("Creating tables...")
            await conn.run_sync(Base.metadata.create_all)
            print("Done.")
    except Exception as e:
        if "gaierror" in str(e) or "Temporary failure in name resolution" in str(e):
            print("\n❌ ERRO DE CONEXÃO: O endereço do banco de dados não pôde ser resolvido.")
            print("💡 DICA: Como você está rodando fora do Docker, certifique-se de que o DATABASE_URL no seu .env está como 'localhost' e não 'db'.")
        else:
            print(f"\n❌ Ocorreu um erro: {e}")
        return

    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())
