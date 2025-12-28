"""
비동기 이미지 생성 작업 관리 모듈

Redis를 사용하여 작업 상태를 저장합니다.
REDIS_URL이 설정되지 않은 경우 메모리 기반 저장소로 폴백합니다.
"""
import secrets
import string
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.redis_client import get_storage, get_ttl, task_key


class TaskStatus(str, Enum):
    """작업 상태"""
    PENDING = "pending"       # 대기 중
    RUNNING = "running"       # 실행 중
    COMPLETED = "completed"   # 완료
    FAILED = "failed"         # 실패


@dataclass
class GenerationTask:
    """이미지 생성 작업"""
    task_id: str
    status: TaskStatus
    emoticon_type: str
    total_count: int
    completed_count: int = 0
    current_description: str = ""
    emoticons: List[Dict[str, Any]] = field(default_factory=list)
    icon: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (Redis 저장용)"""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "emoticon_type": self.emoticon_type,
            "total_count": self.total_count,
            "completed_count": self.completed_count,
            "current_description": self.current_description,
            "progress_percent": round((self.completed_count / self.total_count) * 100) if self.total_count > 0 else 0,
            "emoticons": self.emoticons,
            "icon": self.icon,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenerationTask":
        """딕셔너리에서 객체 생성 (Redis 복원용)"""
        # datetime 파싱
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()
        
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.now()
        
        # TaskStatus enum 파싱
        status = data.get("status", "pending")
        if isinstance(status, str):
            status = TaskStatus(status)
        
        return cls(
            task_id=data["task_id"],
            status=status,
            emoticon_type=data["emoticon_type"],
            total_count=data["total_count"],
            completed_count=data.get("completed_count", 0),
            current_description=data.get("current_description", ""),
            emoticons=data.get("emoticons", []),
            icon=data.get("icon"),
            error_message=data.get("error_message"),
            created_at=created_at,
            updated_at=updated_at
        )


class TaskStorage:
    """작업 저장소 (Redis 기반)"""
    
    def __init__(self):
        self._storage = get_storage()
    
    def _generate_task_id(self, length: int = 12) -> str:
        """짧은 랜덤 작업 ID 생성"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    async def _save_task(self, task: GenerationTask) -> None:
        """작업을 저장소에 저장"""
        key = task_key(task.task_id)
        await self._storage.set_json(key, task.to_dict(), ttl=get_ttl("task"))
    
    async def create_task(self, emoticon_type: str, total_count: int) -> GenerationTask:
        """새 작업 생성"""
        task_id = self._generate_task_id()
        task = GenerationTask(
            task_id=task_id,
            status=TaskStatus.PENDING,
            emoticon_type=emoticon_type,
            total_count=total_count
        )
        await self._save_task(task)
        return task
    
    async def get_task(self, task_id: str) -> Optional[GenerationTask]:
        """작업 조회"""
        key = task_key(task_id)
        data = await self._storage.get_json(key)
        if data:
            return GenerationTask.from_dict(data)
        return None
    
    async def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """작업 상태 업데이트"""
        task = await self.get_task(task_id)
        if task:
            task.status = status
            task.updated_at = datetime.now()
            await self._save_task(task)
    
    async def update_task_progress(
        self, 
        task_id: str, 
        completed_count: int, 
        current_description: str = ""
    ) -> None:
        """작업 진행 상황 업데이트"""
        task = await self.get_task(task_id)
        if task:
            task.completed_count = completed_count
            task.current_description = current_description
            task.updated_at = datetime.now()
            await self._save_task(task)
    
    async def add_emoticon(self, task_id: str, emoticon: Dict[str, Any]) -> None:
        """생성된 이모티콘 추가"""
        task = await self.get_task(task_id)
        if task:
            task.emoticons.append(emoticon)
            task.updated_at = datetime.now()
            await self._save_task(task)
    
    async def set_icon(self, task_id: str, icon: Dict[str, Any]) -> None:
        """아이콘 설정"""
        task = await self.get_task(task_id)
        if task:
            task.icon = icon
            task.updated_at = datetime.now()
            await self._save_task(task)
    
    async def set_error(self, task_id: str, error_message: str) -> None:
        """에러 설정"""
        task = await self.get_task(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = error_message
            task.updated_at = datetime.now()
            await self._save_task(task)
    
    async def complete_task(self, task_id: str) -> None:
        """작업 완료"""
        task = await self.get_task(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.updated_at = datetime.now()
            await self._save_task(task)


# 전역 인스턴스
_task_storage: Optional[TaskStorage] = None


def get_task_storage() -> TaskStorage:
    """작업 저장소 인스턴스 반환"""
    global _task_storage
    if _task_storage is None:
        _task_storage = TaskStorage()
    return _task_storage
