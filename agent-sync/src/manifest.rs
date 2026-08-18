use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::Path;
use std::str::FromStr;

use anyhow::{Context, Result};
use serde::Deserialize;
use serde_json::{Map as JsonMap, Value as JsonValue};
use serde_yaml::Value as YamlValue;

use crate::target::Target;

#[derive(Debug, Clone, Default)]
pub struct Manifest {
    pub exclude: BTreeSet<Target>,
    pub version: String,
    pub overlays: BTreeMap<Target, Overlay>,
    pub hooks: BTreeMap<Target, BTreeMap<String, Vec<JsonMap<String, JsonValue>>>>,
}

#[derive(Debug, Clone, Default)]
pub struct Overlay {
    pub frontmatter: YamlValue,
    pub body_append: String,
}

#[derive(Debug, Deserialize, Default)]
struct RawManifest {
    #[serde(default)]
    exclude: Vec<String>,
    version: Option<String>,
    #[serde(default)]
    overlays: BTreeMap<String, RawOverlay>,
    #[serde(default)]
    hooks: BTreeMap<String, BTreeMap<String, Vec<toml::Value>>>,
}

#[derive(Debug, Deserialize, Default)]
struct RawOverlay {
    #[serde(default)]
    frontmatter: toml::Table,
    #[serde(default)]
    body_append: String,
}

impl Manifest {
    pub fn load(item_root: &Path) -> Result<Self> {
        let path = item_root.join("manifest.toml");
        if !path.exists() {
            return Ok(Self {
                version: "1.0.0".to_owned(),
                ..Self::default()
            });
        }

        let text = fs::read_to_string(&path)
            .with_context(|| format!("read Manifest {}", path.display()))?;
        let raw: RawManifest =
            toml::from_str(&text).with_context(|| format!("parse Manifest {}", path.display()))?;

        let mut manifest = Self {
            version: raw.version.unwrap_or_else(|| "1.0.0".to_owned()),
            ..Self::default()
        };

        for target in raw.exclude {
            manifest.exclude.insert(Target::from_str(&target)?);
        }
        for (target, overlay) in raw.overlays {
            let target = Target::from_str(&target)?;
            let json = serde_json::to_value(&overlay.frontmatter)
                .context("convert overlay frontmatter via JSON")?;
            let frontmatter: YamlValue =
                serde_json::from_value(json).context("decode overlay frontmatter as YAML value")?;
            if !frontmatter.is_mapping() && !frontmatter.is_null() {
                anyhow::bail!("overlays.{target}.frontmatter must be a table");
            }
            manifest.overlays.insert(
                target,
                Overlay {
                    frontmatter: if frontmatter.is_null() {
                        YamlValue::Mapping(serde_yaml::Mapping::new())
                    } else {
                        frontmatter
                    },
                    body_append: overlay.body_append,
                },
            );
        }
        for (target, events) in raw.hooks {
            let target = Target::from_str(&target)?;
            let mut converted_events = BTreeMap::new();
            for (event, entries) in events {
                let mut converted_entries = Vec::with_capacity(entries.len());
                for entry in entries {
                    let value =
                        serde_json::to_value(entry).context("convert hook entry to JSON")?;
                    let object = value.as_object().cloned().with_context(|| {
                        format!("hooks.{target}.{event} entry must be an object")
                    })?;
                    converted_entries.push(object);
                }
                converted_events.insert(event, converted_entries);
            }
            manifest.hooks.insert(target, converted_events);
        }

        Ok(manifest)
    }

    #[must_use]
    pub fn excludes(&self, target: Target) -> bool {
        self.exclude.contains(&target)
    }

    #[must_use]
    pub fn overlay(&self, target: Target) -> Overlay {
        self.overlays.get(&target).cloned().unwrap_or_default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::tempdir;

    #[test]
    fn loads_nested_cursor_overlay() {
        let dir = tempdir().unwrap();
        fs::write(
            dir.path().join("manifest.toml"),
            r#"
[overlays.cursor]
body_append = "\ncursor only\n"

[overlays.cursor.frontmatter]
disable-model-invocation = true

[overlays.cursor.frontmatter.metadata]
source = "cursor"
"#,
        )
        .unwrap();
        let m = Manifest::load(dir.path()).unwrap();
        let o = m.overlay(Target::Cursor);
        eprintln!("frontmatter = {:?}", o.frontmatter);
        assert!(
            o.frontmatter.is_mapping(),
            "expected mapping, got {:?}",
            o.frontmatter
        );
        assert!(o.body_append.contains("cursor only"));
    }
}
