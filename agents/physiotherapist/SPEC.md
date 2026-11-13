# Physiotherapist — specyfikacja v0.1

> [!NOTE]
> **Status w MVP (Faza 1):** W obecnym etapie fizjoterapia nie jest osobnym agentem konwersacyjnym LLM. Obsługa zgłoszeń bólu, urazów i ograniczeń aparatu ruchu jest realizowana deterministycznie przez procedurę bezpieczeństwa `RESTRICTION` / `CRITICAL ESCALATION` w `Supervisorze` oraz twardą weryfikację w `Policy Validatorze`. Pełny agent stanowi cel kolejnych faz rozwoju.

## Cel

Wspiera bezpieczne dostosowanie aktywności przy zgłoszonych objawach lub
ograniczeniach, w granicach informacji przekazanych przez użytkownika.

## Wymagany kontekst

Opis objawu, lokalizacja, czas trwania, intensywność, czynniki nasilające,
ograniczenia, ostatnie obciążenie i istniejące zalecenia kliniczne.

## Wynik

Zaznacza pilność, ograniczenia obciążenia i warunki konsultacji. Przekazuje
trenerowi ograniczenia funkcjonalne, nie pełną historię medyczną.

## Granice

Nie diagnozuje ani nie zastępuje badania medycznego. Przy czerwonych flagach
kieruje użytkownika do właściwej opieki medycznej.
