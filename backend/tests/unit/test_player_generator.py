import random
from collections import Counter

from app.models.player import PlayerPosition
from app.services.player_generator import AttributeGenerator, PlayerGenerator


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

    def test_initial_top_league_elites_are_rare(self):
        random.seed(20260610)
        generator = PlayerGenerator()

        elite_targets = sum(
            sum(1 for target in generator._generate_initial_squad_targets(1, 15) if target >= 90)
            for _ in range(32)
        )
        second_level_elite_targets = sum(
            sum(1 for target in generator._generate_initial_squad_targets(2, 15) if target >= 90)
            for _ in range(32)
        )

        assert 10 <= elite_targets <= 15
        assert second_level_elite_targets == 0

    def test_generated_high_attributes_taper_toward_ceiling(self):
        random.seed(20260612)
        counts = Counter()
        positions_and_archetypes = [
            (PlayerPosition.FW, "射手型"),
            (PlayerPosition.MF, "组织型"),
            (PlayerPosition.DF, "中卫型"),
            (PlayerPosition.GK, "传统型"),
        ]

        for _ in range(120):
            for position, archetype in positions_and_archetypes:
                attrs = AttributeGenerator.generate(
                    position,
                    archetype,
                    "标准型",
                    age=random.randint(22, 29),
                    potential_max=random.randint(80, 100),
                    team_ovr=82,
                    target_ovr=random.randint(82, 90),
                )
                counts.update(value for attr, value in attrs.items() if attr != "ovr" and value >= 16)

        assert counts[16] > counts[17] > counts[18] > counts[19] > counts[20]

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
