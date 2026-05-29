"""
Training state provider - 训练状态提供者（空实现）
按设计文档 7.3 节实现，预留接口供未来训练系统接入。
"""


class TrainingStateProvider:
    """训练状态提供者 - 空实现
    
    未来训练系统完成后，替换此 provider 的实现即可，
    不需要修改合同/比赛快照逻辑。
    """
    
    async def get_player_state_score(self, player_id: str) -> int:
        """获取训练对状态的影响分"""
        return 0
    
    async def get_player_stamina_modifier(self, player_id: str) -> float:
        """获取训练对 stamina 的修正值"""
        return 0.0
    
    async def get_attribute_modifiers(self, player_id: str) -> dict[str, float]:
        """获取训练对属性的修正（指定属性短期加成）"""
        return {}
