"""
MCP 도구 구현
"""
import os
import asyncio
from typing import List, Optional, Union

from src.constants import EMOTICON_SPECS, EMOTICON_TYPE_NAMES, EmoticonType, get_emoticon_spec
from src.models import (
    BeforePreviewRequest, BeforePreviewResponse,
    GenerateRequest, GenerateResponse, GeneratedEmoticon,
    GenerateAsyncResponse,
    AfterPreviewRequest, AfterPreviewResponse,
    CheckRequest, CheckResponse, CheckIssue
)
from src.preview_generator import get_preview_generator
from src.checker import get_checker
from src.image_utils import (
    get_image_bytes, encode_base64_image, get_image_info,
    process_emoticon_image, create_icon, video_to_animated_webp,
    decode_base64_image
)
from src.huggingface_client import get_hf_client
from src.task_storage import get_task_storage, TaskStatus


async def before_preview(request: BeforePreviewRequest) -> BeforePreviewResponse:
    """
    이모티콘 제작 이전 프리뷰
    
    카카오톡 채팅방과 같은 디자인의 페이지에서 이모티콘 탭 부분에
    이모티콘 설명이 글자로 써있는 형태의 프리뷰 페이지 URL을 반환합니다.
    """
    generator = get_preview_generator(os.environ.get("BASE_URL", ""))
    
    # Enum을 문자열로 변환
    emoticon_type_str = request.emoticon_type.value if isinstance(request.emoticon_type, EmoticonType) else request.emoticon_type
    
    plans = [
        {"description": plan.description, "file_type": plan.file_type.value if hasattr(plan.file_type, 'value') else plan.file_type}
        for plan in request.plans
    ]
    
    preview_url = await generator.generate_before_preview(
        emoticon_type=emoticon_type_str,
        title=request.title,
        plans=plans
    )
    
    return BeforePreviewResponse(
        preview_url=preview_url,
        emoticon_type=emoticon_type_str,
        title=request.title,
        total_count=len(request.plans)
    )


async def generate_async(
    request: GenerateRequest,
    hf_token: str
) -> GenerateAsyncResponse:
    """
    이모티콘 비동기 생성 시작
    
    즉시 작업 ID와 상태 확인 URL을 반환하고,
    백그라운드에서 이모티콘 생성을 진행합니다.
    """
    emoticon_type_str = request.emoticon_type.value if isinstance(request.emoticon_type, EmoticonType) else request.emoticon_type
    base_url = os.environ.get("BASE_URL", "")
    
    # 작업 생성
    task_storage = get_task_storage()
    task = await task_storage.create_task(
        emoticon_type=emoticon_type_str,
        total_count=len(request.emoticons)
    )
    
    # 상태 확인 URL 생성
    generator = get_preview_generator(base_url)
    status_url = await generator.generate_status_page(task.task_id)
    
    # 백그라운드 작업 시작
    background_task = asyncio.create_task(
        _run_generation_task(
            task_id=task.task_id,
            request=request,
            hf_token=hf_token,
            base_url=base_url
        )
    )
    
    # 예외 로깅을 위한 콜백 추가
    def _log_exception(t):
        if t.done() and not t.cancelled():
            exc = t.exception()
            if exc:
                import traceback
                print(f"Background task error for {task.task_id}: {exc}")
                traceback.print_exception(type(exc), exc, exc.__traceback__)
    
    background_task.add_done_callback(_log_exception)
    
    return GenerateAsyncResponse(
        task_id=task.task_id,
        status_url=status_url,
        message="이모티콘 생성이 시작되었습니다. 상태 확인 URL에서 진행 상황을 확인하세요.",
        emoticon_type=emoticon_type_str,
        total_count=len(request.emoticons)
    )


async def _run_generation_task(
    task_id: str,
    request: GenerateRequest,
    hf_token: str,
    base_url: str
) -> None:
    """
    백그라운드에서 이모티콘 생성 작업 실행
    """
    task_storage = get_task_storage()
    generator = get_preview_generator(base_url)
    
    try:
        await task_storage.update_task_status(task_id, TaskStatus.RUNNING)
        
        spec = get_emoticon_spec(request.emoticon_type)
        emoticon_type_str = request.emoticon_type.value if isinstance(request.emoticon_type, EmoticonType) else request.emoticon_type
        hf_client = get_hf_client(hf_token)
        
        # 캐릭터 이미지 준비
        await task_storage.update_task_progress(task_id, 0, "캐릭터 이미지 준비 중...")
        
        if request.character_image:
            character_bytes = await get_image_bytes(request.character_image)
        else:
            character_bytes = await hf_client.generate_character(
                "A cute cartoon character with simple design, white background, "
                "suitable for emoticon/sticker, kawaii style"
            )
        
        emoticon_bytes_list: List[bytes] = []
        
        for idx, emoticon_item in enumerate(request.emoticons):
            await task_storage.update_task_progress(
                task_id, 
                idx, 
                f"생성 중: {emoticon_item.description}"
            )
            
            is_animated = spec.is_animated
            
            if is_animated:
                video_bytes = await hf_client.generate_emoticon(
                    character_image=character_bytes,
                    emoticon_description=emoticon_item.description,
                    is_animated=True,
                    animation_prompt=emoticon_item.description
                )
                
                image_bytes = video_to_animated_webp(
                    video_bytes,
                    output_size=spec.sizes[0],
                    max_size_kb=spec.max_size_kb,
                    fps=15
                )
                mime_type = "image/webp"
            else:
                raw_image = await hf_client.generate_emoticon(
                    character_image=character_bytes,
                    emoticon_description=emoticon_item.description,
                    is_animated=False
                )
                
                image_bytes = process_emoticon_image(raw_image, spec)
                mime_type = "image/png" if spec.format == "PNG" else "image/webp"
            
            width, height, _ = get_image_info(image_bytes)
            size_kb = len(image_bytes) / 1024
            
            image_url = await generator.store_image(image_bytes, mime_type)
            emoticon_bytes_list.append(image_bytes)
            
            emoticon_data = {
                "index": idx,
                "image_data": image_url,
                "file_extension": emoticon_item.file_extension.value if hasattr(emoticon_item.file_extension, 'value') else emoticon_item.file_extension,
                "width": width,
                "height": height,
                "size_kb": round(size_kb, 2)
            }
            
            await task_storage.add_emoticon(task_id, emoticon_data)
            await task_storage.update_task_progress(task_id, idx + 1, f"완료: {emoticon_item.description}")
        
        # 아이콘 생성
        await task_storage.update_task_progress(task_id, len(request.emoticons), "아이콘 생성 중...")
        
        if emoticon_bytes_list:
            icon_bytes = create_icon(emoticon_bytes_list[0], spec)
        else:
            icon_bytes = create_icon(character_bytes, spec)
        
        icon_width, icon_height, _ = get_image_info(icon_bytes)
        icon_url = await generator.store_image(icon_bytes, "image/png")
        
        icon_data = {
            "index": -1,
            "image_data": icon_url,
            "file_extension": "png",
            "width": icon_width,
            "height": icon_height,
            "size_kb": round(len(icon_bytes) / 1024, 2)
        }
        
        await task_storage.set_icon(task_id, icon_data)
        await task_storage.complete_task(task_id)
        
    except Exception as e:
        await task_storage.set_error(task_id, str(e))


async def get_generation_result(task_id: str) -> dict:
    """
    이모티콘 생성 결과 조회
    
    완료된 작업의 이미지 URL들을 반환합니다.
    """
    task_storage = get_task_storage()
    task = await task_storage.get_task(task_id)
    
    if task is None:
        return {
            "error": "작업을 찾을 수 없습니다.",
            "task_id": task_id
        }
    
    task_dict = task.to_dict()
    
    if task.status == TaskStatus.COMPLETED:
        return {
            "status": "completed",
            "task_id": task_id,
            "emoticon_type": task.emoticon_type,
            "emoticons": task.emoticons,
            "icon": task.icon,
            "total_count": task.total_count,
            "message": "이모티콘 생성이 완료되었습니다."
        }
    elif task.status == TaskStatus.FAILED:
        return {
            "status": "failed",
            "task_id": task_id,
            "error_message": task.error_message,
            "message": "이모티콘 생성 중 오류가 발생했습니다."
        }
    else:
        return {
            "status": task.status.value,
            "task_id": task_id,
            "progress_percent": task_dict["progress_percent"],
            "completed_count": task.completed_count,
            "total_count": task.total_count,
            "current_description": task.current_description,
            "message": "이모티콘 생성이 아직 진행 중입니다. 잠시 후 다시 조회해주세요."
        }


async def after_preview(request: AfterPreviewRequest) -> AfterPreviewResponse:
    """
    완성본 프리뷰
    
    실제 이모티콘 이미지가 포함된 프리뷰 페이지 URL과
    ZIP 다운로드 URL을 반환합니다.
    """
    generator = get_preview_generator(os.environ.get("BASE_URL", ""))
    emoticon_type_str = request.emoticon_type.value if isinstance(request.emoticon_type, EmoticonType) else request.emoticon_type
    
    emoticons = [
        {"image_data": emoticon.image_data, "frames": emoticon.frames}
        for emoticon in request.emoticons
    ]
    
    preview_url, download_url = await generator.generate_after_preview(
        emoticon_type=emoticon_type_str,
        title=request.title,
        emoticons=emoticons,
        icon=request.icon
    )
    
    return AfterPreviewResponse(
        preview_url=preview_url,
        download_url=download_url,
        emoticon_type=emoticon_type_str,
        title=request.title
    )


async def check(request: CheckRequest) -> CheckResponse:
    """
    이모티콘 검사
    
    이모티콘이 카카오톡 사양에 맞는지 검사합니다.
    파일 형식, 크기, 개수 등을 검사합니다.
    """
    checker = get_checker()
    emoticon_type_str = request.emoticon_type.value if isinstance(request.emoticon_type, EmoticonType) else request.emoticon_type
    
    # 이미지 바이트로 변환
    emoticon_bytes_list = []
    for emoticon in request.emoticons:
        emoticon_bytes = decode_base64_image(emoticon.file_data)
        emoticon_bytes_list.append(emoticon_bytes)
    
    icon_bytes = None
    if request.icon:
        icon_bytes = decode_base64_image(request.icon.file_data)
    
    is_valid, issues = checker.check_emoticons(
        emoticon_type=emoticon_type_str,
        emoticons=emoticon_bytes_list,
        icon=icon_bytes
    )
    
    return CheckResponse(
        is_valid=is_valid,
        issues=issues,
        emoticon_type=emoticon_type_str,
        checked_count=len(request.emoticons)
    )
