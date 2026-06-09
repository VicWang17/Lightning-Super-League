import random

from app.models.player import PlayerPosition
from app.services.player_generator import AttributeGenerator


class TestAttributeGeneratorDiversity:
    def test_ovr_is_normalized_by_position_weight_total(self):
        attrs = {attr: 20 for attr in [
            "sho", "pas", "dri", "spd", "str_", "sta", "acc", "hea", "bal",
            "defe", "tkl", "vis", "cro", "con", "fin", "com", "sav", "ref",
            "pos", "rus", "dec", "fk", "pk",
        ]}

        assert AttributeGenerator.calculate_ovr(PlayerPosition.FW, attrs) == 100
        assert AttributeGenerator.calculate_ovr(PlayerPosition.GK, attrs) == 100

    def test_top_tier_specialists_keep_professional_core_floor(self):
        random.seed(20260608)

        samples = [
            AttributeGenerator.generate(
                PlayerPosition.FW,
                "射手型",
                "标准型",
                age=random.randint(22, 28),
                potential_max=random.randint(90, 100),
                team_ovr=82,
                target_ovr=random.randint(85, 90),
            )
            for _ in range(80)
        ]

        assert min(attrs["spd"] for attrs in samples) >= 12
        assert min(attrs["acc"] for attrs in samples) >= 12

    def test_mid_tier_forwards_can_have_clear_strengths_and_weaknesses(self):
        random.seed(20260605)

        samples = [
            AttributeGenerator.generate(
                PlayerPosition.FW,
                "射手型",
                "标准型",
                age=random.randint(22, 28),
                potential_max=random.randint(85, 94),
                team_ovr=random.randint(50, 60),
            )
            for _ in range(300)
        ]

        distinctive_finishers = [
            attrs for attrs in samples
            if attrs["sho"] >= 15 and attrs["spd"] <= 9
        ]
        assert distinctive_finishers

        fw_core_attrs = ["sho", "dri", "spd", "str_", "sta", "acc", "hea", "fin", "bal", "dec"]
        all_high_core_count = sum(
            1 for attrs in samples
            if all(attrs[attr] >= 13 for attr in fw_core_attrs)
        )
        assert all_high_core_count / len(samples) < 0.12

    def test_generated_attributes_have_position_relevant_spread(self):
        random.seed(20260606)

        for position, archetype in [
            (PlayerPosition.FW, "支点型"),
            (PlayerPosition.MF, "组织型"),
            (PlayerPosition.DF, "中卫型"),
            (PlayerPosition.GK, "传统型"),
        ]:
            spreads = []
            for _ in range(120):
                attrs = AttributeGenerator.generate(
                    position,
                    archetype,
                    "标准型",
                    age=random.randint(21, 30),
                    potential_max=random.randint(75, 94),
                    team_ovr=random.randint(48, 68),
                )
                values = [value for attr, value in attrs.items() if attr != "ovr"]
                spreads.append(max(values) - min(values))

            assert sum(spread >= 7 for spread in spreads) / len(spreads) >= 0.75
