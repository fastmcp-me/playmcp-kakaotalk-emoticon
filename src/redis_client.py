"""
Redis 클라이언트 모듈

REDIS_URL 환경변수가 설정된 경우 Redis를 사용하고,
그렇지 않으면 메모리 기반 저장소로 폴백합니다.

환경변수:
    REDIS_URL: Redis 연결 URL (예: redis://localhost:6379 또는 redis://:password@host:port)

사용 예시:
    from src.redis_client import get_storage, get_ttl
    
    storage = get_storage()
    
    # JSON 데이터 저장/조회
    await storage.set_json("task:abc123", {"status": "running"}, ttl=get_ttl("task"))
    data = await storage.get_json("task:abc123")
    
    # 바이너리 데이터 저장/조회
    await storage.set("image:xyz789", image_bytes, ttl=get_ttl("image"))
    image_data = await storage.get("image:xyz789")
"""
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod


# TTL 설정 (초 단위)
# 환경변수로 커스터마이징 가능: REDIS_TTL_IMAGE=86400 등

DEFAULT_TTL = {
    "task": int(os.environ.get("REDIS_TTL_TASK", 86400)),       # 24시간
    "preview": int(os.environ.get("REDIS_TTL_PREVIEW", 86400)), # 24시간
    "image": int(os.environ.get("REDIS_TTL_IMAGE", 86400)),     # 24시간 (검증 전까지 유지)
    "zip": int(os.environ.get("REDIS_TTL_ZIP", 43200)),         # 12시간
    "status": int(os.environ.get("REDIS_TTL_STATUS", 86400)),   # 24시간
}


class BaseStorage(ABC):
    """저장소 기본 인터페이스"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[bytes]:
        """키에 해당하는 값 조회 (바이너리)"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: bytes, ttl: Optional[int] = None) -> bool:
        """키-값 저장 (바이너리)"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """키 삭제"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        pass
    
    @abstractmethod
    async def keys(self, pattern: str) -> List[str]:
        """패턴에 맞는 키 목록 조회"""
        pass
    
    async def get_json(self, key: str) -> Optional[Any]:
        """JSON으로 저장된 값 조회"""
        data = await self.get(key)
        if data:
            return json.loads(data.decode('utf-8'))
        return None
    
    async def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """값을 JSON으로 저장 (datetime 객체 자동 직렬화)"""
        data = json.dumps(value, ensure_ascii=False, default=self._json_serializer).encode('utf-8')
        return await self.set(key, data, ttl)
    
    @staticmethod
    def _json_serializer(obj: Any) -> str:
        """JSON 직렬화 커스텀 핸들러"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, 'value'):  # Enum 처리
            return obj.value
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class MemoryStorage(BaseStorage):
    """
    메모리 기반 저장소 (Redis 미설정 시 폴백)
    
    주의: 서버 재시작 시 모든 데이터가 사라집니다.
    """
    
    # 메모리 사용량 제한을 위한 최대 항목 수
    MAX_ITEMS = 1000
    
    def __init__(self):
        self._data: Dict[str, bytes] = {}
        self._expiry: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
    
    async def _cleanup_expired(self) -> None:
        """만료된 키 정리"""
        now = datetime.now()
        expired_keys = [
            key for key, expiry in self._expiry.items()
            if expiry < now
        ]
        for key in expired_keys:
            self._data.pop(key, None)
            self._expiry.pop(key, None)
    
    async def _enforce_max_items(self) -> None:
        """최대 항목 수 초과 시 오래된 항목 삭제"""
        if len(self._data) <= self.MAX_ITEMS:
            return
        
        # 만료 시간이 있는 항목 중 가장 오래된 것부터 삭제
        items_with_expiry = [
            (key, expiry) for key, expiry in self._expiry.items()
        ]
        items_with_expiry.sort(key=lambda x: x[1])
        
        # 절반 정리
        items_to_remove = len(self._data) - (self.MAX_ITEMS // 2)
        for key, _ in items_with_expiry[:items_to_remove]:
            self._data.pop(key, None)
            self._expiry.pop(key, None)
    
    async def get(self, key: str) -> Optional[bytes]:
        async with self._lock:
            # 만료 확인
            if key in self._expiry and self._expiry[key] < datetime.now():
                self._data.pop(key, None)
                self._expiry.pop(key, None)
                return None
            
            return self._data.get(key)
    
    async def set(self, key: str, value: bytes, ttl: Optional[int] = None) -> bool:
        async with self._lock:
            await self._cleanup_expired()
            await self._enforce_max_items()
            
            self._data[key] = value
            if ttl:
                self._expiry[key] = datetime.now() + timedelta(seconds=ttl)
            elif key in self._expiry:
                del self._expiry[key]
            return True
    
    async def delete(self, key: str) -> bool:
        async with self._lock:
            self._data.pop(key, None)
            self._expiry.pop(key, None)
            return True
    
    async def exists(self, key: str) -> bool:
        async with self._lock:
            if key in self._expiry and self._expiry[key] < datetime.now():
                self._data.pop(key, None)
                self._expiry.pop(key, None)
                return False
            return key in self._data
    
    async def keys(self, pattern: str) -> List[str]:
        """패턴에 맞는 키 목록 조회 (간단한 prefix 패턴만 지원)"""
        async with self._lock:
            await self._cleanup_expired()
            
            if pattern == "*":
                return list(self._data.keys())
            
            # prefix 패턴 지원 (예: "task:*")
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                return [k for k in self._data.keys() if k.startswith(prefix)]
            
            # 정확히 일치하는 키만
            return [k for k in self._data.keys() if k == pattern]
    
    async def close(self) -> None:
        """연결 종료 (메모리 저장소는 아무것도 하지 않음)"""
        pass


class RedisStorage(BaseStorage):
    """
    Redis 기반 저장소
    
    특징:
    - Connection pooling (redis-py 내장)
    - 자동 재연결 (retry_on_timeout)
    - 바이너리 데이터 지원
    """
    
    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._redis = None
        self._lock = asyncio.Lock()
        self._connection_error_count = 0
        self._max_retries = 3
    
    async def _get_client(self):
        """Redis 클라이언트 가져오기 (지연 연결 + 자동 재연결)"""
        if self._redis is None:
            async with self._lock:
                if self._redis is None:
                    import redis.asyncio as aioredis
                    
                    self._redis = aioredis.from_url(
                        self._redis_url,
                        encoding=None,  # 바이너리 데이터 지원
                        decode_responses=False,
                        retry_on_timeout=True,
                        socket_connect_timeout=5,
                        socket_timeout=10,
                        health_check_interval=30,
                    )
                    self._connection_error_count = 0
        return self._redis
    
    async def _execute_with_retry(self, operation: str, func):
        """재시도 로직이 포함된 Redis 명령 실행"""
        last_error = None
        
        for attempt in range(self._max_retries):
            try:
                client = await self._get_client()
                return await func(client)
            except Exception as e:
                last_error = e
                self._connection_error_count += 1
                
                # 연결 에러가 많으면 클라이언트 재생성
                if self._connection_error_count > 5:
                    async with self._lock:
                        if self._redis:
                            try:
                                await self._redis.close()
                            except Exception:
                                pass
                            self._redis = None
                            self._connection_error_count = 0
                
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
        
        print(f"Redis {operation} failed after {self._max_retries} retries: {last_error}")
        return None
    
    async def get(self, key: str) -> Optional[bytes]:
        result = await self._execute_with_retry(
            f"GET {key}",
            lambda client: client.get(key)
        )
        return result
    
    async def set(self, key: str, value: bytes, ttl: Optional[int] = None) -> bool:
        async def _set(client):
            if ttl:
                await client.setex(key, ttl, value)
            else:
                await client.set(key, value)
            return True
        
        result = await self._execute_with_retry(f"SET {key}", _set)
        return result is True
    
    async def delete(self, key: str) -> bool:
        result = await self._execute_with_retry(
            f"DELETE {key}",
            lambda client: client.delete(key)
        )
        return result is not None
    
    async def exists(self, key: str) -> bool:
        result = await self._execute_with_retry(
            f"EXISTS {key}",
            lambda client: client.exists(key)
        )
        return result is not None and result > 0
    
    async def keys(self, pattern: str) -> List[str]:
        """패턴에 맞는 키 목록 조회"""
        result = await self._execute_with_retry(
            f"KEYS {pattern}",
            lambda client: client.keys(pattern)
        )
        if result is None:
            return []
        return [k.decode('utf-8') if isinstance(k, bytes) else k for k in result]
    
    async def close(self) -> None:
        """연결 종료"""
        async with self._lock:
            if self._redis:
                try:
                    await self._redis.close()
                except Exception:
                    pass
                self._redis = None


# 전역 저장소 인스턴스
_storage: Optional[BaseStorage] = None


def get_storage() -> BaseStorage:
    """
    저장소 인스턴스 반환 (싱글톤)
    
    REDIS_URL 환경변수가 설정되어 있으면 Redis를 사용하고,
    그렇지 않으면 메모리 기반 저장소를 사용합니다.
    """
    global _storage
    
    if _storage is None:
        redis_url = os.environ.get("REDIS_URL")
        
        if redis_url:
            print(f"Using Redis storage")
            _storage = RedisStorage(redis_url)
        else:
            print("REDIS_URL not set, using in-memory storage (data will be lost on restart)")
            _storage = MemoryStorage()
    
    return _storage


def get_ttl(data_type: str) -> int:
    """
    데이터 타입에 따른 TTL(초) 반환
    
    Args:
        data_type: 데이터 타입 ("task", "preview", "image", "zip", "status")
        
    Returns:
        TTL 초 단위
    """
    return DEFAULT_TTL.get(data_type, DEFAULT_TTL["preview"])


# 키 생성 헬퍼 함수들
def task_key(task_id: str) -> str:
    """작업 키 생성"""
    return f"task:{task_id}"


def preview_key(preview_id: str) -> str:
    """프리뷰 키 생성"""
    return f"preview:{preview_id}"


def image_key(image_id: str) -> str:
    """이미지 키 생성"""
    return f"image:{image_id}"


def zip_key(download_id: str) -> str:
    """ZIP 키 생성"""
    return f"zip:{download_id}"


def status_key(task_id: str) -> str:
    """상태 페이지 키 생성"""
    return f"status:{task_id}"
