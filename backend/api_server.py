

import os
import re
import datetime
import time
from typing import List
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from sqlalchemy import func
from database import SessionLocal, ChatHistory
from datetime import date


from fastapi.middleware.cors import CORSMiddleware

from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from crawler_1947 import get_dankook_menu

from langchain_classic.retrievers import EnsembleRetriever

from collections import defaultdict
import datetime

from loguru import logger

# rotation="00:00": 매일 자정에 새로운 로그 파일 생성
# retention="7 days": 7일이 지난 로그 파일은 자동 삭제
logger.add("logs/danbi_chat_{time:YYYY-MM-DD}.log", rotation="00:00", retention="7 days", level="INFO")

load_dotenv()
DB_PATH = "./chroma_db_dd2"

app = FastAPI(title="단국대 AI 서버")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 테스트 단계에서만 전체 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    query: str
    history: str = ""  
    user_id: str = "default_user"  # 카카오톡 유저 식별자를 받기 위해 추가


print(" 서버  로딩 중...")
llm = ChatGoogleGenerativeAI(model="models/gemini-flash-latest", temperature=0)
embedding_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embedding_model, collection_name="campus_rules")

try:
    data = vectorstore.get()
    docs = [Document(page_content=t, metadata=m or {}) for t, m in zip(data['documents'], data['metadatas'])]
    
    def clean_tokenizer(text: str) -> List[str]:
        return re.sub(r"[^가-힣a-zA-Z0-9]", " ", text).split()
        
    bm25_retriever = BM25Retriever.from_documents(docs, preprocess_func=clean_tokenizer)
    bm25_retriever.k = 3
    print(" AI  로딩 완료!")
except Exception as e:
    print(f" DB 로딩 에러: {e}")


def classify_intent(query: str, llm) -> str:
    q_clean = query.replace(" ", "")
    menu_keywords = ["학식", "학생식당", "학생 식당"]
    if any(k in q_clean for k in menu_keywords): return "menu"

    notice_keywords = ["[공지]"]
    if any(k in q_clean for k in notice_keywords):
        return "notice" 
    """    
    prompt = f"질문 '{query}'의 의도를 분석하여 다음 중 하나를 단어만(영어) 출력하세요:\n1. rule\n2. general\n답변:"
    try:
        res = llm.invoke(prompt)
        tag = res.content.strip().lower()
        if "rule" in tag: return "rule"
        return "general"
    except: return "general"
    """
    return "general"

def generate_answer(llm, context: str, query: str, history: str) -> str:
    prompt_template = PromptTemplate.from_template("""
    당신은 **단국대학교 죽전캠퍼스**의 AI 비서입니다.
    아래 [핵심 원칙]과 [답변 가이드]를 따르세요.                                  
    
    [핵심 원칙]
    1. **기본 가정:** 사용자가 질문에서 캠퍼스(죽전/천안)를 명시하지 않았다면 무조건 '죽전캠퍼스'로 간주하세요.
    2. **천안 식별:** [참고 정보]에 '충남' 또는 '천안' 명시 시에만 천안으로 판단하세요.
    3. 내부 기준 숨기기 : 제공된 정보의 [Level 1] ~ [Level 6] 같은 표기는 당신이 건물의 상대적 위치를 파악하기 위한 내부 좌표일 뿐입니다. 실제 답변을 작성할 때는 "Level 4에 위치해 있습니다"라는 말을 쓰지 말고, "상단부에 있습니다", "어느 건물 위쪽에 있습니다" 등 자연스러운 일상 용어로 번역해서 설명하세요.                                              
    
    [이전 대화 기록]
    {history}

    [참고 정보]
    {context}

    질문: {question}
    답변:
    """)
    final_prompt = prompt_template.format(context=context, question=query, history=history)
    response = llm.invoke(final_prompt)
    content = getattr(response, 'content', str(response))
    if isinstance(content, list): 
        return "".join([x.get('text', '') for x in content if isinstance(x, dict)])
    return str(content)


@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    query = request.query
    history = request.history
    user_id = request.user_id #



    total_start_time = time.time()

    step1_start = time.time()
    category = classify_intent(query, llm)
    step1_time = time.time() - step1_start
    
    context_text = ""
    source_info = ""


    step2_start = time.time()
    if category == "menu":
        try:
            crawled_data = get_dankook_menu()
            context_text = f"[오늘 날짜: {datetime.date.today()}]\n\n{crawled_data}"
        except:
            context_text = "식단 정보를 가져오는데 실패했습니다."
    elif category == "notice":
            print("    실시간으로 최신 공지사항을 가져오는 중...")
            try:
                
                from crawler_notice import get_latest_notice
                
                
                department = "학사공지" # 기본값
                if "모바일시스템공학과" in query or "모시공" in query:
                    department = "모바일시스템공학과"
                elif "SW행사" in query or "소융대행사" in query:
                    department = "SW중심대학사업단"
                 
                
                crawled_data = get_latest_notice(department)
                context_text = f"[실시간 {department} 최신 공지사항]\n\n{crawled_data}"
                source_info = f"{department} 게시판 실시간 검색"
                
            except Exception as e:
                context_text = "공지사항을 가져오는데 실패했습니다."
                print(f"❌ 크롤링 에러: {e}")
    else:
        if category == "general":
            retriever = EnsembleRetriever(
                retrievers=[bm25_retriever, vectorstore.as_retriever(search_kwargs={"k": 3})],
                weights=[0.7, 0.3]
        )

        else:
            retriever = vectorstore.as_retriever(search_kwargs={"k": 3, "filter": {"category": category}})
        
        found_docs = retriever.invoke(query)
        context_entries = []
        for doc in found_docs:
            src = doc.metadata.get("출처", "Unknown")

            other_metadata = {k: v for k, v in doc.metadata.items() if k != "출처"}
            meta_str = ", ".join([f"{k}: {v}" for k, v in other_metadata.items()])

            content = doc.page_content.replace("\n", " ")
            if meta_str:
                entry = f"📄 [파일명: {src} | 메타정보: {meta_str}]\n내용: {content}"
            else:
                entry = f"📄 [파일명: {src}]\n내용: {content}"

            context_entries.append(entry)
        context_text = "\n\n---\n\n".join(context_entries)
    step2_time = time.time() - step2_start

   
    step3_start = time.time()
    answer = generate_answer(llm, context_text, query, history)
    step3_time = time.time() - step3_start
    
    
    total_time = time.time() - total_start_time

    
    print("\n" + "="*50)
    print(f" 사용자 질문: {query}")
    print(f" 라우터가 판단한 의도(Category): [{category.upper()}]")
    
    print("📚 [검색된 문서 출처]")
    if category == "menu" or category == "notice":
        print(" └─ 🌐 (실시간 크롤링) 식단 데이터")
    else:
        
        if not found_docs:
            print(" └─ ⚠️ 검색된 문서가 없습니다.")
        else:
            for i, doc in enumerate(found_docs):
                src = doc.metadata.get("출처", "Unknown")
                print(f" └─ 📄 {i+1}순위 문서: {src}")
    print("\n" + "="*50)
    print(f"🙋 사용자 질문: {query}")
    print(f"⏱️ [성능 측정 리포트] 총 소요 시간: {total_time:.2f}초")
    print(f" ├─ 1. 의도 파악 (LLM) : {step1_time:.2f}초")
    print(f" ├─ 2. DB 검색/크롤링  : {step2_time:.2f}초")
    print(f" └─ 3. 답변 생성 (LLM) : {step3_time:.2f}초")
    print("="*50 + "\n")


    db = SessionLocal()
    try:
        new_log = ChatHistory(
            user_id=user_id, 
            query=query,
            answer=answer,
            category=category,

            retrieved_context=context_text,         # 검색된 문서 내용 또는 크롤링 텍스트
            step1_time=round(step1_time, 2),        # 의도 파악 시간 (소수점 2자리)
            step2_time=round(step2_time, 2),        # 검색/크롤링 시간
            step3_time=round(step3_time, 2),        # 답변 생성 시간
            total_time=round(total_time, 2)         # 전체 수행 시간
        )
        db.add(new_log)
        db.commit()
    finally:
        db.close()

    return {
        "answer": answer,
        "category": category 
    }

from fastapi import Request, BackgroundTasks
#import requests
import httpx
import asyncio

async def process_and_send_callback(user_message: str, callback_url: str , user_id: str):
    try:
        request_data = ChatRequest(query=user_message, history="", user_id=user_id)
        response_data = await asyncio.to_thread(chat_endpoint, request_data)
        answer = response_data.get("answer", "답변을 생성하지 못했습니다.")

        payload = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": answer
                        }
                    }
                ]
            }
        }


        async with httpx.AsyncClient() as client:
            await client.post(callback_url, json=payload)

        logger.info(f"카카오 콜백 비동기 전송 성공 - User ID: {user_id}")
        
    except Exception as e:
        logger.info(f"카카오 콜백 비동기 전송 성공 - User ID: {user_id}")
        error_payload = {
            "version": "2.0",
            "template": {"outputs": [{"simpleText": {"text": "서버 내부 오류가 발생했습니다."}}]}
        }
        async with httpx.AsyncClient() as client:
            await client.post(callback_url, json=error_payload)




DAILY_LIMIT = 3
@app.post("/api/kakao")
async def kakao_chat(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
        
        user_message = body["userRequest"]["utterance"]
        user_id = body["userRequest"]["user"]["id"] 
        
        # 1. DB 세션을 열어 오늘 날짜 기준으로 해당 유저의 질문 횟수를 카운트
        db = SessionLocal()
        try:
            today = date.today()
            daily_count = db.query(ChatHistory).filter(
                ChatHistory.user_id == user_id,
                func.date(ChatHistory.created_at) == today 
            ).count()
        finally:
            db.close()

        # 2. 제한 횟수를 초과했는지 검사
        if daily_count >= DAILY_LIMIT:
            return {
                "version": "2.0",
                "template": {
                    "outputs": [
                        {
                            "simpleText": {
                                "text": f"하루 질문 한도 {DAILY_LIMIT}회 초과\n내일 다시 찾아와주세요!"
                            }
                        }
                    ]
                }
            }        

        # 3. 통과했다면 콜백 처리를 진행
        callback_url = body["userRequest"].get("callbackUrl")
        
        if callback_url:
            background_tasks.add_task(process_and_send_callback, user_message, callback_url, user_id)
            return {"useCallback": True}
            
        else:
            return {
                "version": "2.0",
                "template": {
                    "outputs": [{"simpleText": {"text": "콜백 URL 에러 "}}]
                }
            }

    except Exception as e:
        logger.error(f"❌ 카카오 API 수신 에러: {e}")
        return {"useCallback": False}
