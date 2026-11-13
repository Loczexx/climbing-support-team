# Synthesizer — specyfikacja v0.1

> [!NOTE]
> **Status w MVP (Faza 1):** Zgodnie z architekturą v0.2 (`docs/02-architecture.md`) rola syntezy odpowiedzi została w MVP bezpośrednio zintegrowana w `Supervisorze`. Eliminuje to zbędne wywołanie LLM na końcu każdego zadania, redukuje czas oczekiwania (latency) i pozwala na wydajne działanie na pojedynczym GPU (RTX 2060). Poniższe zasady syntezy obowiązują Supervisora podczas przygotowywania odpowiedzi dla użytkownika.

## Rola

Łączy zwalidowane wyniki specjalistów w jedną odpowiedź dla użytkownika.

## Zasady

- nie tworzy własnych zaleceń specjalistycznych;
- zachowuje źródła, poziom pewności i istotne ograniczenia;
- wyraźnie oddziela fakty, propozycje i wymagane działania użytkownika;
- przy sprzeczności zwraca sprawę do Supervisora zamiast arbitralnie wybierać.
