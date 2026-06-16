"""
Tests for PlayerDescriptionService.
"""
import pytest

from app.models.player import Player, PlayerPosition
from app.services.player_description_service import PlayerDescriptionService


def _make_player(position: PlayerPosition, **attrs) -> Player:
    """Build an in-memory Player with the given abilities."""
    defaults = {
        "sho": 10, "pas": 10, "dri": 10,
        "spd": 10, "str_": 10, "sta": 10,
        "acc": 10, "hea": 10, "bal": 10,
        "defe": 10, "tkl": 10, "vis": 10,
        "cro": 10, "con": 10, "fin": 10,
        "com": 10, "sav": 10, "ref": 10,
        "pos": 10, "rus": 10, "dec": 10,
        "fk": 10, "pk": 10,
    }
    defaults.update(attrs)
    return Player(
        name="Test",
        race="western",
        position=position,
        preferred_number=10,
        height=180,
        birth_offset=-22,
        potential_max=70,
        **defaults,
    )


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_description_is_non_empty(seed: int):
    service = PlayerDescriptionService(seed=seed)
    player = _make_player(PlayerPosition.FW, sho=15, spd=14)
    desc = service.generate(player)
    assert desc
    assert len(desc) <= 120


def test_same_position_different_attributes_produces_different_descriptions():
    """同位置、同 OVR 但属性分布不同，描述应明显不同。"""
    service = PlayerDescriptionService(seed=42)
    speed_shooter = _make_player(PlayerPosition.FW, spd=17, acc=16, sho=14)
    pass_playmaker = _make_player(PlayerPosition.FW, pas=17, vis=16, sho=10)

    desc_a = service.generate(speed_shooter)
    desc_b = service.generate(pass_playmaker)
    assert desc_a != desc_b


def test_speed_emphasized_for_fast_player():
    service = PlayerDescriptionService(seed=1)
    player = _make_player(PlayerPosition.FW, spd=18, acc=17, sho=10, pas=10)
    desc = service.generate(player)
    # 速度型球员应出现速度相关字眼
    speed_tokens = {"极速", "闪电", "飞翼", "爆破", "快马"}
    assert any(tok in desc for tok in speed_tokens), f"描述未突出速度: {desc}"


def test_goalkeeper_uses_gk_terms():
    service = PlayerDescriptionService(seed=1)
    player = _make_player(PlayerPosition.GK, sav=16, ref=15, pos=14)
    desc = service.generate(player)
    gk_tokens = {"门神", "守护神", "门线专家", "出击型门将", "定海神针", "扑救", "反应", "出击"}
    assert any(tok in desc for tok in gk_tokens), f"门将描述不合法: {desc}"


def test_low_convergence_for_repeated_generation():
    """同一球员多次生成，结果应有足够多样性。"""
    service = PlayerDescriptionService()
    player = _make_player(PlayerPosition.MF, pas=15, vis=14, spd=12, sho=11)
    results = {service.generate(player) for _ in range(100)}
    assert len(results) >= 5, f"趋同率过高，仅生成 {len(results)} 种描述"


def test_balanced_player_can_be_all_round():
    service = PlayerDescriptionService(seed=7)
    player = _make_player(
        PlayerPosition.MF,
        pas=14, vis=14, dec=14,
        spd=13, dri=13, con=13,
        defe=13, tkl=13,
        sho=12, hea=12, str_=12, sta=12,
    )
    desc = service.generate(player)
    # 能力均衡的球员描述里应当出现传球/组织/调度/核心/发动机/大师等至少一个相关词
    assert any(tok in desc for tok in {"全能型", "组织", "传球", "调度", "核心", "大师", "发动机"}), desc
