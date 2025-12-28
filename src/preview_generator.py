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
        }
        .input-field::placeholder {
            color: var(--text-muted);
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
                <div class="input-field-wrapper">
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
                <button class="panel-category-btn active">이모티콘</button>
                <button class="panel-category-btn">미니 이모티콘</button>
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
            
            <div class="emoticon-grid" id="emoticonGrid">
                {% for plan in plans %}
                <div class="emoticon-item" data-index="{{ loop.index }}" data-desc="{{ plan.description }}">
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
        
        let isPanelOpen = false;
        let selectedEmoticon = null;
        let isStarred = false;
        let isDragging = false;
        let startY = 0;
        let panelHeight = 0;
        
        // Update send button state
        function updateSendButton() {
            if (messageInput.value.trim() || selectedEmoticon) {
                sendBtn.classList.add('active');
                sendBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>';
            } else {
                sendBtn.classList.remove('active');
                sendBtn.textContent = '#';
            }
        }
        
        messageInput.addEventListener('input', updateSendButton);
        
        // Send message or emoticon
        function sendMessage() {
            if (selectedEmoticon) {
                addMessage(`[${selectedEmoticon.index}]`, 'emoticon', selectedEmoticon.desc);
                closeSelection();
                return;
            }
            
            const text = messageInput.value.trim();
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
        }
        .input-field::placeholder {
            color: var(--text-muted);
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
                <div class="input-field-wrapper">
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
                <button class="panel-category-btn active">이모티콘</button>
                <button class="panel-category-btn">미니 이모티콘</button>
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
            
            <div class="emoticon-grid" id="emoticonGrid">
                {% for emoticon in emoticons %}
                <div class="emoticon-item" data-index="{{ loop.index }}" data-src="{{ emoticon.image_data }}">
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
        
        let isPanelOpen = false;
        let selectedEmoticon = null;
        let isStarred = false;
        let isDragging = false;
        let startY = 0;
        let panelHeight = 0;
        
        // Update send button state
        function updateSendButton() {
            if (messageInput.value.trim() || selectedEmoticon) {
                sendBtn.classList.add('active');
                sendBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>';
            } else {
                sendBtn.classList.remove('active');
                sendBtn.textContent = '#';
            }
        }
        
        messageInput.addEventListener('input', updateSendButton);
        
        // Send message or emoticon
        function sendMessage() {
            if (selectedEmoticon) {
                addMessage('', 'emoticon', selectedEmoticon.src);
                closeSelection();
                return;
            }
            
            const text = messageInput.value.trim();
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
        self._image_storage: Dict[str, Dict[str, Any]] = {}  # image_id -> {"data": bytes, "mime_type": str}
    
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
    
    def store_image(self, image_data: bytes, mime_type: str = "image/png") -> str:
        """
        이미지를 저장하고 URL을 반환합니다.
        
        Args:
            image_data: 이미지 바이트 데이터
            mime_type: 이미지 MIME 타입
            
        Returns:
            이미지 URL (예: /image/{image_id} 또는 {base_url}/image/{image_id})
        """
        image_id = self._generate_short_id()
        self._image_storage[image_id] = {
            "data": image_data,
            "mime_type": mime_type
        }
        
        if self.base_url:
            return f"{self.base_url}/image/{image_id}"
        else:
            return f"/image/{image_id}"
    
    def store_base64_image(self, base64_data: str) -> str:
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
        return self.store_image(image_bytes, mime_type)
    
    def get_image(self, image_id: str) -> Optional[Dict[str, Any]]:
        """
        저장된 이미지 정보 반환
        
        Args:
            image_id: 이미지 ID
            
        Returns:
            {"data": bytes, "mime_type": str} 또는 None
        """
        return self._image_storage.get(image_id)
    
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
            프리뷰 페이지 URL
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
            return f"/preview/{preview_id}"
    
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
            download_url = f"/download/{download_id}"
        
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
            preview_url = f"/preview/{preview_id}"
        
        return preview_url, download_url
    
    def _get_image_bytes_from_ref(self, image_ref: str) -> Optional[bytes]:
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
            image_info = self.get_image(image_id)
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
                image_bytes = self._get_image_bytes_from_ref(image_data)
                if image_bytes:
                    filename = f"emoticon_{idx:02d}.{file_format}"
                    zf.writestr(filename, image_bytes)
            
            if icon:
                icon_bytes = self._get_image_bytes_from_ref(icon)
                if icon_bytes:
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
