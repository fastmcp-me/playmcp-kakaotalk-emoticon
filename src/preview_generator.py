"""
프리뷰 페이지 생성 모듈
"""
import secrets
import string
import base64
import zipfile
import io
from typing import List, Optional, Dict, Any
from jinja2 import Template

from src.constants import EMOTICON_SPECS, EMOTICON_TYPE_NAMES, EmoticonType, get_emoticon_spec


# before-preview 템플릿 (기획 단계)
BEFORE_PREVIEW_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - 이모티콘 기획 프리뷰</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #b2c7d9;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            background-color: #fff;
            padding: 12px 16px;
            display: flex;
            align-items: center;
            border-bottom: 1px solid #e5e5e5;
        }
        .header-title {
            font-size: 16px;
            font-weight: 600;
            color: #333;
            flex: 1;
            text-align: center;
        }
        .badge {
            background-color: #fee500;
            color: #3c1e1e;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        .chat-area {
            flex: 1;
            padding: 16px;
            overflow-y: auto;
        }
        .emoticon-panel {
            background-color: #fff;
            border-radius: 16px;
            margin-top: auto;
            max-height: 60vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        .panel-header {
            padding: 16px;
            border-bottom: 1px solid #f0f0f0;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .panel-title {
            font-size: 16px;
            font-weight: 600;
            color: #333;
        }
        .type-badge {
            background-color: #f5f5f5;
            color: #666;
            padding: 4px 8px;
            border-radius: 8px;
            font-size: 12px;
        }
        .emoticon-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            padding: 16px;
            overflow-y: auto;
        }
        .emoticon-item {
            aspect-ratio: 1;
            background-color: #f9f9f9;
            border-radius: 12px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 8px;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .emoticon-item:hover {
            background-color: #f0f0f0;
        }
        .emoticon-number {
            font-size: 24px;
            font-weight: 700;
            color: #fee500;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
        }
        .emoticon-desc {
            font-size: 10px;
            color: #999;
            text-align: center;
            margin-top: 4px;
            line-height: 1.2;
            max-height: 2.4em;
            overflow: hidden;
            text-overflow: ellipsis;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }
        .info-section {
            padding: 16px;
            background-color: #f9f9f9;
            border-top: 1px solid #f0f0f0;
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        .info-label {
            color: #666;
            font-size: 14px;
        }
        .info-value {
            color: #333;
            font-size: 14px;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-title">{{ title }}</div>
        <span class="badge">기획</span>
    </div>
    
    <div class="chat-area"></div>
    
    <div class="emoticon-panel">
        <div class="panel-header">
            <span class="panel-title">{{ title }}</span>
            <span class="type-badge">{{ emoticon_type_name }}</span>
        </div>
        
        <div class="emoticon-grid">
            {% for plan in plans %}
            <div class="emoticon-item">
                <span class="emoticon-number">{{ loop.index }}</span>
                <span class="emoticon-desc">{{ plan.description }}</span>
            </div>
            {% endfor %}
        </div>
        
        <div class="info-section">
            <div class="info-row">
                <span class="info-label">이모티콘 타입</span>
                <span class="info-value">{{ emoticon_type_name }}</span>
            </div>
            <div class="info-row">
                <span class="info-label">총 개수</span>
                <span class="info-value">{{ plans|length }} / {{ spec.count }}개</span>
            </div>
            <div class="info-row">
                <span class="info-label">파일 형식</span>
                <span class="info-value">{{ spec.format }}</span>
            </div>
            <div class="info-row">
                <span class="info-label">크기</span>
                <span class="info-value">{{ spec.sizes[0][0] }} x {{ spec.sizes[0][1] }} px</span>
            </div>
        </div>
    </div>
</body>
</html>
"""

# after-preview 템플릿 (완성본)
AFTER_PREVIEW_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - 이모티콘 프리뷰</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #b2c7d9;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            background-color: #fff;
            padding: 12px 16px;
            display: flex;
            align-items: center;
            border-bottom: 1px solid #e5e5e5;
        }
        .header-title {
            font-size: 16px;
            font-weight: 600;
            color: #333;
            flex: 1;
            text-align: center;
        }
        .badge {
            background-color: #fee500;
            color: #3c1e1e;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        .chat-area {
            flex: 1;
            padding: 16px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .download-section {
            display: flex;
            justify-content: center;
            margin-top: auto;
            margin-bottom: 8px;
        }
        .download-btn {
            background-color: #fee500;
            color: #3c1e1e;
            padding: 12px 24px;
            border-radius: 24px;
            font-size: 14px;
            font-weight: 600;
            text-decoration: none;
            transition: background-color 0.2s;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .download-btn:hover {
            background-color: #fdd835;
        }
        .emoticon-panel {
            background-color: #fff;
            border-radius: 16px;
            margin-top: auto;
            max-height: 60vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        .panel-header {
            padding: 16px;
            border-bottom: 1px solid #f0f0f0;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .icon-preview {
            width: 40px;
            height: 40px;
            border-radius: 8px;
            object-fit: cover;
        }
        .panel-title {
            font-size: 16px;
            font-weight: 600;
            color: #333;
        }
        .type-badge {
            background-color: #f5f5f5;
            color: #666;
            padding: 4px 8px;
            border-radius: 8px;
            font-size: 12px;
        }
        .emoticon-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            padding: 16px;
            overflow-y: auto;
        }
        .emoticon-item {
            aspect-ratio: 1;
            background-color: #f9f9f9;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 8px;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .emoticon-item:hover {
            background-color: #f0f0f0;
        }
        .emoticon-item img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }
        .info-section {
            padding: 16px;
            background-color: #f9f9f9;
            border-top: 1px solid #f0f0f0;
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        .info-label {
            color: #666;
            font-size: 14px;
        }
        .info-value {
            color: #333;
            font-size: 14px;
            font-weight: 500;
        }
        .preview-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.8);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .preview-modal.active {
            display: flex;
        }
        .preview-modal img {
            max-width: 90%;
            max-height: 90%;
            border-radius: 16px;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-title">{{ title }}</div>
        <span class="badge">완성</span>
    </div>
    
    <div class="chat-area">
        <div class="download-section">
            <a href="{{ download_url }}" class="download-btn" download>ZIP 다운로드</a>
        </div>
    </div>
    
    <div class="emoticon-panel">
        <div class="panel-header">
            {% if icon %}
            <img src="{{ icon }}" alt="아이콘" class="icon-preview">
            {% endif %}
            <span class="panel-title">{{ title }}</span>
            <span class="type-badge">{{ emoticon_type_name }}</span>
        </div>
        
        <div class="emoticon-grid">
            {% for emoticon in emoticons %}
            <div class="emoticon-item" onclick="showPreview('{{ emoticon.image_data }}')">
                <img src="{{ emoticon.image_data }}" alt="이모티콘 {{ loop.index }}">
            </div>
            {% endfor %}
        </div>
        
        <div class="info-section">
            <div class="info-row">
                <span class="info-label">이모티콘 타입</span>
                <span class="info-value">{{ emoticon_type_name }}</span>
            </div>
            <div class="info-row">
                <span class="info-label">총 개수</span>
                <span class="info-value">{{ emoticons|length }}개</span>
            </div>
        </div>
    </div>
    
    <div class="preview-modal" id="previewModal" onclick="hidePreview()">
        <img src="" alt="프리뷰" id="previewImage">
    </div>
    
    <script>
        function showPreview(src) {
            document.getElementById('previewImage').src = src;
            document.getElementById('previewModal').classList.add('active');
        }
        function hidePreview() {
            document.getElementById('previewModal').classList.remove('active');
        }
    </script>
</body>
</html>
"""


class PreviewGenerator:
    """프리뷰 페이지 생성기"""
    
    def __init__(self, base_url: str = ""):
        """
        초기화
        
        Args:
            base_url: 생성된 프리뷰 페이지의 베이스 URL
        """
        self.base_url = base_url.rstrip("/")
        self._storage: Dict[str, str] = {}  # preview_id -> HTML content
        self._zip_storage: Dict[str, bytes] = {}  # download_id -> ZIP bytes
    
    def _generate_short_id(self, length: int = 8) -> str:
        """
        짧은 랜덤 ID 생성
        
        Args:
            length: ID 길이 (기본값: 8)
            
        Returns:
            영문+숫자로 구성된 랜덤 문자열
        """
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def generate_before_preview(
        self,
        emoticon_type: EmoticonType | str,
        title: str,
        plans: List[Dict[str, str]]
    ) -> str:
        """
        before-preview 페이지 생성
        
        Args:
            emoticon_type: 이모티콘 타입 (Enum 또는 문자열)
            title: 이모티콘 제목
            plans: 이모티콘 기획 목록 [{description, file_type}, ...]
            
        Returns:
            프리뷰 페이지 URL 또는 data URL
        """
        spec = get_emoticon_spec(emoticon_type)
        # Enum을 문자열로 변환하여 EMOTICON_TYPE_NAMES 조회
        type_key = EmoticonType(emoticon_type) if isinstance(emoticon_type, str) else emoticon_type
        emoticon_type_name = EMOTICON_TYPE_NAMES[type_key]
        
        template = Template(BEFORE_PREVIEW_TEMPLATE)
        html_content = template.render(
            title=title,
            emoticon_type=emoticon_type,
            emoticon_type_name=emoticon_type_name,
            plans=plans,
            spec=spec
        )
        
        preview_id = self._generate_short_id()
        self._storage[preview_id] = html_content
        
        if self.base_url:
            return f"{self.base_url}/preview/{preview_id}"
        else:
            encoded = base64.b64encode(html_content.encode("utf-8")).decode("utf-8")
            return f"data:text/html;base64,{encoded}"
    
    def generate_after_preview(
        self,
        emoticon_type: EmoticonType | str,
        title: str,
        emoticons: List[Dict[str, Any]],
        icon: Optional[str] = None
    ) -> tuple[str, str]:
        """
        after-preview 페이지 생성
        
        Args:
            emoticon_type: 이모티콘 타입 (Enum 또는 문자열)
            title: 이모티콘 제목
            emoticons: 이모티콘 이미지 목록 [{image_data}, ...]
            icon: 아이콘 이미지 (base64 또는 URL)
            
        Returns:
            (프리뷰 페이지 URL, ZIP 다운로드 URL) 튜플
        """
        spec = get_emoticon_spec(emoticon_type)
        # Enum을 문자열로 변환하여 EMOTICON_TYPE_NAMES 조회
        type_key = EmoticonType(emoticon_type) if isinstance(emoticon_type, str) else emoticon_type
        emoticon_type_name = EMOTICON_TYPE_NAMES[type_key]
        
        # ZIP 파일 생성
        download_id = self._generate_short_id()
        zip_bytes = self._create_zip(emoticons, icon, spec.format.lower())
        self._zip_storage[download_id] = zip_bytes
        
        if self.base_url:
            download_url = f"{self.base_url}/download/{download_id}"
        else:
            encoded = base64.b64encode(zip_bytes).decode("utf-8")
            download_url = f"data:application/zip;base64,{encoded}"
        
        template = Template(AFTER_PREVIEW_TEMPLATE)
        html_content = template.render(
            title=title,
            emoticon_type=emoticon_type,
            emoticon_type_name=emoticon_type_name,
            emoticons=emoticons,
            icon=icon,
            download_url=download_url
        )
        
        preview_id = self._generate_short_id()
        self._storage[preview_id] = html_content
        
        if self.base_url:
            preview_url = f"{self.base_url}/preview/{preview_id}"
        else:
            encoded = base64.b64encode(html_content.encode("utf-8")).decode("utf-8")
            preview_url = f"data:text/html;base64,{encoded}"
        
        return preview_url, download_url
    
    def _create_zip(
        self,
        emoticons: List[Dict[str, Any]],
        icon: Optional[str],
        file_format: str
    ) -> bytes:
        """ZIP 파일 생성"""
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, emoticon in enumerate(emoticons, 1):
                image_data = emoticon.get("image_data", "")
                if image_data.startswith("data:"):
                    _, data = image_data.split(",", 1)
                    image_bytes = base64.b64decode(data)
                else:
                    image_bytes = base64.b64decode(image_data)
                
                filename = f"emoticon_{idx:02d}.{file_format}"
                zf.writestr(filename, image_bytes)
            
            if icon:
                if icon.startswith("data:"):
                    _, data = icon.split(",", 1)
                    icon_bytes = base64.b64decode(data)
                else:
                    icon_bytes = base64.b64decode(icon)
                zf.writestr("icon.png", icon_bytes)
        
        return zip_buffer.getvalue()
    
    def get_preview_html(self, preview_id: str) -> Optional[str]:
        """저장된 프리뷰 HTML 반환"""
        return self._storage.get(preview_id)
    
    def get_download_zip(self, download_id: str) -> Optional[bytes]:
        """저장된 ZIP 파일 반환"""
        return self._zip_storage.get(download_id)


# 전역 인스턴스
_preview_generator: Optional[PreviewGenerator] = None


def get_preview_generator(base_url: str = "") -> PreviewGenerator:
    """프리뷰 생성기 인스턴스 반환"""
    global _preview_generator
    if _preview_generator is None:
        _preview_generator = PreviewGenerator(base_url)
    return _preview_generator
