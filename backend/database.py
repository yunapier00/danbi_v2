from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

\

# SQLite 파일 경로
SQLALCHEMY_DATABASE_URL = "sqlite:///./danbi_chat.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 대화 기록 테이블 정의
class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String) # 나중에 로그인 기능 추가 시 활용
    query = Column(Text)
    answer = Column(Text)
    category = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    retrieved_context = Column(Text, nullable=True) # 가져온 문서 내용 (길 수 있으므로 Text 사용)
    step1_time = Column(Float, nullable=True)       # 의도 파악 소요 시간
    step2_time = Column(Float, nullable=True)       # DB 검색/크롤링 소요 시간
    step3_time = Column(Float, nullable=True)       # 답변 생성 소요 시간
    total_time = Column(Float, nullable=True)

# 테이블 생성
Base.metadata.create_all(bind=engine)
