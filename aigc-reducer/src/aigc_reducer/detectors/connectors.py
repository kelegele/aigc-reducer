"""模板化连接词检测器 — 检测 AI 高频连接词。"""

import yaml
import os
from aigc_reducer.parser import Paragraph


class ConnectorDetector:
    def analyze(self, paragraph: Paragraph) -> float:
        text = paragraph.text
        text_lower = text.lower()

        data_path = os.path.join(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(__file__)
                    )
                )
            ),
            "data",
            "ai_connectors.yaml",
        )
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            matches = 0
            for connector in data.get("connectors", {}).get("high_frequency", []):
                if connector.lower() in text_lower:
                    matches += 3
            for connector in data.get("connectors", {}).get("medium_frequency", []):
                if connector.lower() in text_lower:
                    matches += 2
            for connector in data.get("connectors", {}).get("english_connectors", []):
                if connector.lower() in text_lower:
                    matches += 1

            if matches >= 8:
                return 90
            elif matches >= 5:
                return 75
            elif matches >= 3:
                return 55
            elif matches >= 2:
                return 35
            elif matches >= 1:
                return 15
            else:
                return 5
        else:
            return 5
