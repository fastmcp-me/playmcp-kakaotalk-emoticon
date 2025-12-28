"""
프리뷰 페이지 생성 모듈

Redis를 사용하여 프리뷰, 이미지, ZIP 파일을 저장합니다.
REDIS_URL이 설정되지 않은 경우 메모리 기반 저장소로 폴백합니다.
"""
import secrets
import string
import base64
import zipfile
import io
from typing import List, Optional, Dict, Any
from jinja2 import Template

from src.constants import EMOTICON_SPECS, EMOTICON_TYPE_NAMES, EmoticonType, get_emoticon_spec
from src.redis_client import get_storage, get_ttl, preview_key, image_key, zip_key, status_key


# before-preview 템플릿 (기획 단계)
BEFORE_PREVIEW_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{{ title }} - 이모티콘 기획 프리뷰</title>
    <style>
        :root {
            --bg-primary: #000000;
            --bg-secondary: #1a1a1a;
            --bg-tertiary: #2a2a2a;
            --bg-input: #2a2a2a;
            --text-primary: #ffffff;
            --text-secondary: #999999;
            --text-muted: #666666;
            --border-color: #333333;
            --kakao-yellow: #fee500;
            --kakao-brown: #3c1e1e;
            --bubble-mine: #fee500;
            --bubble-mine-text: #3c1e1e;
        }
        .light-mode {
            --bg-primary: #b2c7d9;
            --bg-secondary: #ffffff;
            --bg-tertiary: #f5f5f5;
            --bg-input: #ffffff;
            --text-primary: #333333;
            --text-secondary: #666666;
            --text-muted: #999999;
            --border-color: #e5e5e5;
            --bubble-mine: #fee500;
            --bubble-mine-text: #3c1e1e;
        }
        .light-mode .mini-emoticon-inline {
            background-color: rgba(0,0,0,0.08);
        }
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #000;
            min-height: 100vh;
            min-height: 100dvh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .chat-container {
            width: 100%;
            max-width: 400px;
            height: 100vh;
            height: 100dvh;
            background-color: var(--bg-primary);
            display: flex;
            flex-direction: column;
            position: relative;
            overflow: hidden;
        }
        .header {
            background-color: var(--bg-secondary);
            padding: 12px 16px;
            display: flex;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            z-index: 10;
        }
        .header-back {
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-primary);
            cursor: pointer;
        }
        .header-title {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
            flex: 1;
            text-align: center;
        }
        .header-actions {
            display: flex;
            gap: 12px;
            align-items: center;
        }
        .badge {
            background-color: var(--kakao-yellow);
            color: var(--kakao-brown);
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }
        .mode-toggle {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: var(--bg-tertiary);
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-primary);
            font-size: 14px;
        }
        .chat-area {
            flex: 1;
            padding: 16px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .message {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            max-width: 80%;
            margin-left: auto;
        }
        .message-bubble {
            background-color: var(--bubble-mine);
            color: var(--bubble-mine-text);
            padding: 10px 14px;
            border-radius: 16px 16px 4px 16px;
            font-size: 14px;
            line-height: 1.4;
            word-break: break-word;
        }
        .message-emoticon {
            background: transparent;
            padding: 4px;
        }
        .message-emoticon-content {
            font-size: 64px;
            line-height: 1;
        }
        .message-emoticon-label {
            font-size: 10px;
            color: var(--text-secondary);
            text-align: center;
            margin-top: 4px;
        }
        .message-time {
            font-size: 10px;
            color: var(--text-muted);
            margin-top: 4px;
        }
        .input-wrapper {
            position: relative;
            background-color: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
            z-index: 100;
        }
        .input-bar {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            gap: 8px;
        }
        .input-btn {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: none;
            background-color: var(--bg-tertiary);
            color: var(--text-secondary);
            font-size: 20px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            transition: all 0.2s;
        }
        .input-btn:hover {
            background-color: var(--border-color);
        }
        .input-field-wrapper {
            flex: 1;
            display: flex;
            align-items: center;
            background-color: var(--bg-input);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 0 4px 0 14px;
            min-height: 40px;
        }
        .input-field {
            flex: 1;
            border: none;
            background: transparent;
            color: var(--text-primary);
            font-size: 14px;
            outline: none;
            padding: 8px 0;
            min-width: 50px;
        }
        .input-field::placeholder {
            color: var(--text-muted);
        }
        .input-field-wrapper.has-mini {
            flex-wrap: wrap;
            padding: 6px 4px 6px 10px;
            gap: 4px;
        }
        .emoji-btn {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            border: none;
            background: transparent;
            color: var(--text-secondary);
            font-size: 18px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .emoji-btn:hover {
            background-color: var(--bg-tertiary);
        }
        .emoji-btn.active {
            color: var(--kakao-yellow);
        }
        .send-btn {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: none;
            background-color: var(--bg-tertiary);
            color: var(--text-secondary);
            font-size: 16px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            transition: all 0.2s;
        }
        .send-btn.active {
            background-color: var(--kakao-yellow);
            color: var(--kakao-brown);
        }
        .emoticon-panel {
            background-color: var(--bg-secondary);
            border-radius: 16px 16px 0 0;
            display: flex;
            flex-direction: column;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
        }
        .emoticon-panel.open {
            max-height: 60vh;
        }
        .panel-drag-handle {
            padding: 12px;
            display: flex;
            justify-content: center;
            cursor: grab;
        }
        .panel-drag-handle:active {
            cursor: grabbing;
        }
        .panel-drag-bar {
            width: 40px;
            height: 4px;
            background-color: var(--border-color);
            border-radius: 2px;
        }
        .panel-category-bar {
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 12px 12px;
            padding: 4px;
            background-color: var(--bg-tertiary);
            border-radius: 20px;
            gap: 2px;
            width: fit-content;
        }
        .panel-category-btn {
            padding: 6px 12px;
            border: none;
            background: transparent;
            color: var(--text-muted);
            font-size: 12px;
            border-radius: 16px;
            cursor: pointer;
            transition: all 0.2s;
            white-space: nowrap;
        }
        .panel-category-btn:hover {
            color: var(--text-secondary);
        }
        .panel-category-btn.active {
            background-color: #fff;
            color: #000;
        }
        .panel-tabs {
            display: flex;
            align-items: center;
            padding: 0 12px 12px;
            gap: 4px;
            border-bottom: 1px solid var(--border-color);
        }
        .panel-tab {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            border: none;
            background: transparent;
            color: var(--text-muted);
            font-size: 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .panel-tab:hover {
            background-color: var(--bg-tertiary);
        }
        .panel-tab.active {
            background-color: var(--bg-tertiary);
            color: var(--text-primary);
        }
        .panel-tab-stacked {
            flex-direction: column;
            gap: 2px;
            font-size: 10px;
            line-height: 1;
        }
        .panel-tab-all {
            padding: 4px 8px;
            width: auto;
            font-size: 11px;
            font-weight: 600;
            border: 1px solid var(--border-color);
        }
        .panel-tab-divider {
            width: 1px;
            height: 20px;
            background-color: var(--border-color);
            margin: 0 4px;
        }
        .panel-title-row {
            display: flex;
            align-items: center;
            padding: 12px 16px 8px;
            gap: 8px;
        }
        .panel-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-primary);
        }
        .panel-title-arrow {
            color: var(--text-muted);
            font-size: 12px;
        }
        .panel-type-badge {
            background-color: var(--bg-tertiary);
            color: var(--text-secondary);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            margin-left: auto;
        }
        .emoticon-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 4px;
            padding: 8px 12px 16px;
            overflow-y: auto;
            flex: 1;
        }
        .emoticon-grid.mini-grid {
            grid-template-columns: repeat(6, 1fr);
        }
        .emoticon-item {
            aspect-ratio: 1;
            background-color: var(--bg-tertiary);
            border-radius: 12px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 8px;
            cursor: pointer;
            transition: all 0.15s;
        }
        .emoticon-item.mini-item {
            aspect-ratio: auto;
            height: 40px;
            padding: 4px;
            border-radius: 8px;
        }
        .emoticon-item:hover {
            background-color: var(--border-color);
            transform: scale(1.05);
        }
        .emoticon-item:active {
            transform: scale(0.95);
        }
        .emoticon-number {
            font-size: 24px;
            font-weight: 700;
            color: var(--kakao-yellow);
        }
        .mini-item .emoticon-number {
            font-size: 14px;
        }
        .emoticon-desc {
            font-size: 9px;
            color: var(--text-muted);
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
        .mini-item .emoticon-desc {
            display: none;
        }
        /* 입력칸 내 미니 이모티콘 */
        .input-mini-emoticons {
            display: flex;
            flex-wrap: wrap;
            gap: 2px;
            align-items: center;
            max-width: 100%;
        }
        .input-mini-item {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background-color: var(--kakao-yellow);
            color: var(--kakao-brown);
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
        }
        .input-mini-item:hover {
            opacity: 0.8;
        }
        /* 미니 이모티콘만 전송 시 (6개 이하) */
        .message-mini-only {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            max-width: 80%;
            margin-left: auto;
        }
        .mini-only-container {
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            justify-content: flex-end;
            max-width: 260px;
        }
        .mini-only-item {
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: var(--kakao-yellow);
            color: var(--kakao-brown);
            border-radius: 8px;
            font-size: 16px;
            font-weight: 700;
        }
        /* 말풍선 내 미니 이모티콘 (인라인) */
        .mini-emoticon-inline {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background-color: rgba(0,0,0,0.1);
            border-radius: 3px;
            padding: 1px 4px;
            font-size: 12px;
            font-weight: 600;
            margin: 0 1px;
            vertical-align: middle;
        }
        .selection-popup {
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            margin-bottom: 8px;
            background-color: rgba(0, 0, 0, 0.6);
            border-radius: 16px;
            padding: 12px;
            display: none;
            flex-direction: row;
            align-items: flex-start;
            gap: 8px;
            z-index: 150;
        }
        .selection-popup.active {
            display: flex;
        }
        .selection-star {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            border: none;
            background: transparent;
            color: var(--text-muted);
            font-size: 16px;
            cursor: pointer;
            display: flex;
            align-items: flex-start;
            justify-content: center;
            padding-top: 4px;
        }
        .selection-star.filled {
            color: var(--kakao-yellow);
        }
        .selection-emoticon {
            width: 100px;
            height: 100px;
            background-color: var(--bg-tertiary);
            border-radius: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .selection-emoticon-number {
            font-size: 36px;
            font-weight: 700;
            color: var(--kakao-yellow);
        }
        .selection-emoticon-desc {
            font-size: 10px;
            color: var(--text-muted);
            text-align: center;
            margin-top: 4px;
            padding: 0 8px;
            max-width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .selection-close {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            border: none;
            background: transparent;
            color: var(--text-muted);
            font-size: 18px;
            cursor: pointer;
            display: flex;
            align-items: flex-start;
            justify-content: center;
            padding-top: 4px;
        }
        .info-toggle {
            padding: 8px 16px;
            border-top: 1px solid var(--border-color);
        }
        .info-toggle-btn {
            width: 100%;
            padding: 8px;
            border: none;
            background: var(--bg-tertiary);
            color: var(--text-secondary);
            font-size: 12px;
            border-radius: 8px;
            cursor: pointer;
        }
        .info-section {
            padding: 12px 16px;
            background-color: var(--bg-tertiary);
            border-top: 1px solid var(--border-color);
            display: none;
        }
        .info-section.open {
            display: block;
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 6px;
        }
        .info-row:last-child {
            margin-bottom: 0;
        }
        .info-label {
            color: var(--text-muted);
            font-size: 12px;
        }
        .info-value {
            color: var(--text-primary);
            font-size: 12px;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="chat-container" id="chatContainer">
        <div class="header">
            <div class="header-back">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M15 18l-6-6 6-6"/>
                </svg>
            </div>
            <div class="header-title">{{ title }}</div>
            <div class="header-actions">
                <span class="badge">기획</span>
                <button class="mode-toggle" id="modeToggle" title="다크/라이트 모드 전환">☽</button>
            </div>
        </div>
        
        <div class="chat-area" id="chatArea"></div>
        
        <div class="input-wrapper" id="inputWrapper">
            <div class="selection-popup" id="selectionPopup">
                <button class="selection-star" id="selectionStar">☆</button>
                <div class="selection-emoticon" id="selectionEmoticon">
                    <span class="selection-emoticon-number" id="selectionNumber"></span>
                    <span class="selection-emoticon-desc" id="selectionDesc"></span>
                </div>
                <button class="selection-close" id="selectionClose">✕</button>
            </div>
            <div class="input-bar">
                <button class="input-btn" id="addBtn">+</button>
                <div class="input-field-wrapper" id="inputFieldWrapper">
                    <div class="input-mini-emoticons" id="inputMiniEmoticons" style="display: none;"></div>
                    <input type="text" class="input-field" id="messageInput" placeholder="메시지 입력">
                    <button class="emoji-btn" id="emojiBtn">☺︎</button>
                </div>
                <button class="send-btn" id="sendBtn">#</button>
            </div>
        </div>
        
        <div class="emoticon-panel" id="emoticonPanel">
            <div class="panel-drag-handle" id="dragHandle">
                <div class="panel-drag-bar"></div>
            </div>
            
            <div class="panel-category-bar">
                <button class="panel-category-btn">검색</button>
                <button class="panel-category-btn{% if not is_mini %} active{% endif %}" data-category="emoticon">이모티콘</button>
                <button class="panel-category-btn{% if is_mini %} active{% endif %}" data-category="mini">미니 이모티콘</button>
            </div>
            
            <div class="panel-tabs">
                <button class="panel-tab panel-tab-stacked"><span>○</span><span>☆</span></button>
                <div class="panel-tab-divider"></div>
                <button class="panel-tab panel-tab-all">ALL</button>
                <button class="panel-tab active" id="emoticonTabBtn">☺︎</button>
            </div>
            
            <div class="panel-title-row">
                <span class="panel-title">{{ title }}</span>
                <span class="panel-title-arrow">›</span>
                <span class="panel-type-badge">{{ emoticon_type_name }}</span>
            </div>
            
            <div class="emoticon-grid{% if is_mini %} mini-grid{% endif %}" id="emoticonGrid">
                {% for plan in plans %}
                <div class="emoticon-item{% if is_mini %} mini-item{% endif %}" data-index="{{ loop.index }}" data-desc="{{ plan.description }}">
                    <span class="emoticon-number">{{ loop.index }}</span>
                    <span class="emoticon-desc">{{ plan.description }}</span>
                </div>
                {% endfor %}
            </div>
            
            <div class="info-toggle">
                <button class="info-toggle-btn" id="infoToggleBtn">상세 정보 보기 ▼</button>
            </div>
            
            <div class="info-section" id="infoSection">
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
    </div>
    

    
    <script>
        const chatContainer = document.getElementById('chatContainer');
        const chatArea = document.getElementById('chatArea');
        const inputWrapper = document.getElementById('inputWrapper');
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        const emojiBtn = document.getElementById('emojiBtn');
        const emoticonPanel = document.getElementById('emoticonPanel');
        const dragHandle = document.getElementById('dragHandle');
        const emoticonGrid = document.getElementById('emoticonGrid');
        const selectionPopup = document.getElementById('selectionPopup');
        const selectionNumber = document.getElementById('selectionNumber');
        const selectionDesc = document.getElementById('selectionDesc');
        const selectionStar = document.getElementById('selectionStar');
        const selectionClose = document.getElementById('selectionClose');
        const modeToggle = document.getElementById('modeToggle');
        const infoToggleBtn = document.getElementById('infoToggleBtn');
        const infoSection = document.getElementById('infoSection');
        const inputFieldWrapper = document.getElementById('inputFieldWrapper');
        const inputMiniEmoticons = document.getElementById('inputMiniEmoticons');
        
        let isPanelOpen = false;
        let selectedEmoticon = null;
        let isStarred = false;
        let isDragging = false;
        let startY = 0;
        let panelHeight = 0;
        
        // 미니 이모티콘 여부
        const isMini = {{ 'true' if is_mini else 'false' }};
        // 입력칸에 추가된 미니 이모티콘 목록
        let miniEmoticons = [];
        
        // Update send button state
        function updateSendButton() {
            if (messageInput.value.trim() || selectedEmoticon || miniEmoticons.length > 0) {
                sendBtn.classList.add('active');
                sendBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>';
            } else {
                sendBtn.classList.remove('active');
                sendBtn.textContent = '#';
            }
        }
        
        messageInput.addEventListener('input', updateSendButton);
        
        // 미니 이모티콘 입력칸 UI 업데이트
        function updateMiniInput() {
            if (miniEmoticons.length === 0) {
                inputMiniEmoticons.style.display = 'none';
                inputFieldWrapper.classList.remove('has-mini');
            } else {
                inputMiniEmoticons.style.display = 'flex';
                inputFieldWrapper.classList.add('has-mini');
                inputMiniEmoticons.innerHTML = miniEmoticons.map((e, i) => 
                    `<span class="input-mini-item" data-mini-index="${i}">[${e.index}]</span>`
                ).join('');
            }
            updateSendButton();
        }
        
        // 미니 이모티콘 입력칸에서 클릭 시 제거
        inputMiniEmoticons.addEventListener('click', (e) => {
            const item = e.target.closest('.input-mini-item');
            if (!item) return;
            const idx = parseInt(item.dataset.miniIndex);
            miniEmoticons.splice(idx, 1);
            updateMiniInput();
        });
        
        // Send message or emoticon
        function sendMessage() {
            if (selectedEmoticon && !isMini) {
                addMessage(`[${selectedEmoticon.index}]`, 'emoticon', selectedEmoticon.desc);
                closeSelection();
                return;
            }
            
            const text = messageInput.value.trim();
            
            // 미니 이모티콘 처리
            if (isMini && miniEmoticons.length > 0) {
                if (text === '' && miniEmoticons.length <= 6) {
                    // 미니 이모티콘만 6개 이하: 말풍선 없이 가로로 배치
                    addMiniOnlyMessage(miniEmoticons);
                } else {
                    // 텍스트와 섞여있거나 7개 이상: 말풍선 안에 인라인으로
                    addMixedMessage(text, miniEmoticons);
                }
                miniEmoticons = [];
                messageInput.value = '';
                updateMiniInput();
                return;
            }
            
            if (!text) return;
            
            addMessage(text, 'text');
            messageInput.value = '';
            updateSendButton();
        }
        
        sendBtn.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
        
        // 미니 이모티콘만 전송 (6개 이하)
        function addMiniOnlyMessage(emojis) {
            const message = document.createElement('div');
            message.className = 'message-mini-only';
            
            const time = new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
            
            const itemsHtml = emojis.map(e => `<div class="mini-only-item">[${e.index}]</div>`).join('');
            
            message.innerHTML = `
                <div class="mini-only-container">${itemsHtml}</div>
                <span class="message-time">${time}</span>
            `;
            
            chatArea.appendChild(message);
            chatArea.scrollTop = chatArea.scrollHeight;
        }
        
        // 텍스트와 미니 이모티콘 혼합 메시지
        function addMixedMessage(text, emojis) {
            const message = document.createElement('div');
            message.className = 'message';
            
            const time = new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
            
            // 미니 이모티콘을 인라인으로 표시
            const emojisHtml = emojis.map(e => `<span class="mini-emoticon-inline">[${e.index}]</span>`).join('');
            const content = escapeHtml(text) + emojisHtml;
            
            message.innerHTML = `
                <div class="message-bubble">${content}</div>
                <span class="message-time">${time}</span>
            `;
            
            chatArea.appendChild(message);
            chatArea.scrollTop = chatArea.scrollHeight;
        }
        
        // Add message to chat
        function addMessage(content, type, desc = '') {
            const message = document.createElement('div');
            message.className = 'message';
            
            const time = new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
            
            if (type === 'text') {
                message.innerHTML = `
                    <div class="message-bubble">${escapeHtml(content)}</div>
                    <span class="message-time">${time}</span>
                `;
            } else if (type === 'emoticon') {
                message.innerHTML = `
                    <div class="message-bubble message-emoticon">
                        <div class="message-emoticon-content">${content}</div>
                        <div class="message-emoticon-label">${escapeHtml(desc)}</div>
                    </div>
                    <span class="message-time">${time}</span>
                `;
            }
            
            chatArea.appendChild(message);
            chatArea.scrollTop = chatArea.scrollHeight;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Toggle emoticon panel
        emojiBtn.addEventListener('click', () => {
            isPanelOpen = !isPanelOpen;
            emoticonPanel.classList.toggle('open', isPanelOpen);
            emojiBtn.classList.toggle('active', isPanelOpen);
            
            if (!isPanelOpen) {
                emoticonPanel.style.maxHeight = '';
                closeSelection();
            }
        });
        
        // Emoticon selection
        emoticonGrid.addEventListener('click', (e) => {
            const item = e.target.closest('.emoticon-item');
            if (!item) return;
            
            if (isMini) {
                // 미니 이모티콘: 입력칸에 추가
                miniEmoticons.push({
                    index: item.dataset.index,
                    desc: item.dataset.desc
                });
                updateMiniInput();
                return;
            }
            
            selectedEmoticon = {
                index: item.dataset.index,
                desc: item.dataset.desc
            };
            
            selectionNumber.textContent = selectedEmoticon.index;
            selectionDesc.textContent = selectedEmoticon.desc;
            selectionPopup.classList.add('active');
            isStarred = false;
            selectionStar.textContent = '☆';
            selectionStar.classList.remove('filled');
            updateSendButton();
        });
        
        function closeSelection() {
            selectionPopup.classList.remove('active');
            selectedEmoticon = null;
            updateSendButton();
        }
        
        // Selection popup controls
        selectionClose.addEventListener('click', closeSelection);
        
        selectionStar.addEventListener('click', () => {
            isStarred = !isStarred;
            selectionStar.textContent = isStarred ? '★' : '☆';
            selectionStar.classList.toggle('filled', isStarred);
        });
        
        // Drag handle for panel resize
        dragHandle.addEventListener('mousedown', startDrag);
        dragHandle.addEventListener('touchstart', startDrag, { passive: false });
        
        function startDrag(e) {
            isDragging = true;
            startY = e.type === 'mousedown' ? e.clientY : e.touches[0].clientY;
            panelHeight = emoticonPanel.offsetHeight;
            document.addEventListener('mousemove', onDrag);
            document.addEventListener('mouseup', stopDrag);
            document.addEventListener('touchmove', onDrag, { passive: false });
            document.addEventListener('touchend', stopDrag);
        }
        
        function onDrag(e) {
            if (!isDragging) return;
            e.preventDefault();
            const clientY = e.type === 'mousemove' ? e.clientY : e.touches[0].clientY;
            const delta = startY - clientY;
            const newHeight = Math.min(Math.max(panelHeight + delta, 200), window.innerHeight * 0.8);
            emoticonPanel.style.maxHeight = newHeight + 'px';
        }
        
        function stopDrag() {
            isDragging = false;
            document.removeEventListener('mousemove', onDrag);
            document.removeEventListener('mouseup', stopDrag);
            document.removeEventListener('touchmove', onDrag);
            document.removeEventListener('touchend', stopDrag);
        }
        
        // Mode toggle
        modeToggle.addEventListener('click', () => {
            chatContainer.classList.toggle('light-mode');
            modeToggle.textContent = chatContainer.classList.contains('light-mode') ? '☼' : '☽';
        });
        
        // Info toggle
        infoToggleBtn.addEventListener('click', () => {
            const isOpen = infoSection.classList.toggle('open');
            infoToggleBtn.textContent = isOpen ? '상세 정보 닫기 ▲' : '상세 정보 보기 ▼';
        });
    </script>
</body>
</html>
"""

# status page 템플릿 (진행 상황)
STATUS_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>이모티콘 생성 중...</title>
    <style>
        :root {
            --bg-primary: #1a1a1a;
            --bg-secondary: #2a2a2a;
            --text-primary: #ffffff;
            --text-secondary: #999999;
            --kakao-yellow: #fee500;
            --success-green: #4ade80;
            --error-red: #f87171;
        }
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            width: 100%;
            max-width: 500px;
            background-color: var(--bg-secondary);
            border-radius: 20px;
            padding: 32px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .header {
            text-align: center;
            margin-bottom: 32px;
        }
        .header h1 {
            font-size: 24px;
            margin-bottom: 8px;
        }
        .header .task-id {
            font-size: 12px;
            color: var(--text-secondary);
            font-family: monospace;
        }
        .status-badge {
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            margin: 16px 0;
        }
        .status-pending {
            background-color: var(--text-secondary);
            color: #000;
        }
        .status-running {
            background-color: var(--kakao-yellow);
            color: #000;
        }
        .status-completed {
            background-color: var(--success-green);
            color: #000;
        }
        .status-failed {
            background-color: var(--error-red);
            color: #000;
        }
        .progress-section {
            margin: 24px 0;
        }
        .progress-bar-container {
            background-color: var(--bg-primary);
            border-radius: 10px;
            height: 20px;
            overflow: hidden;
            margin-bottom: 12px;
        }
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, var(--kakao-yellow), #ffd000);
            border-radius: 10px;
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .progress-bar span {
            font-size: 11px;
            font-weight: 600;
            color: #000;
        }
        .progress-text {
            display: flex;
            justify-content: space-between;
            font-size: 14px;
            color: var(--text-secondary);
        }
        .current-task {
            text-align: center;
            padding: 16px;
            background-color: var(--bg-primary);
            border-radius: 12px;
            margin: 16px 0;
        }
        .current-task-label {
            font-size: 12px;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }
        .current-task-desc {
            font-size: 16px;
            color: var(--text-primary);
        }
        .emoticon-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin-top: 24px;
            max-height: 300px;
            overflow-y: auto;
        }
        .emoticon-item {
            aspect-ratio: 1;
            background-color: var(--bg-primary);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .emoticon-item img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }
        .emoticon-item.pending {
            opacity: 0.3;
        }
        .emoticon-item.pending::after {
            content: '';
            width: 24px;
            height: 24px;
            border: 2px solid var(--text-secondary);
            border-radius: 50%;
        }
        .instructions {
            margin-top: 24px;
            padding: 16px;
            background-color: rgba(254, 229, 0, 0.1);
            border: 1px solid rgba(254, 229, 0, 0.3);
            border-radius: 12px;
        }
        .instructions h3 {
            font-size: 14px;
            color: var(--kakao-yellow);
            margin-bottom: 8px;
        }
        .instructions p {
            font-size: 13px;
            color: var(--text-secondary);
            line-height: 1.5;
        }
        .instructions code {
            background-color: var(--bg-primary);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            color: var(--kakao-yellow);
        }
        .error-message {
            margin-top: 16px;
            padding: 16px;
            background-color: rgba(248, 113, 113, 0.1);
            border: 1px solid rgba(248, 113, 113, 0.3);
            border-radius: 12px;
            color: var(--error-red);
            font-size: 14px;
        }
        .result-section {
            margin-top: 24px;
            text-align: center;
        }
        .result-section h3 {
            font-size: 18px;
            color: var(--success-green);
            margin-bottom: 16px;
        }
        .spinner {
            display: inline-block;
            width: 40px;
            height: 40px;
            border: 3px solid var(--bg-primary);
            border-top-color: var(--kakao-yellow);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 16px 0;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .refresh-note {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 16px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎨 이모티콘 생성</h1>
            <div class="task-id">작업 ID: {{ task_id }}</div>
        </div>
        
        <div id="statusContent">
            <div style="text-align: center;">
                <div class="spinner"></div>
                <p>로딩 중...</p>
            </div>
        </div>
    </div>
    
    <script>
        const taskId = '{{ task_id }}';
        
        async function fetchStatus() {
            try {
                const response = await fetch(`/status/${taskId}/json`);
                const data = await response.json();
                updateUI(data);
                
                if (data.status !== 'completed' && data.status !== 'failed') {
                    setTimeout(fetchStatus, 2000);
                }
            } catch (error) {
                console.error('Status fetch error:', error);
                setTimeout(fetchStatus, 3000);
            }
        }
        
        function updateUI(data) {
            const content = document.getElementById('statusContent');
            
            let statusClass = 'status-' + data.status;
            let statusText = {
                'pending': '대기 중',
                'running': '생성 중',
                'completed': '완료',
                'failed': '실패'
            }[data.status] || data.status;
            
            let html = `
                <div style="text-align: center;">
                    <span class="status-badge ${statusClass}">${statusText}</span>
                </div>
            `;
            
            if (data.status === 'running' || data.status === 'pending') {
                html += `
                    <div class="progress-section">
                        <div class="progress-bar-container">
                            <div class="progress-bar" style="width: ${data.progress_percent}%">
                                <span>${data.progress_percent}%</span>
                            </div>
                        </div>
                        <div class="progress-text">
                            <span>${data.completed_count} / ${data.total_count} 완료</span>
                            <span>${data.emoticon_type}</span>
                        </div>
                    </div>
                `;
                
                if (data.current_description) {
                    html += `
                        <div class="current-task">
                            <div class="current-task-label">현재 작업</div>
                            <div class="current-task-desc">${data.current_description}</div>
                        </div>
                    `;
                }
                
                html += `
                    <div class="spinner" style="margin: 24px auto; display: block;"></div>
                    <p class="refresh-note">페이지가 자동으로 업데이트됩니다...</p>
                `;
            }
            
            if (data.status === 'completed') {
                html += `
                    <div class="result-section">
                        <h3>✅ 생성 완료!</h3>
                        <p>이제 AI에게 작업 ID를 전달하여 결과를 확인하세요.</p>
                    </div>
                    <div class="instructions">
                        <h3>💡 다음 단계</h3>
                        <p>AI에게 다음 메시지를 보내세요:</p>
                        <p style="margin-top: 8px;"><code>이모티콘 생성 완료! 작업 ID: ${taskId}</code></p>
                    </div>
                `;
                
                if (data.emoticons && data.emoticons.length > 0) {
                    html += `<div class="emoticon-grid">`;
                    data.emoticons.forEach(e => {
                        html += `
                            <div class="emoticon-item">
                                <img src="${e.image_data}" alt="이모티콘">
                            </div>
                        `;
                    });
                    html += `</div>`;
                }
            }
            
            if (data.status === 'failed') {
                html += `
                    <div class="error-message">
                        <strong>오류 발생:</strong> ${data.error_message || '알 수 없는 오류'}
                    </div>
                    <div class="instructions">
                        <h3>💡 해결 방법</h3>
                        <p>AI에게 다시 생성을 요청해보세요.</p>
                    </div>
                `;
            }
            
            content.innerHTML = html;
        }
        
        fetchStatus();
    </script>
</body>
</html>
"""

# after-preview 템플릿 (완성본)
AFTER_PREVIEW_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{{ title }} - 이모티콘 프리뷰</title>
    <style>
        :root {
            --bg-primary: #000000;
            --bg-secondary: #1a1a1a;
            --bg-tertiary: #2a2a2a;
            --bg-input: #2a2a2a;
            --text-primary: #ffffff;
            --text-secondary: #999999;
            --text-muted: #666666;
            --border-color: #333333;
            --kakao-yellow: #fee500;
            --kakao-brown: #3c1e1e;
            --bubble-mine: #fee500;
            --bubble-mine-text: #3c1e1e;
        }
        .light-mode {
            --bg-primary: #b2c7d9;
            --bg-secondary: #ffffff;
            --bg-tertiary: #f5f5f5;
            --bg-input: #ffffff;
            --text-primary: #333333;
            --text-secondary: #666666;
            --text-muted: #999999;
            --border-color: #e5e5e5;
            --bubble-mine: #fee500;
            --bubble-mine-text: #3c1e1e;
        }
        .light-mode .mini-emoticon-inline {
            background-color: rgba(0,0,0,0.08);
        }
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #000;
            min-height: 100vh;
            min-height: 100dvh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .chat-container {
            width: 100%;
            max-width: 400px;
            height: 100vh;
            height: 100dvh;
            background-color: var(--bg-primary);
            display: flex;
            flex-direction: column;
            position: relative;
            overflow: hidden;
        }
        .header {
            background-color: var(--bg-secondary);
            padding: 12px 16px;
            display: flex;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            z-index: 10;
        }
        .header-back {
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-primary);
            cursor: pointer;
        }
        .header-title {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
            flex: 1;
            text-align: center;
        }
        .header-actions {
            display: flex;
            gap: 12px;
            align-items: center;
        }
        .badge {
            background-color: var(--kakao-yellow);
            color: var(--kakao-brown);
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }
        .mode-toggle {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: var(--bg-tertiary);
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-primary);
            font-size: 14px;
        }
        .chat-area {
            flex: 1;
            padding: 16px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .download-banner {
            display: flex;
            justify-content: center;
            padding: 12px;
        }
        .download-btn {
            background-color: var(--kakao-yellow);
            color: var(--kakao-brown);
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.2s;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }
        .download-btn:hover {
            transform: scale(1.05);
        }
        .message {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            max-width: 80%;
            margin-left: auto;
        }
        .message-bubble {
            background-color: var(--bubble-mine);
            color: var(--bubble-mine-text);
            padding: 10px 14px;
            border-radius: 16px 16px 4px 16px;
            font-size: 14px;
            line-height: 1.4;
            word-break: break-word;
        }
        .message-emoticon {
            background: transparent;
            padding: 4px;
        }
        .message-emoticon img {
            max-width: 120px;
            max-height: 120px;
            object-fit: contain;
        }
        .message-time {
            font-size: 10px;
            color: var(--text-muted);
            margin-top: 4px;
        }
        .input-wrapper {
            position: relative;
            background-color: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
            z-index: 100;
        }
        .input-bar {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            gap: 8px;
        }
        .input-btn {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: none;
            background-color: var(--bg-tertiary);
            color: var(--text-secondary);
            font-size: 20px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            transition: all 0.2s;
        }
        .input-btn:hover {
            background-color: var(--border-color);
        }
        .input-field-wrapper {
            flex: 1;
            display: flex;
            align-items: center;
            background-color: var(--bg-input);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 0 4px 0 14px;
            min-height: 40px;
        }
        .input-field {
            flex: 1;
            border: none;
            background: transparent;
            color: var(--text-primary);
            font-size: 14px;
            outline: none;
            padding: 8px 0;
            min-width: 50px;
        }
        .input-field::placeholder {
            color: var(--text-muted);
        }
        .input-field-wrapper.has-mini {
            flex-wrap: wrap;
            padding: 6px 4px 6px 10px;
            gap: 4px;
        }
        .emoji-btn {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            border: none;
            background: transparent;
            color: var(--text-secondary);
            font-size: 18px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .emoji-btn:hover {
            background-color: var(--bg-tertiary);
        }
        .emoji-btn.active {
            color: var(--kakao-yellow);
        }
        .send-btn {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: none;
            background-color: var(--bg-tertiary);
            color: var(--text-secondary);
            font-size: 16px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            transition: all 0.2s;
        }
        .send-btn.active {
            background-color: var(--kakao-yellow);
            color: var(--kakao-brown);
        }
        .emoticon-panel {
            background-color: var(--bg-secondary);
            border-radius: 16px 16px 0 0;
            display: flex;
            flex-direction: column;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
        }
        .emoticon-panel.open {
            max-height: 60vh;
        }
        .panel-drag-handle {
            padding: 12px;
            display: flex;
            justify-content: center;
            cursor: grab;
        }
        .panel-drag-handle:active {
            cursor: grabbing;
        }
        .panel-drag-bar {
            width: 40px;
            height: 4px;
            background-color: var(--border-color);
            border-radius: 2px;
        }
        .panel-category-bar {
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 12px 12px;
            padding: 4px;
            background-color: var(--bg-tertiary);
            border-radius: 20px;
            gap: 2px;
            width: fit-content;
        }
        .panel-category-btn {
            padding: 6px 12px;
            border: none;
            background: transparent;
            color: var(--text-muted);
            font-size: 12px;
            border-radius: 16px;
            cursor: pointer;
            transition: all 0.2s;
            white-space: nowrap;
        }
        .panel-category-btn:hover {
            color: var(--text-secondary);
        }
        .panel-category-btn.active {
            background-color: #fff;
            color: #000;
        }
        .panel-tabs {
            display: flex;
            align-items: center;
            padding: 0 12px 12px;
            gap: 4px;
            border-bottom: 1px solid var(--border-color);
        }
        .panel-tab {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            border: none;
            background: transparent;
            color: var(--text-muted);
            font-size: 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .panel-tab:hover {
            background-color: var(--bg-tertiary);
        }
        .panel-tab.active {
            background-color: var(--bg-tertiary);
            color: var(--text-primary);
        }
        .panel-tab-stacked {
            flex-direction: column;
            gap: 2px;
            font-size: 10px;
            line-height: 1;
        }
        .panel-tab-all {
            padding: 4px 8px;
            width: auto;
            font-size: 11px;
            font-weight: 600;
            border: 1px solid var(--border-color);
        }
        .panel-tab-divider {
            width: 1px;
            height: 20px;
            background-color: var(--border-color);
            margin: 0 4px;
        }
        .panel-tab-icon {
            width: 28px;
            height: 28px;
            border-radius: 6px;
            object-fit: cover;
        }
        .panel-title-row {
            display: flex;
            align-items: center;
            padding: 12px 16px 8px;
            gap: 8px;
        }
        .panel-icon-preview {
            width: 32px;
            height: 32px;
            border-radius: 6px;
            object-fit: cover;
        }
        .panel-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-primary);
        }
        .panel-title-arrow {
            color: var(--text-muted);
            font-size: 12px;
        }
        .panel-type-badge {
            background-color: var(--bg-tertiary);
            color: var(--text-secondary);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            margin-left: auto;
        }
        .emoticon-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 4px;
            padding: 8px 12px 16px;
            overflow-y: auto;
            flex: 1;
        }
        .emoticon-grid.mini-grid {
            grid-template-columns: repeat(6, 1fr);
        }
        .emoticon-item {
            aspect-ratio: 1;
            background-color: var(--bg-tertiary);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 8px;
            cursor: pointer;
            transition: all 0.15s;
        }
        .emoticon-item.mini-item {
            aspect-ratio: auto;
            height: 40px;
            padding: 4px;
            border-radius: 8px;
        }
        .emoticon-item:hover {
            background-color: var(--border-color);
            transform: scale(1.05);
        }
        .emoticon-item:active {
            transform: scale(0.95);
        }
        .emoticon-item img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }
        .emoticon-item.mini-item img {
            height: 32px;
            width: auto;
        }
        /* 입력칸 내 미니 이모티콘 */
        .input-mini-emoticons {
            display: flex;
            flex-wrap: wrap;
            gap: 2px;
            align-items: center;
            max-width: 100%;
        }
        .input-mini-item {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
            cursor: pointer;
            height: 24px;
            overflow: hidden;
        }
        .input-mini-item img {
            height: 100%;
            width: auto;
        }
        .input-mini-item:hover {
            opacity: 0.8;
        }
        /* 미니 이모티콘만 전송 시 (6개 이하) */
        .message-mini-only {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            max-width: 80%;
            margin-left: auto;
        }
        .mini-only-container {
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            justify-content: flex-end;
            max-width: 260px;
        }
        .mini-only-item {
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .mini-only-item img {
            height: 100%;
            width: auto;
        }
        /* 말풍선 내 미니 이모티콘 (인라인) */
        .mini-emoticon-inline {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 3px;
            margin: 0 1px;
            vertical-align: middle;
            height: 18px;
        }
        .mini-emoticon-inline img {
            height: 100%;
            width: auto;
        }
        .selection-popup {
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            margin-bottom: 8px;
            background-color: rgba(0, 0, 0, 0.6);
            border-radius: 16px;
            padding: 12px;
            display: none;
            flex-direction: row;
            align-items: flex-start;
            gap: 8px;
            z-index: 150;
        }
        .selection-popup.active {
            display: flex;
        }
        .selection-star {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            border: none;
            background: transparent;
            color: var(--text-muted);
            font-size: 16px;
            cursor: pointer;
            display: flex;
            align-items: flex-start;
            justify-content: center;
            padding-top: 4px;
        }
        .selection-star.filled {
            color: var(--kakao-yellow);
        }
        .selection-emoticon {
            width: 100px;
            height: 100px;
            background-color: var(--bg-tertiary);
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 8px;
        }
        .selection-emoticon img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }
        .selection-close {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            border: none;
            background: transparent;
            color: var(--text-muted);
            font-size: 18px;
            cursor: pointer;
            display: flex;
            align-items: flex-start;
            justify-content: center;
            padding-top: 4px;
        }
        .info-toggle {
            padding: 8px 16px;
            border-top: 1px solid var(--border-color);
        }
        .info-toggle-btn {
            width: 100%;
            padding: 8px;
            border: none;
            background: var(--bg-tertiary);
            color: var(--text-secondary);
            font-size: 12px;
            border-radius: 8px;
            cursor: pointer;
        }
        .info-section {
            padding: 12px 16px;
            background-color: var(--bg-tertiary);
            border-top: 1px solid var(--border-color);
            display: none;
        }
        .info-section.open {
            display: block;
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 6px;
        }
        .info-row:last-child {
            margin-bottom: 0;
        }
        .info-label {
            color: var(--text-muted);
            font-size: 12px;
        }
        .info-value {
            color: var(--text-primary);
            font-size: 12px;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="chat-container" id="chatContainer">
        <div class="header">
            <div class="header-back">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M15 18l-6-6 6-6"/>
                </svg>
            </div>
            <div class="header-title">{{ title }}</div>
            <div class="header-actions">
                <span class="badge">완성</span>
                <button class="mode-toggle" id="modeToggle" title="다크/라이트 모드 전환">☽</button>
            </div>
        </div>
        
        <div class="chat-area" id="chatArea">
            <div class="download-banner">
                <a href="{{ download_url }}" class="download-btn" download>ZIP 다운로드</a>
            </div>
        </div>
        
        <div class="input-wrapper" id="inputWrapper">
            <div class="selection-popup" id="selectionPopup">
                <button class="selection-star" id="selectionStar">☆</button>
                <div class="selection-emoticon" id="selectionEmoticon">
                    <img src="" alt="" id="selectionImage">
                </div>
                <button class="selection-close" id="selectionClose">✕</button>
            </div>
            <div class="input-bar">
                <button class="input-btn" id="addBtn">+</button>
                <div class="input-field-wrapper" id="inputFieldWrapper">
                    <div class="input-mini-emoticons" id="inputMiniEmoticons" style="display: none;"></div>
                    <input type="text" class="input-field" id="messageInput" placeholder="메시지 입력">
                    <button class="emoji-btn" id="emojiBtn">☺︎</button>
                </div>
                <button class="send-btn" id="sendBtn">#</button>
            </div>
        </div>
        
        <div class="emoticon-panel" id="emoticonPanel">
            <div class="panel-drag-handle" id="dragHandle">
                <div class="panel-drag-bar"></div>
            </div>
            
            <div class="panel-category-bar">
                <button class="panel-category-btn">검색</button>
                <button class="panel-category-btn{% if not is_mini %} active{% endif %}" data-category="emoticon">이모티콘</button>
                <button class="panel-category-btn{% if is_mini %} active{% endif %}" data-category="mini">미니 이모티콘</button>
            </div>
            
            <div class="panel-tabs">
                <button class="panel-tab panel-tab-stacked"><span>○</span><span>☆</span></button>
                <div class="panel-tab-divider"></div>
                <button class="panel-tab panel-tab-all">ALL</button>
                {% if icon %}
                <button class="panel-tab active" id="emoticonTabBtn">
                    <img src="{{ icon }}" alt="" class="panel-tab-icon">
                </button>
                {% else %}
                <button class="panel-tab active" id="emoticonTabBtn">☺︎</button>
                {% endif %}
            </div>
            
            <div class="panel-title-row">
                {% if icon %}
                <img src="{{ icon }}" alt="" class="panel-icon-preview">
                {% endif %}
                <span class="panel-title">{{ title }}</span>
                <span class="panel-title-arrow">›</span>
                <span class="panel-type-badge">{{ emoticon_type_name }}</span>
            </div>
            
            <div class="emoticon-grid{% if is_mini %} mini-grid{% endif %}" id="emoticonGrid">
                {% for emoticon in emoticons %}
                <div class="emoticon-item{% if is_mini %} mini-item{% endif %}" data-index="{{ loop.index }}" data-src="{{ emoticon.image_data }}">
                    <img src="{{ emoticon.image_data }}" alt="이모티콘 {{ loop.index }}">
                </div>
                {% endfor %}
            </div>
            
            <div class="info-toggle">
                <button class="info-toggle-btn" id="infoToggleBtn">상세 정보 보기 ▼</button>
            </div>
            
            <div class="info-section" id="infoSection">
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
    </div>
    
    <script>
        const chatContainer = document.getElementById('chatContainer');
        const chatArea = document.getElementById('chatArea');
        const inputWrapper = document.getElementById('inputWrapper');
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        const emojiBtn = document.getElementById('emojiBtn');
        const emoticonPanel = document.getElementById('emoticonPanel');
        const dragHandle = document.getElementById('dragHandle');
        const emoticonGrid = document.getElementById('emoticonGrid');
        const selectionPopup = document.getElementById('selectionPopup');
        const selectionImage = document.getElementById('selectionImage');
        const selectionStar = document.getElementById('selectionStar');
        const selectionClose = document.getElementById('selectionClose');
        const modeToggle = document.getElementById('modeToggle');
        const infoToggleBtn = document.getElementById('infoToggleBtn');
        const infoSection = document.getElementById('infoSection');
        const inputFieldWrapper = document.getElementById('inputFieldWrapper');
        const inputMiniEmoticons = document.getElementById('inputMiniEmoticons');
        
        let isPanelOpen = false;
        let selectedEmoticon = null;
        let isStarred = false;
        let isDragging = false;
        let startY = 0;
        let panelHeight = 0;
        
        // 미니 이모티콘 여부
        const isMini = {{ 'true' if is_mini else 'false' }};
        // 입력칸에 추가된 미니 이모티콘 목록
        let miniEmoticons = [];
        
        // Update send button state
        function updateSendButton() {
            if (messageInput.value.trim() || selectedEmoticon || miniEmoticons.length > 0) {
                sendBtn.classList.add('active');
                sendBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>';
            } else {
                sendBtn.classList.remove('active');
                sendBtn.textContent = '#';
            }
        }
        
        messageInput.addEventListener('input', updateSendButton);
        
        // 미니 이모티콘 입력칸 UI 업데이트
        function updateMiniInput() {
            if (miniEmoticons.length === 0) {
                inputMiniEmoticons.style.display = 'none';
                inputFieldWrapper.classList.remove('has-mini');
            } else {
                inputMiniEmoticons.style.display = 'flex';
                inputFieldWrapper.classList.add('has-mini');
                inputMiniEmoticons.innerHTML = miniEmoticons.map((e, i) => 
                    `<span class="input-mini-item" data-mini-index="${i}"><img src="${e.src}" alt=""></span>`
                ).join('');
            }
            updateSendButton();
        }
        
        // 미니 이모티콘 입력칸에서 클릭 시 제거
        inputMiniEmoticons.addEventListener('click', (e) => {
            const item = e.target.closest('.input-mini-item');
            if (!item) return;
            const idx = parseInt(item.dataset.miniIndex);
            miniEmoticons.splice(idx, 1);
            updateMiniInput();
        });
        
        // Send message or emoticon
        function sendMessage() {
            if (selectedEmoticon && !isMini) {
                addMessage('', 'emoticon', selectedEmoticon.src);
                closeSelection();
                return;
            }
            
            const text = messageInput.value.trim();
            
            // 미니 이모티콘 처리
            if (isMini && miniEmoticons.length > 0) {
                if (text === '' && miniEmoticons.length <= 6) {
                    // 미니 이모티콘만 6개 이하: 말풍선 없이 가로로 배치
                    addMiniOnlyMessage(miniEmoticons);
                } else {
                    // 텍스트와 섞여있거나 7개 이상: 말풍선 안에 인라인으로
                    addMixedMessage(text, miniEmoticons);
                }
                miniEmoticons = [];
                messageInput.value = '';
                updateMiniInput();
                return;
            }
            
            if (!text) return;
            
            addMessage(text, 'text');
            messageInput.value = '';
            updateSendButton();
        }
        
        sendBtn.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
        
        // 미니 이모티콘만 전송 (6개 이하)
        function addMiniOnlyMessage(emojis) {
            const message = document.createElement('div');
            message.className = 'message-mini-only';
            
            const time = new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
            
            const itemsHtml = emojis.map(e => `<div class="mini-only-item"><img src="${e.src}" alt=""></div>`).join('');
            
            message.innerHTML = `
                <div class="mini-only-container">${itemsHtml}</div>
                <span class="message-time">${time}</span>
            `;
            
            chatArea.appendChild(message);
            chatArea.scrollTop = chatArea.scrollHeight;
        }
        
        // 텍스트와 미니 이모티콘 혼합 메시지
        function addMixedMessage(text, emojis) {
            const message = document.createElement('div');
            message.className = 'message';
            
            const time = new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
            
            // 미니 이모티콘을 인라인으로 표시
            const emojisHtml = emojis.map(e => `<span class="mini-emoticon-inline"><img src="${e.src}" alt=""></span>`).join('');
            const content = escapeHtml(text) + emojisHtml;
            
            message.innerHTML = `
                <div class="message-bubble">${content}</div>
                <span class="message-time">${time}</span>
            `;
            
            chatArea.appendChild(message);
            chatArea.scrollTop = chatArea.scrollHeight;
        }
        
        // Add message to chat
        function addMessage(content, type, imageSrc = '') {
            const message = document.createElement('div');
            message.className = 'message';
            
            const time = new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
            
            if (type === 'text') {
                message.innerHTML = `
                    <div class="message-bubble">${escapeHtml(content)}</div>
                    <span class="message-time">${time}</span>
                `;
            } else if (type === 'emoticon') {
                message.innerHTML = `
                    <div class="message-bubble message-emoticon">
                        <img src="${imageSrc}" alt="이모티콘">
                    </div>
                    <span class="message-time">${time}</span>
                `;
            }
            
            chatArea.appendChild(message);
            chatArea.scrollTop = chatArea.scrollHeight;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Toggle emoticon panel
        emojiBtn.addEventListener('click', () => {
            isPanelOpen = !isPanelOpen;
            emoticonPanel.classList.toggle('open', isPanelOpen);
            emojiBtn.classList.toggle('active', isPanelOpen);
            
            if (!isPanelOpen) {
                emoticonPanel.style.maxHeight = '';
                closeSelection();
            }
        });
        
        // Emoticon selection
        emoticonGrid.addEventListener('click', (e) => {
            const item = e.target.closest('.emoticon-item');
            if (!item) return;
            
            if (isMini) {
                // 미니 이모티콘: 입력칸에 추가
                miniEmoticons.push({
                    index: item.dataset.index,
                    src: item.dataset.src
                });
                updateMiniInput();
                return;
            }
            
            selectedEmoticon = {
                index: item.dataset.index,
                src: item.dataset.src
            };
            
            selectionImage.src = selectedEmoticon.src;
            selectionPopup.classList.add('active');
            isStarred = false;
            selectionStar.textContent = '☆';
            selectionStar.classList.remove('filled');
            updateSendButton();
        });
        
        function closeSelection() {
            selectionPopup.classList.remove('active');
            selectedEmoticon = null;
            updateSendButton();
        }
        
        // Selection popup controls
        selectionClose.addEventListener('click', closeSelection);
        
        selectionStar.addEventListener('click', () => {
            isStarred = !isStarred;
            selectionStar.textContent = isStarred ? '★' : '☆';
            selectionStar.classList.toggle('filled', isStarred);
        });
        
        // Drag handle for panel resize
        dragHandle.addEventListener('mousedown', startDrag);
        dragHandle.addEventListener('touchstart', startDrag, { passive: false });
        
        function startDrag(e) {
            isDragging = true;
            startY = e.type === 'mousedown' ? e.clientY : e.touches[0].clientY;
            panelHeight = emoticonPanel.offsetHeight;
            document.addEventListener('mousemove', onDrag);
            document.addEventListener('mouseup', stopDrag);
            document.addEventListener('touchmove', onDrag, { passive: false });
            document.addEventListener('touchend', stopDrag);
        }
        
        function onDrag(e) {
            if (!isDragging) return;
            e.preventDefault();
            const clientY = e.type === 'mousemove' ? e.clientY : e.touches[0].clientY;
            const delta = startY - clientY;
            const newHeight = Math.min(Math.max(panelHeight + delta, 200), window.innerHeight * 0.8);
            emoticonPanel.style.maxHeight = newHeight + 'px';
        }
        
        function stopDrag() {
            isDragging = false;
            document.removeEventListener('mousemove', onDrag);
            document.removeEventListener('mouseup', stopDrag);
            document.removeEventListener('touchmove', onDrag);
            document.removeEventListener('touchend', stopDrag);
        }
        
        // Mode toggle
        modeToggle.addEventListener('click', () => {
            chatContainer.classList.toggle('light-mode');
            modeToggle.textContent = chatContainer.classList.contains('light-mode') ? '☼' : '☽';
        });
        
        // Info toggle
        infoToggleBtn.addEventListener('click', () => {
            const isOpen = infoSection.classList.toggle('open');
            infoToggleBtn.textContent = isOpen ? '상세 정보 닫기 ▲' : '상세 정보 보기 ▼';
        });
    </script>
</body>
</html>
"""


class PreviewGenerator:
    """프리뷰 페이지 생성기 (Redis 기반)"""
    
    def __init__(self, base_url: str = ""):
        """
        초기화
        
        Args:
            base_url: 생성된 프리뷰 페이지의 베이스 URL
        """
        self.base_url = base_url.rstrip("/")
        self._storage = get_storage()
    
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
    
    async def store_image(self, image_data: bytes, mime_type: str = "image/png") -> str:
        """
        이미지를 저장하고 URL을 반환합니다.
        
        Args:
            image_data: 이미지 바이트 데이터
            mime_type: 이미지 MIME 타입
            
        Returns:
            이미지 URL (예: /image/{image_id} 또는 {base_url}/image/{image_id})
        """
        image_id = self._generate_short_id()
        ttl = get_ttl("image")
        
        # 이미지 데이터 저장 (바이너리)
        await self._storage.set(image_key(image_id), image_data, ttl=ttl)
        # 메타데이터 저장 (JSON)
        await self._storage.set_json(f"{image_key(image_id)}:meta", {"mime_type": mime_type}, ttl=ttl)
        
        if self.base_url:
            return f"{self.base_url}/image/{image_id}"
        else:
            return f"/image/{image_id}"
    
    async def store_base64_image(self, base64_data: str) -> str:
        """
        Base64 인코딩된 이미지를 저장하고 URL을 반환합니다.
        
        Args:
            base64_data: Base64 인코딩된 이미지 (data:image/...;base64,... 형식 지원)
            
        Returns:
            이미지 URL
        """
        if base64_data.startswith("data:"):
            # data:image/png;base64,... 형식 파싱
            header, data = base64_data.split(",", 1)
            mime_type = header.split(":")[1].split(";")[0]
        else:
            data = base64_data
            mime_type = "image/png"
        
        image_bytes = base64.b64decode(data)
        return await self.store_image(image_bytes, mime_type)
    
    async def get_image(self, image_id: str) -> Optional[Dict[str, Any]]:
        """
        저장된 이미지 정보 반환
        
        Args:
            image_id: 이미지 ID
            
        Returns:
            {"data": bytes, "mime_type": str} 또는 None
        """
        # 이미지 데이터 조회
        data = await self._storage.get(image_key(image_id))
        if data is None:
            return None
        
        # 메타데이터 조회
        meta = await self._storage.get_json(f"{image_key(image_id)}:meta")
        mime_type = meta.get("mime_type", "image/png") if meta else "image/png"
        
        return {"data": data, "mime_type": mime_type}
    
    async def generate_status_page(self, task_id: str) -> str:
        """
        생성 작업 상태 페이지 URL 생성
        
        Args:
            task_id: 작업 ID
            
        Returns:
            상태 페이지 URL
        """
        template = Template(STATUS_PAGE_TEMPLATE)
        html_content = template.render(task_id=task_id)
        
        # 상태 페이지 저장
        await self._storage.set(status_key(task_id), html_content.encode('utf-8'), ttl=get_ttl("status"))
        
        if self.base_url:
            return f"{self.base_url}/status/{task_id}"
        else:
            return f"/status/{task_id}"
    
    async def get_status_html(self, task_id: str) -> Optional[str]:
        """저장된 상태 페이지 HTML 반환"""
        data = await self._storage.get(status_key(task_id))
        if data:
            return data.decode('utf-8')
        return None
    
    async def generate_before_preview(
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
            프리뷰 페이지 URL
        """
        spec = get_emoticon_spec(emoticon_type)
        # Enum을 문자열로 변환하여 EMOTICON_TYPE_NAMES 조회
        type_key = EmoticonType(emoticon_type) if isinstance(emoticon_type, str) else emoticon_type
        emoticon_type_name = EMOTICON_TYPE_NAMES[type_key]
        
        # 미니 이모티콘 여부 확인
        is_mini = type_key in [EmoticonType.STATIC_MINI, EmoticonType.DYNAMIC_MINI]
        
        template = Template(BEFORE_PREVIEW_TEMPLATE)
        html_content = template.render(
            title=title,
            emoticon_type=emoticon_type,
            emoticon_type_name=emoticon_type_name,
            plans=plans,
            spec=spec,
            is_mini=is_mini
        )
        
        preview_id = self._generate_short_id()
        await self._storage.set(preview_key(preview_id), html_content.encode('utf-8'), ttl=get_ttl("preview"))
        
        if self.base_url:
            return f"{self.base_url}/preview/{preview_id}"
        else:
            return f"/preview/{preview_id}"
    
    async def generate_after_preview(
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
        
        # 미니 이모티콘 여부 확인
        is_mini = type_key in [EmoticonType.STATIC_MINI, EmoticonType.DYNAMIC_MINI]
        
        # ZIP 파일 생성
        download_id = self._generate_short_id()
        zip_bytes = await self._create_zip(emoticons, icon, spec.format.lower())
        await self._storage.set(zip_key(download_id), zip_bytes, ttl=get_ttl("zip"))
        
        if self.base_url:
            download_url = f"{self.base_url}/download/{download_id}"
        else:
            download_url = f"/download/{download_id}"
        
        template = Template(AFTER_PREVIEW_TEMPLATE)
        html_content = template.render(
            title=title,
            emoticon_type=emoticon_type,
            emoticon_type_name=emoticon_type_name,
            emoticons=emoticons,
            icon=icon,
            download_url=download_url,
            is_mini=is_mini
        )
        
        preview_id = self._generate_short_id()
        await self._storage.set(preview_key(preview_id), html_content.encode('utf-8'), ttl=get_ttl("preview"))
        
        if self.base_url:
            preview_url = f"{self.base_url}/preview/{preview_id}"
        else:
            preview_url = f"/preview/{preview_id}"
        
        return preview_url, download_url
    
    async def _get_image_bytes_from_ref(self, image_ref: str) -> Optional[bytes]:
        """
        이미지 참조(서버 URL, data URL, 또는 base64)에서 바이트를 추출합니다.
        
        Args:
            image_ref: 이미지 URL (/image/{id}), data URL, 또는 base64 문자열
            
        Returns:
            이미지 바이트 또는 None
        """
        if not image_ref:
            return None
        
        # 서버 내부 URL (/image/{id} 또는 {base_url}/image/{id})
        if "/image/" in image_ref:
            # URL에서 image_id 추출
            image_id = image_ref.split("/image/")[-1].split("?")[0].split("#")[0]
            image_info = await self.get_image(image_id)
            if image_info:
                return image_info["data"]
            return None
        
        # data URL (data:image/...;base64,...)
        if image_ref.startswith("data:"):
            _, data = image_ref.split(",", 1)
            return base64.b64decode(data)
        
        # 순수 base64
        try:
            return base64.b64decode(image_ref)
        except Exception:
            return None
    
    async def _create_zip(
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
                image_bytes = await self._get_image_bytes_from_ref(image_data)
                if image_bytes:
                    filename = f"emoticon_{idx:02d}.{file_format}"
                    zf.writestr(filename, image_bytes)
            
            if icon:
                icon_bytes = await self._get_image_bytes_from_ref(icon)
                if icon_bytes:
                    zf.writestr("icon.png", icon_bytes)
        
        return zip_buffer.getvalue()
    
    async def get_preview_html(self, preview_id: str) -> Optional[str]:
        """저장된 프리뷰 HTML 반환"""
        data = await self._storage.get(preview_key(preview_id))
        if data:
            return data.decode('utf-8')
        return None
    
    async def get_download_zip(self, download_id: str) -> Optional[bytes]:
        """저장된 ZIP 파일 반환"""
        return await self._storage.get(zip_key(download_id))


# 전역 인스턴스
_preview_generator: Optional[PreviewGenerator] = None


def get_preview_generator(base_url: str = "") -> PreviewGenerator:
    """프리뷰 생성기 인스턴스 반환"""
    global _preview_generator
    if _preview_generator is None:
        _preview_generator = PreviewGenerator(base_url)
    return _preview_generator
