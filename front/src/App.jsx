import { useState } from 'react';
// 챗봇 UI 기본 CSS 스타일 불러오기
import '@chatscope/chat-ui-kit-styles/dist/default/styles.min.css';
import {
  MainContainer,
  ChatContainer,
  MessageList,
  Message,
  MessageInput,
  TypingIndicator
} from '@chatscope/chat-ui-kit-react';

function App() {
  // 채팅 기록을 관리하는 State
  const [messages, setMessages] = useState([
    {
      message: "안녕하세요! 단국대학교 AI 어시스턴트입니다. 무엇을 도와드릴까요?",
      sender: "Danbi",
      direction: "incoming" // incoming: 상대방(단비), outgoing: 나(유저)
    }
  ]);
  
  // 단비가 답변을 생성 중인지 확인하는 State (타이핑 애니메이션 용도)
  const [isTyping, setIsTyping] = useState(false);

  // 전송 버튼을 눌렀을 때 실행되는 함수
  const handleSend = async (message) => {
    // 1. 사용자가 보낸 질문을 화면에 즉시 추가
    const newMessage = { message, sender: "user", direction: "outgoing" };
    const newMessages = [...messages, newMessage];
    setMessages(newMessages);
    
    // 2. 타이핑 인디케이터 켜기
    setIsTyping(true);

    try {
      // 3. FastAPI 백엔드 서버로 요청 보내기 (URL과 바디 구조는 백엔드에 맞게 수정)
      const response = await fetch("https://danbiv2-production.up.railway.app/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: message }) 
      });

      const data = await response.json();

      // 4. FastAPI에서 받은 단비의 답변을 화면에 추가
      setMessages([...newMessages, {
        message: data.answer, // 실제 FastAPI 응답 JSON의 Key값(answer 등)으로 변경
        sender: "Danbi",
        direction: "incoming"
      }]);

    } catch (error) {
      console.error("API 통신 에러:", error);
      setMessages([...newMessages, {
        message: "서버와 연결할 수 없습니다. 잠시 후 다시 시도해주세요.",
        sender: "Danbi",
        direction: "incoming"
      }]);
    } finally {
      // 5. 통신이 끝나면 타이핑 인디케이터 끄기
      setIsTyping(false);
    }
  };

  // 모바일 화면(최대 500px)에 맞춘 UI 렌더링
  return (
    <div style={{ position: "relative", height: "100vh", maxWidth: "500px", margin: "0 auto" }}>
      <MainContainer>
        <ChatContainer>
          
          <MessageList
            typingIndicator={isTyping ? <TypingIndicator content=" 로딩 중..." /> : null}
          >
            {messages.map((msg, i) => (
              <Message key={i} model={msg} />
            ))}
          </MessageList>

          <MessageInput 
            placeholder="AI에게 질문해 보세요!" 
            onSend={handleSend} 
            attachButton={false} // 파일 첨부 버튼 숨김
          />
          
        </ChatContainer>
      </MainContainer>
    </div>
  );
}

export default App;
