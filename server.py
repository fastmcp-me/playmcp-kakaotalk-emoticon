"""
카카오 이모티콘 PlayMCP 서버

카카오톡 이모티콘 제작을 자동화하거나 제작에 도움을 주기 위한 MCP 서버입니다.
PlayMCP에서 호스팅되며, 허깅페이스 계정 연동을 통해 이미지 생성 API를 사용합니다.
"""
import os
from typing import List, Optional

# FastAPI 관련 임포트만 최상위에 유지 (빠른 헬스체크를 위해)
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware


# MCP 관련 전역 변수 (하단에서 초기화)
_mcp = None
_mcp_app = None
_mcp_transport_type = None


def _extract_hf_token_from_headers() -> Optional[str]:
    """
    HTTP 헤더에서 Hugging Face 토큰을 추출합니다.
    Authorization: Bearer <token> 형식을 지원합니다.
    
    Returns:
        추출된 토큰 또는 None
    """
    try:
        from fastmcp.server.dependencies import get_http_headers
        headers = get_http_headers()
        if headers:
            # case-insensitive 헤더 검색
            auth_header = None
            for key, value in headers.items():
                if key.lower() == "authorization":
                    auth_header = value
                    break
            
            if auth_header and auth_header.lower().startswith("bearer "):
                return auth_header[7:].strip()  # "Bearer " 이후의 토큰 부분 추출
    except Exception:
        # 헤더를 가져올 수 없는 경우 (예: HTTP 컨텍스트가 아닌 경우)
        pass
    return None

# FastAPI 앱 생성 (lifespan은 MCP 초기화 후 설정됨)
app = FastAPI(title="카카오 이모티콘 MCP 서버")

# CORS 설정 추가 (외부 MCP 클라이언트 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트 (Railway 배포용)"""
    return {"status": "healthy", "service": "kakao-emoticon-mcp"}


@app.get("/.well-known/mcp")
async def mcp_metadata():
    """MCP 서버 메타데이터 엔드포인트 (PlayMCP가 서버 정보를 불러올 때 사용)"""
    return {
        "version": "1.0",
        "protocolVersion": "2024-11-05",
        "serverInfo": {
            "name": "kakao-emoticon-mcp",
            "title": "카카오 이모티콘 MCP 서버",
            "version": "1.0.0"
        },
        "description": "카카오톡 이모티콘 제작 자동화 MCP 서버. 큰 방향(캐릭터, 분위기, 타입)만 물어보고 세부 기획(각 이모티콘의 설명)은 AI가 직접 창작합니다.",
        "transport": {
            "type": "streamable-http",
            "endpoint": "/"
        },
        "capabilities": {
            "tools": {"listChanged": False},
            "resources": {},
            "prompts": {}
        },
        "tools": [
            {
                "name": "get_specs_tool",
                "description": "이모티콘 사양 조회. 타입별 필요 개수, 파일 형식, 크기 등을 확인합니다."
            },
            {
                "name": "before_preview_tool",
                "description": "제작 전 프리뷰. 큰 방향(캐릭터, 분위기)만 묻고 개별 이모티콘 설명은 AI가 직접 창작합니다."
            },
            {
                "name": "generate_tool",
                "description": "AI 이모티콘 생성. 기획을 기반으로 실제 이미지를 생성합니다."
            },
            {
                "name": "after_preview_tool",
                "description": "완성본 프리뷰. 카카오톡 채팅 스타일로 결과물을 확인하고 다운로드할 수 있습니다."
            },
            {
                "name": "check_tool",
                "description": "규격 검사. 제출 전 카카오톡 규격에 맞는지 검증합니다."
            }
        ]
    }


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "name": "kakao-emoticon-mcp",
        "description": "카카오톡 이모티콘 제작 자동화 MCP 서버",
        "version": "1.0.0",
        "endpoints": {
            "mcp": "/",
            "health": "/health",
            "preview": "/preview/{preview_id}",
            "download": "/download/{download_id}"
        }
    }


@app.get("/preview/{preview_id}", response_class=HTMLResponse)
async def get_preview(preview_id: str):
    """프리뷰 페이지 반환"""
    from src.preview_generator import get_preview_generator
    
    generator = get_preview_generator(os.environ.get("BASE_URL", ""))
    html = generator.get_preview_html(preview_id)
    if html:
        return HTMLResponse(content=html)
    return HTMLResponse(content="Preview not found", status_code=404)


@app.get("/download/{download_id}")
async def get_download(download_id: str):
    """ZIP 파일 다운로드"""
    from src.preview_generator import get_preview_generator
    
    generator = get_preview_generator(os.environ.get("BASE_URL", ""))
    zip_bytes = generator.get_download_zip(download_id)
    if zip_bytes:
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=emoticons.zip"}
        )
    return Response(content="Download not found", status_code=404)


# ===== MCP 도구 등록 함수 (MCP 초기화 전에 정의되어야 함) =====
def _register_tools(mcp):
    """MCP 도구들을 등록"""
    
    @mcp.tool(
        description="""
제작 전 프리뷰 도구

목적: 실제 이미지 대신 텍스트 설명이 표시되는 카카오톡 스타일 채팅 프리뷰 페이지를 생성합니다.

⚠️ AI 행동 지침:
✅ 적절한 질문: "어떤 느낌의 이모티콘을 원하세요?", "어떤 타입으로 할까요?"
❌ 부적절한 질문: "이모티콘 하나하나 어떤 상황인지 다 알려주세요"

- 큰 방향(캐릭터, 분위기, 타입)만 물어보고
- 개별 이모티콘 설명(타입별 16~42개)은 AI가 직접 창작해야 합니다

워크플로우 위치: get_specs_tool 호출 후 가장 먼저 사용

요청 시 필요한 정보:
- emoticon_type (문자열, 필수): 이모티콘 타입
  - "static": 멈춰있는 이모티콘 (32개)
  - "dynamic": 움직이는 이모티콘 (24개)
  - "big": 큰 이모티콘 (16개)
  - "static-mini": 멈춰있는 미니 (42개)
  - "dynamic-mini": 움직이는 미니 (35개)
- title (문자열, 필수): 이모티콘 세트 제목
- plans (배열, 필수): 각 이모티콘 기획 목록 (AI가 직접 창작)
  - description (문자열): 이모티콘 설명 (예: "손 흔드는 고양이")
  - file_type (문자열): 파일 형식 ("PNG" 또는 "WebP")

반환값:
- preview_url: 텍스트 기반 프리뷰 페이지 URL
- total_count: 기획된 이모티콘 총 개수
- emoticon_type: 사용된 이모티콘 타입
- title: 이모티콘 세트 제목

예시:
사용자: "고양이 이모티콘 만들어줘"
AI: "어떤 느낌의 고양이로 할까요?" (적절) → "귀여운 고양이로 해주세요" → AI가 "하품하는 고양이", "화난 고양이" 등 타입에 맞는 개수만큼 직접 창작
"""
    )
    async def before_preview_tool(
        emoticon_type: str,
        title: str,
        plans: List[dict]
    ) -> dict:
        from src.models import BeforePreviewRequest, EmoticonPlan
        from src.tools import before_preview
        
        request = BeforePreviewRequest(
            emoticon_type=emoticon_type,
            title=title,
            plans=[EmoticonPlan(**p) for p in plans]
        )
        
        response = await before_preview(request)
        return response.model_dump()

    @mcp.tool(
        description="""
AI 이모티콘 생성기

목적: 캐릭터 참조 이미지와 설명을 기반으로 AI가 실제 이모티콘 이미지를 생성합니다.
이것이 이모티콘 이미지를 만드는 핵심 도구입니다.

⚠️ AI 행동 지침:
- 1단계에서 만든 기획을 그대로 사용하여 생성
- 캐릭터 이미지가 없으면 AI가 자동 생성 (사용자에게 요청 X)
- 생성 중간에 사용자 확인 불필요

워크플로우 위치: before_preview_tool 직후 사용

요청 시 필요한 정보:
- emoticon_type (문자열, 필수): 이모티콘 타입 (크기, 포맷, 애니메이션 결정)
- emoticons (배열, 필수): 생성할 이모티콘 목록
  - description (문자열): 이모티콘 상세 설명
  - file_extension (문자열): 파일 확장자 ("png" 또는 "webp")
- character_image (문자열, 선택): 캐릭터 참조 이미지 (Base64 또는 URL)
  - 생략하면 AI가 새 캐릭터를 자동 생성
- hf_token (문자열, 선택): Hugging Face API 토큰
  - Authorization 헤더(Bearer 토큰)로도 전달 가능

반환값:
- emoticons (배열): 생성된 이미지들
  - index: 이모티콘 번호
  - image_data: Base64 인코딩된 이미지 데이터
  - file_extension: 파일 확장자
  - width, height: 이미지 크기
  - size_kb: 파일 용량 (KB)
- icon: 자동 생성된 아이콘 (78x78 PNG)
- emoticon_type: 사용된 이모티콘 타입

동작 방식:
- 정적 이모티콘 (static, static-mini): PNG 이미지 생성
- 움직이는 이모티콘 (dynamic, dynamic-mini, big): 비디오 생성 → 애니메이션 WebP 변환
"""
    )
    async def generate_tool(
        emoticon_type: str,
        emoticons: List[dict],
        character_image: Optional[str] = None,
        hf_token: Optional[str] = None
    ) -> dict:
        from src.models import GenerateRequest, EmoticonGenerateItem
        from src.tools import generate
        
        # Authorization 헤더에서 토큰 추출 시도, 없으면 파라미터 사용
        # 우선순위: Authorization 헤더 > hf_token 파라미터 > 환경변수 HF_TOKEN
        token = _extract_hf_token_from_headers() or hf_token
        
        # 토큰이 없고 환경변수도 없으면 에러 반환
        if not token and not os.environ.get("HF_TOKEN"):
            return {
                "error": "Hugging Face 토큰이 필요합니다.",
                "message": "Authorization 헤더(Bearer 토큰) 또는 hf_token 파라미터로 토큰을 전달해주세요.",
                "token_url": "https://huggingface.co/settings/tokens"
            }
        
        request = GenerateRequest(
            emoticon_type=emoticon_type,
            character_image=character_image,
            emoticons=[EmoticonGenerateItem(**e) for e in emoticons]
        )
        
        response = await generate(request, token)
        return response.model_dump()

    @mcp.tool(
        description="""
완성본 프리뷰

목적: 실제 이모티콘 이미지가 포함된 카카오톡 스타일 채팅 프리뷰 페이지를 생성합니다.
사용자가 실제 채팅 환경에서 이모티콘이 어떻게 보이는지 확인하고 다운로드할 수 있습니다.

⚠️ AI 행동 지침:
- generate_tool 완료 후 자동으로 호출
- 프리뷰 URL과 다운로드 URL을 사용자에게 제공
- "마음에 드세요?" 같은 피드백 질문은 적절함

워크플로우 위치: generate_tool 직후 사용

요청 시 필요한 정보:
- emoticon_type (문자열, 필수): 이모티콘 타입
- title (문자열, 필수): 이모티콘 세트 제목
- emoticons (배열, 필수): 이모티콘 이미지 목록
  - image_data (문자열): Base64 인코딩 이미지 또는 URL
  - frames (배열, 선택): 움직이는 이모티콘의 프레임 이미지들
- icon (문자열, 선택): 아이콘 이미지 (Base64 또는 URL)

반환값:
- preview_url: 카카오톡 채팅 시뮬레이션에서 이모티콘 확인 URL
- download_url: 제출용 ZIP 파일 다운로드 URL
- emoticon_type: 이모티콘 타입
- title: 이모티콘 세트 제목
"""
    )
    async def after_preview_tool(
        emoticon_type: str,
        title: str,
        emoticons: List[dict],
        icon: Optional[str] = None
    ) -> dict:
        from src.models import AfterPreviewRequest, EmoticonImage
        from src.tools import after_preview
        
        request = AfterPreviewRequest(
            emoticon_type=emoticon_type,
            title=title,
            emoticons=[EmoticonImage(**e) for e in emoticons],
            icon=icon
        )
        
        response = await after_preview(request)
        return response.model_dump()

    @mcp.tool(
        description="""
카카오톡 규격 검사기

목적: 이모티콘이 카카오톡 공식 제출 규격에 맞는지 검증합니다.
제출 전 모든 기술 사양을 충족하는지 확인합니다.

⚠️ AI 행동 지침:
- 프리뷰 표시 후 자동으로 검증 실행
- 문제 발견 시 설명 후 수정 제안

워크플로우 위치: after_preview_tool 직후 마지막 단계

요청 시 필요한 정보:
- emoticon_type (문자열, 필수): 검증할 이모티콘 타입
- emoticons (배열, 필수): 검사할 이모티콘 목록
  - file_data (문자열): Base64 인코딩된 파일 데이터
  - filename (문자열, 선택): 파일명
- icon (객체, 선택): 검사할 아이콘 이미지
  - file_data (문자열): Base64 인코딩된 파일 데이터
  - filename (문자열, 선택): 파일명

반환값:
- is_valid (불리언): 모든 검사 통과 여부
- issues (배열): 발견된 문제 목록
  - index: 문제가 있는 이모티콘 번호 (-1: 아이콘, -2: 전체)
  - issue_type: 문제 유형 (size, format, dimension, count)
  - message: 사람이 읽을 수 있는 설명
  - current_value: 현재 값
  - expected_value: 기대 값
- checked_count: 검사한 이모티콘 개수
- emoticon_type: 검사한 이모티콘 타입

검증 항목:
- 파일 형식 (정적: PNG, 움직이는: WebP)
- 이미지 크기 (타입에 따라 360x360, 180x180, 540x540)
- 파일 용량 (타입에 따라 100KB~1MB)
- 이모티콘 개수 (타입에 따라 16~42개)
- 아이콘 규격 (78x78 PNG, 최대 16KB)
"""
    )
    async def check_tool(
        emoticon_type: str,
        emoticons: List[dict],
        icon: Optional[dict] = None
    ) -> dict:
        from src.models import CheckRequest, CheckEmoticonItem
        from src.tools import check
        
        request = CheckRequest(
            emoticon_type=emoticon_type,
            emoticons=[CheckEmoticonItem(**e) for e in emoticons],
            icon=CheckEmoticonItem(**icon) if icon else None
        )
        
        response = await check(request)
        return response.model_dump()

    @mcp.tool(
        description="""
카카오톡 이모티콘 사양 정보

목적: 카카오톡 공식 이모티콘 제출 사양을 조회합니다.
몇 개의 이모티콘을 만들어야 하는지, 어떤 포맷을 사용해야 하는지 먼저 확인하세요.

⚠️ AI 행동 지침:
- 기획 전에 사양 확인하여 개수와 포맷 파악
- 사용자에게 "어떤 타입으로 할까요?" 질문 가능 (적절한 질문)

워크플로우 위치: before_preview_tool 전에 가장 먼저 호출

요청 시 필요한 정보:
- emoticon_type (문자열, 선택): 조회할 특정 타입
  - 생략하면 모든 타입 정보 반환
  - "static": 멈춰있는 이모티콘
  - "dynamic": 움직이는 이모티콘
  - "big": 큰 이모티콘
  - "static-mini": 멈춰있는 미니 이모티콘
  - "dynamic-mini": 움직이는 미니 이모티콘

반환값 (각 타입별):
- type: 이모티콘 타입 식별자
- type_name: 한글 이름
- count: 필요한 이모티콘 개수
- format: 필요한 파일 형식 (PNG 또는 WebP)
- sizes: 허용 크기 [{width, height}]
- max_size_kb: 이모티콘당 최대 파일 크기
- icon_size: 아이콘 크기 (78x78)
- icon_max_size_kb: 아이콘 최대 크기 (16KB)
- is_animated: 애니메이션 지원 여부

이모티콘 타입 요약:
- static: 멈춰있는 이모티콘 (32개 PNG, 360x360, 최대 150KB)
- dynamic: 움직이는 이모티콘 (24개 WebP, 360x360, 최대 650KB)
- big: 큰 이모티콘 (16개 WebP, 최대 540x540, 최대 1MB)
- static-mini: 멈춰있는 미니 (42개 PNG, 180x180, 최대 100KB)
- dynamic-mini: 움직이는 미니 (35개 WebP, 180x180, 최대 500KB)
"""
    )
    async def get_specs_tool(
        emoticon_type: Optional[str] = None
    ) -> dict:
        from src.constants import EMOTICON_SPECS, EMOTICON_TYPE_NAMES
        
        if emoticon_type:
            spec = EMOTICON_SPECS.get(emoticon_type)
            if spec:
                return {
                    "type": spec.type,
                    "type_name": EMOTICON_TYPE_NAMES[spec.type],
                    "count": spec.count,
                    "format": spec.format,
                    "sizes": [{"width": w, "height": h} for w, h in spec.sizes],
                    "max_size_kb": spec.max_size_kb,
                    "icon_size": {"width": spec.icon_size[0], "height": spec.icon_size[1]},
                    "icon_max_size_kb": spec.icon_max_size_kb,
                    "is_animated": spec.is_animated
                }
            return {"error": f"Unknown emoticon type: {emoticon_type}"}
        
        all_specs = {}
        for etype, spec in EMOTICON_SPECS.items():
            all_specs[etype] = {
                "type": spec.type,
                "type_name": EMOTICON_TYPE_NAMES[spec.type],
                "count": spec.count,
                "format": spec.format,
                "sizes": [{"width": w, "height": h} for w, h in spec.sizes],
                "max_size_kb": spec.max_size_kb,
                "icon_size": {"width": spec.icon_size[0], "height": spec.icon_size[1]},
                "icon_max_size_kb": spec.icon_max_size_kb,
                "is_animated": spec.is_animated
            }
        return all_specs


# ===== MCP 초기화 함수들 =====
def _get_mcp():
    """MCP 서버 인스턴스를 지연 로딩으로 가져옴"""
    global _mcp
    
    if _mcp is not None:
        return _mcp
    
    from fastmcp import FastMCP
    
    _mcp = FastMCP(
        name="kakao-emoticon-mcp",
        instructions="""
카카오톡 이모티콘 제작 자동화 MCP 서버입니다.

✅ 적절한 질문 (큰 방향성 결정):
- 어떤 캐릭터/주제로 이모티콘을 만들지
- 어떤 감정/상황을 표현하고 싶은지
- 원하는 전체적인 느낌/분위기
- 결과물이 마음에 드는지
- 어떤 타입(멈춰있는/움직이는)으로 할지

❌ 부적절한 질문 (AI가 스스로 해야 함):
- 이모티콘 하나하나의 상황을 사용자에게 다 물어보기
- 캐릭터를 극단적으로 자세하게 묘사하라고 요구
- 세부적인 포즈나 표정 하나하나 물어보기
- 이모티콘 지식 없이 사용자에게 따지기

예시:
사용자: "고양이 이모티콘 만들어줘"
- ✅ "어떤 느낌의 고양이로 할까요? (귀여운/시크한/웃긴)" - 적절
- ❌ "이모티콘 하나하나 어떤 상황인지 다 알려주세요" - 부적절
- AI가 알아서 "하품하는 고양이", "화난 고양이" 등 타입에 맞는 개수를 창작해야 함
(타입별 개수: static 32개, dynamic 24개, big 16개, static-mini 42개, dynamic-mini 35개)

워크플로우:
1. get_specs_tool: 선택한 이모티콘 타입의 사양 확인
2. before_preview_tool: AI가 창의적인 설명으로 기획 생성 (세부 설명은 AI가 직접 창작)
3. generate_tool: AI 기획 기반으로 모든 이모티콘 생성
4. after_preview_tool: 최종 프리뷰 표시 및 다운로드 제공
5. check_tool: 제출 전 규격 검증

AI는 큰 방향만 사용자에게 묻고, 세부 기획은 스스로 창작해야 합니다.
"""
    )
    
    _register_tools(_mcp)
    
    return _mcp


def _init_mcp_app():
    """MCP 앱을 초기화하고 lifespan을 가져옴"""
    global _mcp_app, _mcp_transport_type, app
    
    try:
        import traceback
        print("Initializing MCP server...")
        mcp_instance = _get_mcp()
        print("MCP instance created, checking available app methods...")
        
        if hasattr(mcp_instance, 'streamable_http_app'):
            try:
                _mcp_app = mcp_instance.streamable_http_app(path='/')
            except TypeError:
                _mcp_app = mcp_instance.streamable_http_app()
            _mcp_transport_type = "Streamable HTTP"
        elif hasattr(mcp_instance, 'http_app'):
            try:
                _mcp_app = mcp_instance.http_app(path='/')
            except TypeError:
                _mcp_app = mcp_instance.http_app()
            _mcp_transport_type = "HTTP"
        elif hasattr(mcp_instance, 'sse_app'):
            _mcp_app = mcp_instance.sse_app()
            _mcp_transport_type = "SSE"
        else:
            raise AttributeError("FastMCP instance has no supported app method")
        
        print(f"MCP app created - {_mcp_transport_type} transport")
        
        # MCP 앱의 lifespan이 있으면 새 FastAPI 앱 생성
        if hasattr(_mcp_app, 'lifespan'):
            new_app = FastAPI(title="카카오 이모티콘 MCP 서버", lifespan=_mcp_app.lifespan)
            new_app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            # 기존 라우트 복사
            for route in app.routes:
                new_app.routes.append(route)
            app = new_app
            print("FastAPI app recreated with MCP lifespan")
        
        return True
    except Exception as e:
        print(f"Warning: MCP initialization failed: {e}")
        traceback.print_exc()
        print("Server will continue running without MCP support")
        return False


# MCP 초기화 실행 (_register_tools가 정의된 후에 실행)
_init_mcp_app()

# MCP 앱을 루트에 마운트 (모든 라우트 정의 후에 마운트해야 기존 엔드포인트가 우선됨)
if _mcp_app is not None:
    app.mount("/", _mcp_app)
    print(f"MCP server initialized - {_mcp_transport_type} endpoint available at root")
else:
    print("MCP app not available - server running without MCP support")


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    uvicorn.run(app, host=host, port=port)
