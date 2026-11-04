# Climbing Support Team

Projekt MVP wirtualnego zespołu specjalistów wspierających osobę wspinającą się:
trenera wspinaczkowego, dietetyka ogólnego i fizjoterapeutę. System prowadzi
Supervisor, który kieruje sprawę do właściwych specjalistów. Odpowiedź dla
użytkownika składa Synthesizer.

## Cel MVP

- przechowywanie profilu, celu, planu i historii użytkownika;
- routing pytań do jednego lub wielu agentów;
- tworzenie uzasadnionych rekomendacji;
- przedstawianie istotnych zmian jako propozycji wymagających akceptacji;
- zachowanie źródeł i granic pewności rekomendacji.

## Układ katalogów

- `docs/` — decyzje produktowe i architektura;
- `agents/` — odpowiedzialności oraz granice agentów;
- `knowledge/` — zasady budowy bazy wiedzy i źródeł;
- `schemas/` — kontrakty danych wymienianych przez komponenty;
- `data/` — przyszłe dane lokalne i migracje (bez danych użytkowników w repozytorium);
- `services/` — przyszłe moduły aplikacji;
- `tests/` — przyszłe scenariusze testowe.

Szczegółowy plan pierwszej implementacji: [docs/03-mvp-roadmap.md](docs/03-mvp-roadmap.md).
