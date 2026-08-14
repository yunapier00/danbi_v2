from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta, timezone

# SQLite 파일 경로
SQLALCHEMY_DATABASE_URL = "sqlite:///./danbi_chat.db"

# SQLite 사용 시 스레드 설정
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_kst_now():
    return datetime.now(timezone.utc) + timedelta(hours=9)

# 대화 기록 테이블 정의
class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    
    # 잦은 조회가 발생하는 user_id에 index=True 추가 (Rate Limit 쿼리 최적화)
    user_id = Column(String, index=True) 
    
    query = Column(Text)
    answer = Column(Text)
    category = Column(String)
    
   
    created_at = Column(DateTime, default=get_kst_now, index=True)

    retrieved_context = Column(Text, nullable=True) # 가져온 문서 내용
    step1_time = Column(Float, nullable=True)       # 의도 파악 소요 시간
    step2_time = Column(Float, nullable=True)       # DB 검색/크롤링 소요 시간
    step3_time = Column(Float, nullable=True)       # 답변 생성 소요 시간
    total_time = Column(Float, nullable=True)       # 전체 소요 시간

# 테이블 생성
Base.metadata.create_all(bind=engine)
