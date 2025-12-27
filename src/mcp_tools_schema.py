"""
MCP 도구 스키마 정의

AI가 도구를 발견하고 사용할 때 필요한 메타데이터를 정의합니다.
/.well-known/mcp 엔드포인트와 도구 등록에서 공통으로 사용합니다.
"""
from typing import List, Dict, Any


# MCP 프로토콜 버전 (MCP 사양 기준)
MCP_PROTOCOL_VERSION = "2024-11-05"


# 도구별 inputSchema 정의 (JSON Schema 형식)
TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "get_specs_tool": {
        "name": "get_specs_tool",
        "description": "[1단계] 카카오톡 이모티콘 사양 조회. 타입별 개수, 파일 형식, 크기 제한을 확인합니다. 작업 시작 전 반드시 먼저 호출하세요.",
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
        "description": "[2단계] 제작 전 프리뷰 생성. AI가 이모티콘 설명을 직접 창작하여 카카오톡 스타일 프리뷰 페이지를 생성합니다. 사용자에게는 큰 방향만 묻고 세부 기획은 AI가 창작하세요.",
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
        "description": "[3단계] AI 이모티콘 이미지 생성. 캐릭터 이미지와 설명을 기반으로 실제 이모티콘 이미지를 생성합니다. 캐릭터 이미지 없으면 자동 생성됩니다.",
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
                    "description": "Hugging Face API 토큰. Authorization 헤더로도 전달 가능"
                }
            },
            "required": ["emoticon_type", "emoticons"]
        }
    },
    "after_preview_tool": {
        "name": "after_preview_tool",
        "description": "[4단계] 완성본 프리뷰 생성. 실제 이모티콘 이미지가 포함된 카카오톡 스타일 프리뷰와 ZIP 다운로드 URL을 제공합니다.",
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
        "description": "[5단계] 카카오톡 규격 검사. 파일 형식, 크기, 용량, 개수가 제출 규격에 맞는지 검증합니다.",
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
MCP_SERVER_INSTRUCTIONS = """카카오톡 이모티콘 제작 자동화 MCP 서버입니다.

## AI 행동 지침

### ✅ 적절한 질문 (큰 방향만 확인)
- 어떤 캐릭터/주제로 이모티콘을 만들지
- 어떤 느낌/분위기를 원하는지  
- 어떤 타입(멈춰있는/움직이는)으로 할지
- 결과물이 마음에 드는지

### ❌ 부적절한 질문 (AI가 스스로 해야 함)
- 이모티콘 하나하나의 상황을 사용자에게 다 물어보기
- 세부적인 포즈나 표정 하나하나 확인하기

## 워크플로우
1. get_specs_tool → 타입별 사양 확인 (개수, 형식)
2. before_preview_tool → AI가 창작한 기획으로 프리뷰 생성
3. generate_tool → 실제 이모티콘 이미지 생성
4. after_preview_tool → 완성본 프리뷰 및 다운로드
5. check_tool → 제출 전 규격 검증

## 타입별 이모티콘 개수
- static: 32개 | dynamic: 24개 | big: 16개
- static-mini: 42개 | dynamic-mini: 35개

핵심: 큰 방향만 사용자에게 묻고, 세부 기획은 AI가 직접 창작합니다."""
