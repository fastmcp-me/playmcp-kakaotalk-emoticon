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
        "description": "카카오톡 이모티콘 제작 자동화 MCP 서버. 이모티콘 계획, 제작, 검증을 자동으로 수행합니다.",
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
                "name": "before_preview_tool",
                "description": "이모티콘 제작 이전 프리뷰. 카카오톡 채팅방과 같은 디자인의 페이지에서 제작할 이모티콘의 계획을 테스트 해 볼 수 있습니다."
            },
            {
                "name": "generate_tool",
                "description": "이모티콘 생성. 캐릭터 이미지와 이모티콘 설명을 기반으로 AI가 이모티콘을 생성합니다."
            },
            {
                "name": "after_preview_tool",
                "description": "완성본 프리뷰. 완성된 이모티콘을 카카오톡 채팅방과 같은 디자인의 페이지에서 테스트 해 볼 수 있습니다."
            },
            {
                "name": "check_tool",
                "description": "이모티콘 사양 검사. 이모티콘이 카카오톡 제출 규격에 맞는지 검사합니다."
            },
            {
                "name": "get_specs_tool",
                "description": "이모티콘 사양 정보 조회. 각 이모티콘 타입별 제출 규격 정보를 반환합니다."
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
        description="이모티콘 제작 이전 프리뷰. 카카오톡 채팅방과 같은 디자인의 페이지에서 "
                    "이모티콘 탭 부분에 이모티콘 설명이 글자로 표시되는 프리뷰 페이지 URL을 반환합니다. "
                    "이모티콘 기획/계획 단계에서 사용합니다."
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
        description="이모티콘 생성. 캐릭터 이미지와 이모티콘 설명을 기반으로 AI가 이모티콘을 생성합니다. "
                    "캐릭터 이미지가 없으면 자동으로 생성합니다. "
                    "움직이는 이모티콘은 비디오 생성 후 애니메이션 WebP로 변환됩니다. "
                    "허깅페이스 토큰이 필요합니다."
    )
    async def generate_tool(
        emoticon_type: str,
        emoticons: List[dict],
        character_image: Optional[str] = None,
        hf_token: Optional[str] = None
    ) -> dict:
        from src.models import GenerateRequest, EmoticonGenerateItem
        from src.tools import generate
        
        request = GenerateRequest(
            emoticon_type=emoticon_type,
            character_image=character_image,
            emoticons=[EmoticonGenerateItem(**e) for e in emoticons]
        )
        
        response = await generate(request, hf_token)
        return response.model_dump()

    @mcp.tool(
        description="완성본 프리뷰. 실제 이모티콘 이미지가 포함된 카카오톡 스타일 프리뷰 페이지를 생성합니다. "
                    "상단에 ZIP 다운로드 버튼이 있으며, 이모티콘을 클릭하면 확대해서 볼 수 있습니다."
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
        description="이모티콘 사양 검사. 이모티콘이 카카오톡 제출 규격에 맞는지 검사합니다. "
                    "파일 형식, 이미지 크기, 파일 용량, 개수 등을 확인합니다."
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
        description="이모티콘 사양 정보 조회. 각 이모티콘 타입별 제출 규격 정보를 반환합니다."
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
        instructions="카카오톡 이모티콘 제작 자동화 MCP 서버. "
                     "이모티콘 기획 프리뷰, AI 이미지 생성, 완성본 프리뷰, 사양 검사 기능을 제공합니다."
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
