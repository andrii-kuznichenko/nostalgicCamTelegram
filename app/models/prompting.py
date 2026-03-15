from dataclasses import dataclass


@dataclass(slots=True)
class PromptPackage:
    prompt: str
    negative_prompt: str
    selected_mode: str
    applied_blocks: list[str]
