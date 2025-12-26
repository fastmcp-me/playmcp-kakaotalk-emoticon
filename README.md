# 카카오 이모티콘 PlayMCP 서버

카카오톡 이모티콘 제작을 자동화하거나 제작에 도움을 주기 위한 MCP (Model Context Protocol) 서버입니다.

## 기능

### 1. before-preview (이모티콘 기획 프리뷰)
- 이모티콘 제작 전 기획 단계에서 사용
- 카카오톡 채팅방 스타일의 프리뷰 페이지 생성
- 각 이모티콘 위치에 설명 텍스트 표시

### 2. generate (이모티콘 생성)
- Hugging Face API를 사용한 AI 이모티콘 생성
- 캐릭터 이미지 기반 이모티콘 제작
- 캐릭터 이미지가 없으면 자동 생성
- 움직이는 이모티콘은 비디오 생성 후 WebP 변환

### 3. after-preview (완성본 프리뷰)
- 실제 이모티콘 이미지가 포함된 프리뷰 페이지
- ZIP 파일 다운로드 기능
- 이모티콘 클릭 시 확대 보기

### 4. check (이모티콘 검사)
- 카카오톡 이모티콘 제출 규격 검사
- 파일 형식, 크기, 용량, 개수 검증

## 이모티콘 사양

### 멈춰있는 이모티콘 (static)
| 항목 | 사양 |
|------|------|
| 이모티콘 이미지 | 32개, PNG, 360×360px, 150KB |
| 아이콘 이미지 | 1개, PNG, 78×78px, 16KB |

### 움직이는 이모티콘 (dynamic)
| 항목 | 사양 |
|------|------|
| 이모티콘 이미지 | 24개, WebP, 360×360px, 650KB |
| 아이콘 이미지 | 1개, PNG, 78×78px, 16KB |

### 큰 이모티콘 (big)
| 항목 | 사양 |
|------|------|
| 이모티콘 이미지 | 16개, WebP, 540×540px / 300×540px / 540×300px, 1MB |
| 아이콘 이미지 | 1개, PNG, 78×78px, 16KB |

### 멈춰있는 미니 이모티콘 (static-mini)
| 항목 | 사양 |
|------|------|
| 이모티콘 이미지 | 42개, PNG, 180×180px, 100KB |

### 움직이는 미니 이모티콘 (dynamic-mini)
| 항목 | 사양 |
|------|------|
| 이모티콘 이미지 | 35개, WebP, 180×180px, 500KB |

## 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정
```bash
# Hugging Face API 토큰 (필수)
export HF_TOKEN="your_huggingface_token"

# 서버 설정 (선택)
export HOST="0.0.0.0"
export PORT="8000"
export BASE_URL="https://your-server-url.com"
```

### 3. 서버 실행
```bash
python server.py
```

또는

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

## Railway 배포

### 1. Railway 프로젝트 생성
1. [Railway](https://railway.app)에 로그인
2. "New Project" 클릭
3. "Deploy from GitHub repo" 선택
4. 이 레포지토리 선택

### 2. 환경 변수 설정
Railway 대시보드에서 Variables 탭에 다음 환경변수 추가:

| 변수명 | 설명 | 필수 |
|---------|------|------|
| `HF_TOKEN` | Hugging Face API 토큰 | ✅ |
| `BASE_URL` | 배포된 서버 URL (Railway가 자동 생성) | ❌ |

> **참고**: `PORT`는 Railway가 자동으로 설정합니다.

### 3. 배포 확인
- Railway가 자동으로 빌드 및 배포
- 제공된 URL로 접속하여 확인: `playmcp-kakaotalk-emoticon.bloupla.net/health`

### 4. PlayMCP 등록
배포 후 MCP 엔드포인트 URL을 PlayMCP에 등록:
```
playmcp-kakaotalk-emoticon.bloupla.net/mcp
```

## PlayMCP 등록

1. [PlayMCP](https://playmcp.kakao.com)에 카카오 계정으로 로그인
2. MCP 서버 등록 메뉴에서 서버 URL 입력
3. 허깅페이스 계정 연동 설정
4. 테스트 후 공개 전환

## API 사용 예시

### before-preview
```json
{
  "emoticon_type": "static",
  "title": "귀여운 고양이",
  "plans": [
    {"description": "인사하는 고양이", "file_type": "PNG"},
    {"description": "졸린 고양이", "file_type": "PNG"}
  ]
}
```

### generate
```json
{
  "emoticon_type": "static",
  "character_image": "data:image/png;base64,...",
  "emoticons": [
    {"description": "고양이가 손을 흔들며 인사하는 모습", "file_extension": "png"},
    {"description": "고양이가 눈을 감고 졸고 있는 모습", "file_extension": "png"}
  ]
}
```

### after-preview
```json
{
  "emoticon_type": "static",
  "title": "귀여운 고양이",
  "emoticons": [
    {"image_data": "data:image/png;base64,..."},
    {"image_data": "data:image/png;base64,..."}
  ],
  "icon": "data:image/png;base64,..."
}
```

### check
```json
{
  "emoticon_type": "static",
  "emoticons": [
    {"file_data": "base64...", "filename": "emoticon_01.png"}
  ],
  "icon": {"file_data": "base64...", "filename": "icon.png"}
}
```

## 사용 모델

- **이미지 편집**: Qwen/Qwen-Image-Edit
- **비디오 생성**: Wan-AI/Wan2.1-I2V-14B-480P
- **캐릭터 생성**: black-forest-labs/FLUX.1-schnell

## 라이선스

MIT License
