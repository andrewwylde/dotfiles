# Child dependency / ship order

```mermaid
flowchart TD
  A[PARABLE-609] --> B[PARABLE-616 identity]
  B --> B1[633 name/handle]
  B --> B2[632 file type]
  B --> B3[637 icon]
  B --> B4[638 details]
  A --> C[PARABLE-631 tree]
  A --> E[PARABLE-641 Monaco]
  E --> F[PARABLE-644 property picker]
  E --> G[PARABLE-636 bottom pane]
  A --> H[PARABLE-640 schedule reports]
```

Recommended ship order:

1. PARABLE-641 shared Monaco / Piece source editor
2. PARABLE-644 Property Picker (blocked by 641)
3. PARABLE-616 + 633/632/637/638 identity children
4. PARABLE-631 tree navigation
5. PARABLE-636 editor output bottom pane
6. PARABLE-640 schedule reports
