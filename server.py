"""
카카오 이모티콘 PlayMCP 서버

카카오톡 이모티콘 제작을 자동화하거나 제작에 도움을 주기 위한 MCP 서버입니다.
PlayMCP에서 호스팅되며, 허깅페이스 계정 연동을 통해 이미지 생성 API를 사용합니다.
"""
import os
from typing import List, Optional, Annotated

# FastAPI 관련 임포트만 최상위에 유지 (빠른 헬스체크를 위해)
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import Field


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
    from src.mcp_tools_schema import get_mcp_tools_list, MCP_PROTOCOL_VERSION, MCP_SERVER_INSTRUCTIONS
    
    return {
        "version": "1.0",
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "serverInfo": {
            "name": "kakao-emoticon-mcp",
            "title": "카카오 이모티콘 MCP 서버",
            "version": "1.0.0"
        },
        "description": "카카오톡 이모티콘 제작 자동화 MCP 서버. 사용자가 '이모티콘', '스티커', '카카오톡'을 언급하면 AI가 자동으로 도구를 사용합니다.",
        "instructions": MCP_SERVER_INSTRUCTIONS,
        "transports": [
            {
                "type": "streamable-http",
                "endpoint": "/"
            }
        ],
        "transport": {
            "type": "streamable-http",
            "endpoint": "/"
        },
        "capabilities": {
            "tools": {"listChanged": False},
            "resources": {},
            "prompts": {}
        },
        "tools": get_mcp_tools_list()
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
            "download": "/download/{download_id}",
            "image": "/image/{image_id}"
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


@app.get("/image/{image_id}")
async def get_image(image_id: str):
    """저장된 이미지 반환"""
    from src.preview_generator import get_preview_generator
    
    generator = get_preview_generator(os.environ.get("BASE_URL", ""))
    image_info = generator.get_image(image_id)
    if image_info:
        return Response(
            content=image_info["data"],
            media_type=image_info["mime_type"]
        )
    return Response(content="Image not found", status_code=404)


# ===== MCP 도구 등록 함수 (MCP 초기화 전에 정의되어야 함) =====
def _register_tools(mcp):
    """MCP 도구들을 등록"""
    from src.constants import EmoticonType, FileType, FileExtension
    from src.models import EmoticonPlan, EmoticonGenerateItem, EmoticonImage, CheckEmoticonItem
    
    @mcp.tool(
        description="[2단계] 제작 전 프리뷰 생성. 트리거: get_specs_tool 호출 후 사용자가 캐릭터/분위기를 알려주면 호출. AI가 타입별 개수(16~42개)만큼 이모티콘 설명을 직접 창작합니다."
    )
    async def before_preview_tool(
        emoticon_type: Annotated[EmoticonType, Field(description="이모티콘 타입: static(멈춰있는, 32개), dynamic(움직이는, 24개), big(큰, 16개), static-mini(멈춰있는 미니, 42개), dynamic-mini(움직이는 미니, 35개)")],
        title: Annotated[str, Field(description="이모티콘 세트 제목 (예: '귀여운 고양이 이모티콘')")],
        plans: Annotated[List[EmoticonPlan], Field(description="각 이모티콘 기획 목록. AI가 타입별 개수만큼 직접 창작. 각 항목은 description(설명)과 file_type(PNG/WebP) 포함")]
    ) -> dict:
        """제작 전 프리뷰를 생성합니다. 카카오톡 채팅방 스타일로 이모티콘 기획을 미리보기합니다."""
        from src.models import BeforePreviewRequest
        from src.tools import before_preview
        
        request = BeforePreviewRequest(
            emoticon_type=emoticon_type,
            title=title,
            plans=plans
        )
        
        response = await before_preview(request)
        return response.model_dump()

    @mcp.tool(
        description="[3단계] AI 이모티콘 이미지 생성. 트리거: before_preview_tool 호출 후 자동으로 호출. 캐릭터 이미지 없으면 AI가 자동 생성합니다."
    )
    async def generate_tool(
        emoticon_type: Annotated[EmoticonType, Field(description="이모티콘 타입: static(멈춰있는, 32개), dynamic(움직이는, 24개), big(큰, 16개), static-mini(멈춰있는 미니, 42개), dynamic-mini(움직이는 미니, 35개)")],
        emoticons: Annotated[List[EmoticonGenerateItem], Field(description="생성할 이모티콘 목록. 각 항목은 description(상황/표정 설명)과 file_extension(png/webp) 포함")],
        character_image: Annotated[Optional[str], Field(description="캐릭터 참조 이미지 (Base64 또는 URL). 생략 시 AI가 자동 생성")] = None,
        hf_token: Annotated[Optional[str], Field(description="Hugging Face API 토큰. Authorization 헤더로도 전달 가능")] = None
    ) -> dict:
        """AI를 사용하여 이모티콘 이미지를 생성합니다."""
        from src.models import GenerateRequest
        from src.tools import generate
        
        # Authorization 헤더에서 토큰 추출 시도, 없으면 파라미터 사용
        # 우선순위: Authorization 헤더 > hf_token 파라미터
        token = _extract_hf_token_from_headers() or hf_token
        
        # 토큰이 없으면 에러 반환
        if not token:
            return {
                "error": "Hugging Face 토큰이 필요합니다.",
                "message": "Authorization 헤더(Bearer 토큰) 또는 hf_token 파라미터로 토큰을 전달해주세요.",
                "token_url": "https://huggingface.co/settings/tokens"
            }
        
        request = GenerateRequest(
            emoticon_type=emoticon_type,
            character_image=character_image,
            emoticons=emoticons
        )
        
        response = await generate(request, token)
        return response.model_dump()

    @mcp.tool(
        description="[4단계] 완성본 프리뷰 생성. 트리거: generate_tool 호출 후 자동으로 호출. 카카오톡 스타일 프리뷰와 ZIP 다운로드 URL을 제공합니다."
    )
    async def after_preview_tool(
        emoticon_type: Annotated[EmoticonType, Field(description="이모티콘 타입: static, dynamic, big, static-mini, dynamic-mini")],
        title: Annotated[str, Field(description="이모티콘 세트 제목")],
        emoticons: Annotated[List[EmoticonImage], Field(description="이모티콘 이미지 목록. 각 항목은 image_data(Base64 또는 URL) 포함")],
        icon: Annotated[Optional[str], Field(description="아이콘 이미지 (Base64 또는 URL)")] = None
    ) -> dict:
        """완성된 이모티콘의 프리뷰를 생성하고 ZIP 다운로드 URL을 제공합니다."""
        from src.models import AfterPreviewRequest
        from src.tools import after_preview
        
        request = AfterPreviewRequest(
            emoticon_type=emoticon_type,
            title=title,
            emoticons=emoticons,
            icon=icon
        )
        
        response = await after_preview(request)
        return response.model_dump()

    @mcp.tool(
        description="[5단계] 카카오톡 규격 검사. 트리거: after_preview_tool 호출 후 자동으로 호출하여 제출 규격 검증. 문제 발견 시 사용자에게 안내."
    )
    async def check_tool(
        emoticon_type: Annotated[EmoticonType, Field(description="검증할 이모티콘 타입: static, dynamic, big, static-mini, dynamic-mini")],
        emoticons: Annotated[List[CheckEmoticonItem], Field(description="검사할 이모티콘 목록. 각 항목은 file_data(Base64 인코딩) 포함")],
        icon: Annotated[Optional[CheckEmoticonItem], Field(description="검사할 아이콘 이미지 (선택사항)")] = None
    ) -> dict:
        """이모티콘이 카카오톡 제출 규격에 맞는지 검사합니다."""
        from src.models import CheckRequest
        from src.tools import check
        
        request = CheckRequest(
            emoticon_type=emoticon_type,
            emoticons=emoticons,
            icon=icon
        )
        
        response = await check(request)
        return response.model_dump()

    @mcp.tool(
        description="[1단계] 카카오톡 이모티콘 사양 조회. 트리거: 사용자가 '이모티콘', '스티커', '카카오톡' 등을 언급하면 즉시 이 도구부터 호출하세요. 타입별 개수, 파일 형식, 크기 제한을 반환합니다."
    )
    async def get_specs_tool(
        emoticon_type: Annotated[Optional[EmoticonType], Field(description="조회할 이모티콘 타입: static(멈춰있는), dynamic(움직이는), big(큰), static-mini(멈춰있는 미니), dynamic-mini(움직이는 미니). 생략 시 모든 타입 반환")] = None
    ) -> dict:
        """카카오톡 이모티콘 사양(타입별 개수, 파일 형식, 크기 제한)을 조회합니다."""
        from src.constants import EMOTICON_SPECS, EMOTICON_TYPE_NAMES
        
        if emoticon_type:
            spec = EMOTICON_SPECS.get(emoticon_type)
            if spec:
                return {
                    "type": spec.type.value,
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
            all_specs[etype.value] = {
                "type": spec.type.value,
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
    from src.mcp_tools_schema import MCP_SERVER_INSTRUCTIONS
    
    _mcp = FastMCP(
        name="kakao-emoticon-mcp",
        instructions=MCP_SERVER_INSTRUCTIONS
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
        
        # Streamable HTTP transport 생성
        # Streamable HTTP는 하나의 엔드포인트에서 GET(SSE 스트림)과 POST(JSON-RPC)를 모두 처리
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

# Streamable HTTP transport를 루트에 마운트
# Streamable HTTP는 하나의 엔드포인트에서 GET(SSE 스트림)과 POST(JSON-RPC)를 모두 처리함
# FastAPI의 명시적 라우트(/health, /.well-known/mcp 등)는 마운트된 앱보다 우선 처리됨
if _mcp_app is not None:
    app.mount("/", _mcp_app)
    print(f"MCP server initialized - {_mcp_transport_type} endpoint available at /")
else:
    print("MCP app not available - server running without MCP support")


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    uvicorn.run(app, host=host, port=port)
