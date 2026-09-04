# RunUAT BuildCookRun Command Reference

Automation tool (`RunUAT.bat` on Windows, `RunUAT.sh` on Linux/Mac) is located at:
`[EngineRoot]/Engine/Build/BatchFiles/RunUAT.bat`

## Standard Packaging Commands

### 1. Windows Shipping Build (Client/Standalone)
```bash
Engine\Build\BatchFiles\RunUAT.bat BuildCookRun \
  -project="C:/Projects/MyGame/MyGame.uproject" \
  -noP4 \
  -platform=Win64 \
  -clientconfig=Shipping \
  -cook \
  -allmaps \
  -build \
  -stage \
  -pak \
  -archive \
  -archivedirectory="C:/Builds/MyGame_Win64_Shipping" \
  -clean
```

### 2. Dedicated Server & Client Build
```bash
# Server Build
Engine\Build\BatchFiles\RunUAT.bat BuildCookRun \
  -project="C:/Projects/MyGame/MyGame.uproject" \
  -noP4 \
  -platform=Win64 \
  -server \
  -serverconfig=Development \
  -cook \
  -stage \
  -pak \
  -archive \
  -archivedirectory="C:/Builds/MyGame_Server"

# Client Build
Engine\Build\BatchFiles\RunUAT.bat BuildCookRun \
  -project="C:/Projects/MyGame/MyGame.uproject" \
  -noP4 \
  -platform=Win64 \
  -client \
  -clientconfig=Development \
  -cook \
  -stage \
  -pak \
  -archive \
  -archivedirectory="C:/Builds/MyGame_Client"
```

---

## Critical Flags Breakdown

| Flag | Purpose |
| :--- | :--- |
| `-project="..."` | Absolute path to `.uproject` file. |
| `-cook` | Cooks assets for the specified target platform into platform-specific shaders/formats. |
| `-build` | Compiles source code for the specified configuration. |
| `-stage` | Copies executable and cooked content into a staged directory layout. |
| `-pak` | Packs cooked assets into compressed `.pak` / `.ucas` / `.utoc` container files. |
| `-archive` | Moves the staged build to `-archivedirectory`. |
| `-allmaps` | Cooks all valid maps found in Content directory (omit to cook only Maps in Packaging Settings). |
| `-clean` | Wipes intermediate cooked data to guarantee a fresh, artifact-free build. |
| `-compressed` | Enables runtime chunk compression (Oodle). |
