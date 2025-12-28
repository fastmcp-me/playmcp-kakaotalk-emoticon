"""
Hugging Face Inference API 클라이언트
"""
import io
import asyncio
from typing import Optional
from huggingface_hub import InferenceClient
from PIL import Image


class HuggingFaceClient:
    """Hugging Face Inference API 클라이언트"""
    
    # 기본 모델 설정
    IMAGE_EDIT_MODEL = "Qwen/Qwen-Image-Edit"
    IMAGE_TO_VIDEO_MODEL = "Lightricks/LTX-Video-0.9.8-13B-distilled"
    TEXT_TO_IMAGE_MODEL = "black-forest-labs/FLUX.2-dev"
    
    def __init__(self, api_key: str):
        """
        초기화
        
        Args:
            api_key: Hugging Face API 키 (필수)
        """
        if not api_key:
            raise ValueError("Hugging Face API 토큰이 필요합니다. Authorization 헤더 또는 hf_token 파라미터로 전달해주세요.")
        self.api_key = api_key
        
        self.client = InferenceClient(
            provider="auto",
            api_key=self.api_key,
        )
    
    async def generate_character(self, prompt: str) -> bytes:
        """
        캐릭터 이미지 생성
        
        Args:
            prompt: 캐릭터 설명
            
        Returns:
            생성된 이미지 바이트
        """
        def _generate():
            image = self.client.text_to_image(
                prompt=prompt,
                model=self.TEXT_TO_IMAGE_MODEL,
            )
            output = io.BytesIO()
            image.save(output, format="PNG")
            return output.getvalue()
        
        return await asyncio.to_thread(_generate)
    
    async def edit_image(
        self,
        input_image: bytes,
        prompt: str,
        model: Optional[str] = None
    ) -> bytes:
        """
        이미지 편집 (image-to-image)
        
        Args:
            input_image: 입력 이미지 바이트
            prompt: 편집 지시 프롬프트
            model: 사용할 모델 (기본: Qwen-Image-Edit)
            
        Returns:
            편집된 이미지 바이트
        """
        _model = model or self.IMAGE_EDIT_MODEL
        
        def _edit():
            image = self.client.image_to_image(
                input_image,
                prompt=prompt,
                model=_model,
            )
            output = io.BytesIO()
            image.save(output, format="PNG")
            return output.getvalue()
        
        return await asyncio.to_thread(_edit)
    
    async def generate_video(
        self,
        input_image: bytes,
        prompt: str,
        model: Optional[str] = None
    ) -> bytes:
        """
        이미지를 비디오로 변환 (image-to-video)
        
        Args:
            input_image: 입력 이미지 바이트
            prompt: 동작 설명 프롬프트
            model: 사용할 모델 (기본: Wan2.1-I2V)
            
        Returns:
            생성된 비디오 바이트
        """
        _model = model or self.IMAGE_TO_VIDEO_MODEL
        
        def _generate():
            return self.client.image_to_video(
                input_image,
                prompt=prompt,
                model=_model,
            )
        
        return await asyncio.to_thread(_generate)
    
    async def generate_emoticon(
        self,
        character_image: bytes,
        emoticon_description: str,
        is_animated: bool = False,
        animation_prompt: Optional[str] = None
    ) -> bytes:
        """
        이모티콘 생성
        
        Args:
            character_image: 캐릭터 이미지 바이트
            emoticon_description: 이모티콘 설명 (상황, 배치 등)
            is_animated: 애니메이션 이모티콘 여부
            animation_prompt: 애니메이션 동작 설명
            
        Returns:
            생성된 이모티콘 이미지/비디오 바이트
        """
        # 1. 이미지 편집으로 이모티콘 첫 프레임 생성
        edited_image = await self.edit_image(
            character_image,
            prompt=emoticon_description
        )
        
        if not is_animated:
            return edited_image
        
        # 2. 애니메이션 이모티콘의 경우 비디오 생성
        if animation_prompt is None:
            animation_prompt = emoticon_description
        
        video = await self.generate_video(
            edited_image,
            prompt=animation_prompt
        )
        
        return video


def get_hf_client(api_key: str) -> HuggingFaceClient:
    """HuggingFace 클라이언트 인스턴스 반환
    
    Args:
        api_key: Hugging Face API 키 (필수)
    """
    return HuggingFaceClient(api_key=api_key)
