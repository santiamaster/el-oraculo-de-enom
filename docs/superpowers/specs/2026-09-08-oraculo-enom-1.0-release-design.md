# El Oráculo de ENOM — Diseño de cierre hacia 1.0.0

## Objetivo

Convertir el candidato local `0.1.0` ya implementado y probado en una publicación
`1.0.0` verificable para Windows, sin incorporar funciones nuevas. El trabajo se
divide en ocho tramos independientes para limitar el contexto, revisar cada cambio
y detenerse antes de avanzar al siguiente.

## Punto de partida

- La funcionalidad definida en
  `docs/superpowers/specs/2026-09-07-oraculo-enom-general-dice-design.md` está
  implementada en `feature/initial-app`.
- La suite local, compilación de bytecode, revisión del diff y bundle local de
  PyInstaller ya tuvieron una pasada verde.
- La versión continúa en `0.1.0`.
- No se hizo push de la rama, pull request, validación del artefacto real de
  Windows, merge, tag ni GitHub Release.
- Faltan los materiales profesionales de distribución: aceptación manual,
  avisos/licencias de terceros, changelog, SBOM y hashes.

## Alcance aprobado

El cierre comprende exactamente estos tramos:

| Tramo | Resultado |
|---|---|
| 10 | Candidato local limpio, reproducible y con registro de estado |
| 11 | Rama remota, pull request y CI de Windows verde |
| 12 | Artefacto de Windows descargado e inspeccionado |
| 13 | Aceptación funcional manual documentada en Windows |
| 14 | Licencias y avisos de terceros incluidos y verificados |
| 15 | Changelog, notas, SBOM y SHA-256 generados por CI |
| 16 | Candidato final versionado como `1.0.0` y completamente validado |
| 17 | Pull request integrado, tag y GitHub Release publicados y verificados |

## Reglas de ejecución

- Se ejecuta un solo tramo por autorización explícita del usuario.
- Cada tramo empieza releyendo el estado real de Git, el plan y el registro de
  avance; no se presupone que una acción externa haya terminado.
- Cada tramo termina con pruebas o inspecciones adecuadas, revisión del diff,
  commit y actualización del pull request cuando este exista.
- Después del informe de cada tramo se detiene el trabajo. Nunca se inicia el
  siguiente automáticamente.
- Un defecto descubierto se corrige en el tramo que lo revela si está dentro de
  su alcance. Si exige rediseño o amplía el alcance, se registra y se detiene el
  tramo para acordar una corrección.
- Los bundles, ZIP descargados y directorios temporales no se incorporan al
  repositorio.
- No se fuerza ningún push, no se reescribe historial compartido y no se publica
  una release antes del Tramo 17.

## Criterios de publicación

La versión `1.0.0` solo puede publicarse cuando concurran todas estas condiciones:

1. suite automatizada, compilación y diff-check verdes;
2. workflow de Windows verde sobre el SHA exacto del candidato;
3. ZIP inspeccionado, sin base de desarrollo, fuentes ni tests;
4. checklist manual de Windows completo y asociado al hash del ZIP;
5. licencias y avisos incluidos dentro de la carpeta portable;
6. changelog, notas, SBOM CycloneDX y SHA-256 presentes;
7. versión coherente en metadatos y documentación;
8. pull request revisado e integrado sin cambios posteriores no validados.

## Exclusiones

No forman parte de este cierre nuevas funciones, instalador, Microsoft Store,
Android, Web, telemetría, actualización automática ni firma Authenticode. La
firma se documentará como decisión explícita para una entrega futura; su ausencia
no bloqueará `1.0.0` siempre que los hashes y la procedencia por Git/tag sean
verificables.
