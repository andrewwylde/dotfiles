# Scaffold inventory (preserve behavior / replace contracts)

| Area | Preserve (behavior/tests) | Replace (contracts) |
|------|---------------------------|---------------------|
| Monaco | `monaco-sql-editor/*` lazy load, workers, themes, hints, tokens | Shared `PieceSourceEditor` under `domains/parables/` (PARABLE-641) |
| Property picker | Token picker/chips/layout | Extension seam owned by PARABLE-644 |
| Tree | `TreeList` presentation | Hierarchy builder owned by PARABLE-631 |
| Bottom pane | `BottomPane` presentation | Results/History/Details contracts owned by PARABLE-636 |
| Identity | Piece / ResourceWorkspace visuals | PARABLE-616 + children |
| Types/SDK mirrors | — | Delete `plots.types.ts` persisted shapes, `ParablePackageLike`, `ParableTemplatesSdkLike` |
| Persistence demos | — | Delete/replace localStorage parable/demo state before production |

Never promote temporary GraphQL paths under `platform-schemas/schemas/`.
Current main uses TypeScript schema under `platform-schemas/services/*/src/`.
