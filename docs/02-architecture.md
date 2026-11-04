# Architektura v0.1

```text
Użytkownik
    │
    ▼
Supervisor ──────► specjaliści: trener / dietetyk / fizjoterapeuta
    │                                             │
    ├────────────► Memory Manager ◄───────────────┤
    │                                             │
    ▼                                             ▼
Policy / Validator ◄──── PROPOSAL + EvidenceRecord
    │
    ▼
Synthesizer ──────► odpowiedź dla użytkownika
```

## Komponenty

| Komponent | Odpowiedzialność |
| --- | --- |
| Supervisor | Rozpoznaje domenę, dobiera agentów i wymagany kontekst. |
| Memory Manager | Zapisuje fakty, zdarzenia, podsumowania i preferencje. |
| Agenci specjaliści | Analizują sprawę wyłącznie w granicach swojej specjalizacji. |
| Policy / Validator | Sprawdza format, bezpieczeństwo i wymóg akceptacji. |
| Synthesizer | Łączy zatwierdzone wyniki w jedną, zrozumiałą odpowiedź. |

## Przepływ

1. Supervisor klasyfikuje pytanie i tworzy zadanie.
2. Memory Manager zwraca minimalny, istotny kontekst.
3. Jeden lub wielu specjalistów tworzy ustrukturyzowaną rekomendację.
4. Wynik zawiera dowody (`EvidenceRecord`) i poziom pewności.
5. Validator oznacza zmianę planu jako propozycję lub odrzuca wynik.
6. Synthesizer przedstawia odpowiedź i, gdy trzeba, prosi o akceptację.

## Uruchomienie

Na początku wszystkie moduły mogą działać lokalnie na jednym komputerze. Granice
komponentów i kontrakty w `schemas/` pozwolą później rozdzielić je między procesy,
maszyny lub usługi chmurowe bez zmiany logiki biznesowej.
