"""
多账号轮询 Key Pool
- Round-robin 选择下一个可用 key
- 单 key 额度耗尽/限流时自动降级（标记冷却）
- 冷却到期自动恢复
"""
import time
import asyncio
from typing import List, Dict, Optional


class KeyState:
    """单个 Key 的状态"""
    __slots__ = ('key', 'cooldown_until', 'fail_count', 'total_calls', 'total_errors')

    def __init__(self, key: str):
        self.key = key
        self.cooldown_until: float = 0.0   # 冷却到期时间戳
        self.fail_count: int = 0           # 连续失败次数
        self.total_calls: int = 0          # 总调用次数
        self.total_errors: int = 0         # 总错误次数

    @property
    def is_available(self) -> bool:
        """是否可用（不在冷却期）"""
        return time.time() >= self.cooldown_until

    def mark_error(self, retry_after: float = 60.0):
        """标记错误，进入冷却"""
        self.fail_count += 1
        self.total_errors += 1
        # 冷却时间：基础 30s + 每次失败递增 30s，上限 5 分钟
        cooldown = min(30.0 + self.fail_count * 30.0, 300.0)
        # 如果 API 返回了 retry-after，使用它
        if retry_after > 0:
            cooldown = max(cooldown, retry_after)
        self.cooldown_until = time.time() + cooldown

    def mark_success(self):
        """标记成功，重置连续失败计数"""
        self.fail_count = 0
        self.total_calls += 1

    def to_dict(self) -> dict:
        remaining = max(0, self.cooldown_until - time.time())
        return {
            'key': self.key[:8] + '...' + self.key[-4:] if len(self.key) > 12 else self.key,
            'available': self.is_available,
            'cooldown_remaining': round(remaining, 1),
            'fail_count': self.fail_count,
            'total_calls': self.total_calls,
            'total_errors': self.total_errors,
        }


class KeyPool:
    """
    多账号轮询池
    
    用法:
        pool = KeyPool(["key1", "key2", "key3"])
        key = await pool.get_key()   # round-robin 选一个可用的
        pool.mark_success(key)       # 成功
        pool.mark_error(key, retry_after=60)  # 失败，冷却 60s
    """

    def __init__(self, keys: List[str]):
        self._states: List[KeyState] = [KeyState(k) for k in keys if k and k.strip()]
        self._index: int = 0  # round-robin 指针
        self._lock = asyncio.Lock()

    @property
    def size(self) -> int:
        return len(self._states)

    @property
    def available_count(self) -> int:
        return sum(1 for s in self._states if s.is_available)

    async def get_key(self) -> Optional[str]:
        """
        获取下一个可用的 key（round-robin）
        如果所有 key 都在冷却中，返回 None
        """
        if not self._states:
            return None

        async with self._lock:
            n = len(self._states)
            # 从当前位置开始，尝试所有 key
            for i in range(n):
                idx = (self._index + i) % n
                state = self._states[idx]
                if state.is_available:
                    self._index = (idx + 1) % n
                    return state.key

            # 所有 key 都在冷却中，找到最早恢复的那个
            earliest = min(self._states, key=lambda s: s.cooldown_until)
            return earliest.key

    def mark_success(self, key: str):
        """标记 key 调用成功"""
        for state in self._states:
            if state.key == key:
                state.mark_success()
                return

    def mark_error(self, key: str, retry_after: float = 0.0):
        """标记 key 调用失败，进入冷却"""
        for state in self._states:
            if state.key == key:
                state.mark_error(retry_after)
                return

    def get_status(self) -> List[dict]:
        """获取所有 key 的状态（用于 UI 展示）"""
        return [s.to_dict() for s in self._states]

    def update_keys(self, keys: List[str]):
        """热更新 key 列表（保留未变更 key 的状态）"""
        filtered = [k for k in keys if k and k.strip()]
        old_keys = [s.key for s in self._states]
        if filtered == old_keys:
            return  # key 列表没变，不重置 index
        old_map = {s.key: s for s in self._states}
        new_states = []
        for k in filtered:
            if k in old_map:
                new_states.append(old_map[k])
            else:
                new_states.append(KeyState(k))
        self._states = new_states
        self._index = 0


# ──────────────────────────────────────────────────────────────
# 全局 Pool 管理器
# ──────────────────────────────────────────────────────────────
class KeyPoolManager:
    """管理所有 Provider 的 KeyPool 实例"""

    def __init__(self):
        self._pools: Dict[str, KeyPool] = {}

    def get_or_create(self, provider_id: str, keys: List[str]) -> KeyPool:
        """获取或创建 provider 的 key pool"""
        if provider_id not in self._pools:
            self._pools[provider_id] = KeyPool(keys)
        else:
            self._pools[provider_id].update_keys(keys)
        return self._pools[provider_id]

    def remove(self, provider_id: str):
        """移除 provider 的 pool"""
        self._pools.pop(provider_id, None)

    def get_all_status(self) -> Dict[str, List[dict]]:
        """获取所有 pool 状态"""
        return {pid: pool.get_status() for pid, pool in self._pools.items()}


# 全局单例
key_pool_manager = KeyPoolManager()
