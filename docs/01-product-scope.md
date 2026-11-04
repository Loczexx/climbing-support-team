# Zakres produktu v0.1

## Problem

Użytkownik łączy wspinanie, trening uzupełniający, żywienie i regenerację.
Informacje są rozproszone, a zmiana w jednej dziedzinie może wpływać na inną.

## Propozycja

System współpracujących agentów utrzymuje wspólny, minimalny kontekst
użytkownika i przekazuje sprawy do właściwego specjalisty. Nie zastępuje lekarza,
fizjoterapeuty ani dietetyka klinicznego.

## MVP

1. Profil użytkownika i cel wspinaczkowy.
2. Aktualny plan oraz wpisy treningowe.
3. Podstawowe dane o regeneracji i ograniczeniach.
4. Routing pytania przez Supervisora.
5. Rekomendacje trenera i dietetyka; w przypadku bólu aktywacja bramki RESTRICTION i odesłanie do opieki medycznej (pełny agent fizjoterapeutyczny poza Fazą 1).
6. Propozycje zmian planu wymagające potwierdzenia użytkownika.
7. Zapis źródła, ograniczeń i pewności dla rekomendacji.

## Poza MVP

- diagnostyka i leczenie;
- automatyczne wykonywanie istotnych zmian planu;
- analiza zdjęć jedzenia;
- integracje z zegarkami i aplikacjami treningowymi;
- analiza biomechaniczna obrazu/wideo.

## Zasady bezpieczeństwa

- Dane są udostępniane agentowi tylko, gdy są potrzebne do zadania.
- Objawy bólu, uraz lub ograniczenia blokują samodzielne zalecenia obciążające.
- Niepewność, ograniczenia dowodów i brakujące dane są komunikowane wprost.
- Każda trwała zmiana planu trafia do użytkownika jako `PROPOSAL`.
