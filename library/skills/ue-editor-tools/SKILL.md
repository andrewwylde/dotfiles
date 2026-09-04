---
name: ue-editor-tools
description: "Use when extending the Unreal Editor with editor tool, editor utility widget, Blutility, detail customization, property customization, editor mode, asset editor, editor subsystem, editor extension, UToolMenus, or scripted asset operations. For Slate fundamentals, see ue-ui-umg-slate. For module build config, see ue-module-build-system."
metadata:
  version: "2026.1.0"
  engine: unreal
  category: editor
  difficulty: advanced
---

# UE Editor Tools

You are an expert in extending the Unreal Editor with custom tools and workflows. Editor extensions improve developer productivity and enforce project conventions.

## Tool Categories

| Tool Type | Purpose | Common Use Cases |
|-----------|---------|------------------|
| **Editor Utility Widget** | UMG panel from editor right-click | Batch renaming, asset validation |
| **Blutility** | UAssetActionUtility or UActorActionUtility | Level validation, mesh decimation |
| **Detail Customization** | Customize Details panel for types | Hide/show properties based on context |
| **Property Customization** | Control how properties render/validate | Custom vector editors, enum dropdowns |
| **Editor Subsystem** | Global editor state management | Project-wide tool coordination |
| **UToolMenus** | Extend editor menus/toolbars | Add custom actions to File/Edit menus |
| **Editor Mode** | Custom interaction modes (Place, Landscape) | Terrain painting, custom placement tools |
| **Asset Editor** | Custom editor for asset types | Curve editor, material graph |

## Key Implementation Patterns

### 1. Editor Utility Widget
```cpp
UCLASS()
class UMyUtilityWidget : public UEditorUtilityWidget
{
    GENERATED_BODY()

public:
    UFUNCTION(Button)
    void ValidateSelectedAssets()
    {
        TArray<UObject*> Selected = GetSelectedAssets();
        for (UObject* Asset : Selected)
        {
            if (!IsValidAsset(Asset))
            {
                UE_LOG(LogTemp, Warning, TEXT("Invalid asset: %s"), *Asset->GetName());
            }
        }
    }
};
```

### 2. Blutility for Asset Processing
```cpp
UCLASS()
class UAssetValidator : public UAssetActionUtility
{
    GENERATED_BODY()

public:
    UFUNCTION(CallInEditor, Button)
    void ValidateAllStaticMeshes()
    {
        TArray<UStaticMesh*> Meshes = GetAssetsOfClass<UStaticMesh>();
        for (UStaticMesh* Mesh : Meshes)
        {
            if (Mesh->GetNumLODs() == 0)
            {
                AddError(FString::Printf(TEXT("Mesh %s missing LODs"), *Mesh->GetName()));
            }
        }
    }
};
```

### 3. Detail Customization
```cpp
UCLASS()
class FMyDetailCustomization : public IDetailCustomization
{
public:
    static TSharedRef<IDetailCustomization> MakeInstance()
    {
        return MakeShareable(new FMyDetailCustomization());
    }

    virtual void CustomizeDetails(IDetailLayoutBuilder& DetailBuilder) override
    {
        IDetailCategoryBuilder& MyCategory = DetailBuilder.EditCategory("My Settings");
        MyCategory.AddProperty(GET_MEMBER_NAME_CHECKED(FMyData, bEnableFeature));
        MyCategory.AddCustomRow(TEXT("Advanced Settings"))
            .ValueContent()
            [
                SNew(SCheckBox)
                .IsChecked(this, &FMyDetailCustomization::IsAdvancedChecked)
                .OnCheckStateChanged(this, &FMyDetailCustomization::OnAdvancedToggled)
            ];
    }
};
```

### 4. Property Customization for Validation
```cpp
UCLASS()
class FMyVectorProperty : public IPropertyTypeCustomization
{
public:
    static TSharedRef<IPropertyTypeCustomization> MakeInstance()
    {
        return MakeShareable(new FMyVectorProperty());
    }

    virtual void CustomizeHeader(TSharedRef<IPropertyHandle> PropertyHandle,
                                FDetailWidgetRow& HeaderRow,
                                IPropertyTypeCustomizationUtils& CustomizationUtils) override
    {
        HeaderRow.NameContent()
        [
            PropertyHandle->CreatePropertyNameWidget()
        ]
        .ValueContent()
        .MinDesiredWidth(125)
        .MaxDesiredWidth(400)
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot()
            .AutoWidth()
            [
                SNew(SEditableTextBox)
                .Text(this, &FMyVectorProperty::GetX)
                .OnTextCommitted(this, &FMyVectorProperty::OnXCommitted)
            ]
            // Similar for Y/Z...
        ];
    }
};
```

## In-Engine MCP Integration

Use `unreal-editor-mcp` to expose editor functions as queryable resources:
- `get_selected_assets` — returns array of asset paths
- `execute_blutility` — run Blutility with parameters
- `modify_detail_panel` — inject custom UI into Details tab

## Files

- Create: `editor-tool-patterns.md`
- References: `references/editor-subsystems.md`, `references/blutility-patterns.md`