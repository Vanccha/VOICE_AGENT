"""Konuşmayı ekrana da yazdıran ortak voice workflow."""

from __future__ import annotations

from collections.abc import AsyncIterator

from agents.voice import SingleAgentVoiceWorkflow


class PrintingWorkflow(SingleAgentVoiceWorkflow):
    """SingleAgentVoiceWorkflow ile aynı, ama söylenenleri terminale de yazar.

    Boş (anlaşılamayan) kayıtlarda ajanı hiç çalıştırmaz.
    """

    async def run(self, transcription: str) -> AsyncIterator[str]:
        text = transcription.strip()
        if len(text) < 2:
            print("\n  (Ne dediğini anlayamadım, tekrar dene)")
            return

        print(f"\n[Sen] {text}")
        agent_before = self._current_agent.name
        print(f"[{agent_before}] ", end="", flush=True)
        async for chunk in super().run(text):
            print(chunk, end="", flush=True)
            yield chunk
        print()
        if self._current_agent.name != agent_before:
            print(f"  (aktarıldı -> {self._current_agent.name})")
