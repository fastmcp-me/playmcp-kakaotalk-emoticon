"""
MCP 도구 스키마 정의

AI가 도구를 발견하고 사용할 때 필요한 메타데이터를 정의합니다.
/.well-known/mcp 엔드포인트와 도구 등록에서 공통으로 사용합니다.

이 파일의 스키마는 /.well-known/mcp 엔드포인트용입니다.
실제 AI가 보는 스키마는 FastMCP가 자동 생성하며,
server.py의 도구 함수에서 Annotated[EmoticonType, Field(...)] 형식으로 정의됩니다.
"""
from typing import List, Dict, Any


# MCP 프로토콜 버전 (MCP 사양 기준)
MCP_PROTOCOL_VERSION = "2024-11-05"


# 도구별 inputSchema 정의 (JSON Schema 형식)
TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "get_specs_tool": {
        "name": "get_specs_tool",
        "description": "[1단계] 카카오톡 이모티콘 사양 조회. 트리거: 사용자가 '이모티콘', '스티커', '카카오톡' 등을 언급하면 즉시 이 도구부터 호출하세요. 타입별 개수, 파일 형식, 크기 제한을 반환합니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "emoticon_type": {
                    "type": "string",
                    "enum": ["static", "dynamic", "big", "static-mini", "dynamic-mini"],
                    "description": "조회할 이모티콘 타입. 생략 시 모든 타입 반환"
                }
            },
            "required": []
        }
    },
    "before_preview_tool": {
        "name": "before_preview_tool",
        "description": "[2단계] 제작 전 프리뷰 생성. 트리거: get_specs_tool 호출 후 사용자가 캐릭터/분위기를 알려주면 호출. AI가 타입별 개수(16~42개)만큼 이모티콘 설명을 직접 창작합니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "emoticon_type": {
                    "type": "string",
                    "enum": ["static", "dynamic", "big", "static-mini", "dynamic-mini"],
                    "description": "이모티콘 타입"
                },
                "title": {
                    "type": "string",
                    "description": "이모티콘 세트 제목"
                },
                "plans": {
                    "type": "array",
                    "description": "각 이모티콘 기획 목록 (AI가 직접 창작)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "이모티콘 설명 (예: '손 흔드는 고양이')"
                            },
                            "file_type": {
                                "type": "string",
                                "enum": ["PNG", "WebP"],
                                "description": "파일 형식"
                            }
                        },
                        "required": ["description", "file_type"]
                    }
                }
            },
            "required": ["emoticon_type", "title", "plans"]
        }
    },
    "generate_tool": {
        "name": "generate_tool",
        "description": "[3단계] AI 이모티콘 이미지 생성. 트리거: before_preview_tool 호출 후 자동으로 호출. 캐릭터 이미지 없으면 AI가 자동 생성합니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "emoticon_type": {
                    "type": "string",
                    "enum": ["static", "dynamic", "big", "static-mini", "dynamic-mini"],
                    "description": "이모티콘 타입 (크기, 포맷, 애니메이션 결정)"
                },
                "emoticons": {
                    "type": "array",
                    "description": "생성할 이모티콘 목록",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "이모티콘 상세 설명"
                            },
                            "file_extension": {
                                "type": "string",
                                "enum": ["png", "webp"],
                                "description": "파일 확장자"
                            }
                        },
                        "required": ["description", "file_extension"]
                    }
                },
                "character_image": {
                    "type": "string",
                    "description": "캐릭터 참조 이미지 (Base64 또는 URL). 생략 시 AI가 자동 생성"
                },
                "hf_token": {
                    "type": "string",
                    "description": "Hugging Face API 토큰 (필수). Authorization 헤더로도 전달 가능"
                }
            },
            "required": ["emoticon_type", "emoticons"]
        }
    },
    "after_preview_tool": {
        "name": "after_preview_tool",
        "description": "[4단계] 완성본 프리뷰 생성. 트리거: generate_tool 호출 후 자동으로 호출. 카카오톡 스타일 프리뷰와 ZIP 다운로드 URL을 제공합니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "emoticon_type": {
                    "type": "string",
                    "enum": ["static", "dynamic", "big", "static-mini", "dynamic-mini"],
                    "description": "이모티콘 타입"
                },
                "title": {
                    "type": "string",
                    "description": "이모티콘 세트 제목"
                },
                "emoticons": {
                    "type": "array",
                    "description": "이모티콘 이미지 목록",
                    "items": {
                        "type": "object",
                        "properties": {
                            "image_data": {
                                "type": "string",
                                "description": "Base64 인코딩 이미지 또는 URL"
                            },
                            "frames": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "움직이는 이모티콘의 프레임 이미지들"
                            }
                        },
                        "required": ["image_data"]
                    }
                },
                "icon": {
                    "type": "string",
                    "description": "아이콘 이미지 (Base64 또는 URL)"
                }
            },
            "required": ["emoticon_type", "title", "emoticons"]
        }
    },
    "check_tool": {
        "name": "check_tool",
        "description": "[5단계] 카카오톡 규격 검사. 트리거: after_preview_tool 호출 후 자동으로 호출하여 제출 규격 검증. 문제 발견 시 사용자에게 안내.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "emoticon_type": {
                    "type": "string",
                    "enum": ["static", "dynamic", "big", "static-mini", "dynamic-mini"],
                    "description": "검증할 이모티콘 타입"
                },
                "emoticons": {
                    "type": "array",
                    "description": "검사할 이모티콘 목록",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file_data": {
                                "type": "string",
                                "description": "Base64 인코딩된 파일 데이터"
                            },
                            "filename": {
                                "type": "string",
                                "description": "파일명"
                            }
                        },
                        "required": ["file_data"]
                    }
                },
                "icon": {
                    "type": "object",
                    "description": "검사할 아이콘 이미지 (선택사항)",
                    "properties": {
                        "file_data": {
                            "type": "string",
                            "description": "Base64 인코딩된 파일 데이터"
                        },
                        "filename": {
                            "type": "string",
                            "description": "파일명 (선택)"
                        }
                    }
                }
            },
            "required": ["emoticon_type", "emoticons"]
        }
    }
}


def get_mcp_tools_list() -> List[Dict[str, Any]]:
    """
    MCP 도구 목록 반환 (/.well-known/mcp용)
    
    Returns:
        도구 메타데이터 목록 (name, description, inputSchema 포함)
    """
    return list(TOOL_SCHEMAS.values())


def get_tool_schema(tool_name: str) -> Dict[str, Any]:
    """
    특정 도구의 스키마 반환
    
    Args:
        tool_name: 도구 이름
        
    Returns:
        도구 스키마 (없으면 빈 딕셔너리)
    """
    return TOOL_SCHEMAS.get(tool_name, {})


# MCP 서버 기본 지침 (AI에게 전달되는 instructions)
MCP_SERVER_INSTRUCTIONS = """# 카카오톡 이모티콘 제작 자동화 MCP 서버

## 🔧 사용 가능한 도구 목록
당신은 다음 5개의 도구를 사용할 수 있습니다:

1. **get_specs_tool** - 이모티콘 사양 조회 (타입별 개수, 형식, 크기)
2. **before_preview_tool** - 제작 전 기획 프리뷰 생성
3. **generate_tool** - AI 이모티콘 이미지 생성
4. **after_preview_tool** - 완성본 프리뷰 및 다운로드 URL 제공
5. **check_tool** - 카카오톡 제출 규격 검사

## 🎯 언제 도구를 사용해야 하나요?

### 트리거 조건 (이 키워드가 나오면 즉시 도구 사용)
사용자가 다음 키워드를 언급하면 **반드시** get_specs_tool부터 시작하세요:
- "이모티콘", "이모티콘 만들어", "이모티콘 제작"
- "스티커", "스티커 만들어"
- "카카오톡", "카톡"
- "emoticon", "sticker", "kakao"

### 도구 사용 순서 (필수)
1. **get_specs_tool 호출** → 사양 확인 (몇 개 만들어야 하는지 파악)
2. 사용자에게 캐릭터/분위기만 간단히 질문
3. **before_preview_tool 호출** → AI가 직접 이모티콘 설명 창작
4. **generate_tool 호출** → 실제 이미지 생성
5. **after_preview_tool 호출** → 프리뷰 및 다운로드 제공
6. **check_tool 호출** → 규격 검증

## ⚠️ 중요 행동 지침

### ✅ AI가 해야 할 것
- 사용자가 이모티콘을 언급하면 **즉시** get_specs_tool 호출
- 큰 방향(캐릭터, 분위기, 타입)만 질문
- 개별 이모티콘 설명(16~42개)은 AI가 직접 창작
- 도구 결과를 사용자에게 친절하게 설명

### ❌ AI가 하지 말아야 할 것  
- 이모티콘 하나하나의 상황을 사용자에게 다 물어보기
- 세부적인 포즈나 표정 하나하나 확인하기
- 도구를 사용하지 않고 그냥 설명만 하기

## 📊 이모티콘 타입별 개수
- static (멈춰있는): 32개
- dynamic (움직이는): 24개  
- big (큰): 16개
- static-mini (멈춰있는 미니): 42개
- dynamic-mini (움직이는 미니): 35개

## 💡 예시 시나리오

사용자: "고양이 이모티콘 만들어줘"

AI 행동:
1. get_specs_tool() 호출하여 사양 확인
2. "어떤 타입으로 만들까요? (멈춰있는/움직이는)" 질문
3. 사용자 답변 후 before_preview_tool() 호출
   - AI가 직접 32개의 이모티콘 설명 창작 (예: "하품하는 고양이", "화난 고양이" 등)
4. generate_tool() 호출하여 이미지 생성
5. after_preview_tool() 호출하여 결과 제공

핵심: **도구를 적극적으로 사용**하고, 세부 기획은 AI가 창작합니다."""
