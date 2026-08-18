use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};
use serde_json::{Map, Value};
use walkdir::WalkDir;

use crate::config::Config;
use crate::install::{self, InstallMode, InstallOutcome};
use crate::library::LibraryItem;
use crate::state::{InstalledPath, State};
use crate::target::Target;

const MANAGED_PREFIX: &str = "agent-sync:";

pub fn sync(
    config: &Config,
    packs: &[&LibraryItem],
    old_state: &State,
    dry_run: bool,
) -> Result<Vec<InstalledPath>> {
    let mut installed = Vec::new();

    for target in [Target::Claude, Target::Cursor] {
        let mut target_entries: BTreeMap<String, Vec<Map<String, Value>>> = BTreeMap::new();
        for pack in packs {
            if pack.manifest.excludes(target) {
                continue;
            }
            let entries = pack
                .manifest
                .hooks
                .get(&target)
                .cloned()
                .unwrap_or_default();
            if entries.is_empty() {
                continue;
            }

            let scripts = install_scripts(config, pack, target, old_state, dry_run)?;
            let rewrites = scripts
                .iter()
                .map(|(source, destination, _)| (source.clone(), destination.clone()))
                .collect::<Vec<_>>();
            installed.extend(scripts.into_iter().map(|(source, destination, mode)| {
                InstalledPath::new(
                    source,
                    target.id(),
                    destination,
                    mode.as_str(),
                    "hooks",
                    &pack.name,
                )
            }));

            for (event, event_entries) in entries {
                let output = target_entries.entry(event.clone()).or_default();
                for (ordinal, mut entry) in event_entries.into_iter().enumerate() {
                    rewrite_commands(&mut entry, &rewrites);
                    entry.insert(
                        "_as".to_owned(),
                        Value::String(format!(
                            "agent-sync:{}:{}:{event}:{ordinal}",
                            pack.name, pack.manifest.version
                        )),
                    );
                    output.push(entry);
                }
            }
        }
        merge_config(config, target, target_entries, dry_run)?;
    }

    Ok(installed)
}

pub fn verify(config: &Config, packs: &[&LibraryItem]) -> Result<bool> {
    let mut valid = true;
    for target in [Target::Claude, Target::Cursor] {
        let expected = expected_managed(config, packs, target)?;
        let config_path = target
            .hooks_config(&config.target_home)
            .context("supported hook target must have a config path")?;
        let value = read_config(&config_path)?;
        let actual = managed_entries(&value)?;
        if actual != expected {
            eprintln!(
                "ERROR hooks {target}: managed entries differ in {}",
                config_path.display()
            );
            valid = false;
        }

        for pack in packs {
            if pack.manifest.excludes(target)
                || pack
                    .manifest
                    .hooks
                    .get(&target)
                    .is_none_or(BTreeMap::is_empty)
            {
                continue;
            }
            for (_, destination, _) in script_plan(config, pack, target)? {
                if !install::path_exists(&destination) {
                    eprintln!(
                        "ERROR hooks {target}: missing script {}",
                        destination.display()
                    );
                    valid = false;
                }
            }
        }
    }
    Ok(valid)
}

pub fn remove_managed(config: &Config) -> Result<()> {
    for target in [Target::Claude, Target::Cursor] {
        merge_config(config, target, BTreeMap::new(), false)?;
    }
    Ok(())
}

pub fn expected_script_paths(config: &Config, packs: &[&LibraryItem]) -> Result<Vec<PathBuf>> {
    let mut paths = Vec::new();
    for target in [Target::Claude, Target::Cursor] {
        for pack in packs {
            if pack.manifest.excludes(target)
                || pack
                    .manifest
                    .hooks
                    .get(&target)
                    .is_none_or(BTreeMap::is_empty)
            {
                continue;
            }
            paths.extend(
                script_plan(config, pack, target)?
                    .into_iter()
                    .map(|(_, destination, _)| destination),
            );
        }
    }
    paths.sort();
    paths.dedup();
    Ok(paths)
}

fn install_scripts(
    config: &Config,
    pack: &LibraryItem,
    target: Target,
    old_state: &State,
    dry_run: bool,
) -> Result<Vec<(PathBuf, PathBuf, InstallMode)>> {
    let preferred = if target == Target::Cursor {
        InstallMode::Copy
    } else {
        InstallMode::Symlink
    };
    let mut installed = Vec::new();
    for (source, destination, _) in script_plan(config, pack, target)? {
        let outcome = install::install(
            &source,
            &destination,
            preferred,
            old_state.owns(&destination),
            dry_run,
        )?;
        match outcome {
            InstallOutcome::Installed(mode) => {
                println!(
                    "{} hooks/{} -> {} ({})",
                    if dry_run { "PLAN" } else { "SYNC" },
                    pack.name,
                    destination.display(),
                    mode.as_str()
                );
                installed.push((source, destination, mode));
            }
            InstallOutcome::SkippedForeign(reason) => bail!(
                "refusing hook script destination {}: {reason}",
                destination.display()
            ),
        }
    }
    Ok(installed)
}

fn script_plan(
    config: &Config,
    pack: &LibraryItem,
    target: Target,
) -> Result<Vec<(PathBuf, PathBuf, InstallMode)>> {
    let hooks_dir = target
        .hooks_dir(&config.target_home)
        .context("supported hook target must have a scripts directory")?;
    let mut scripts = Vec::new();
    for entry in WalkDir::new(&pack.path).follow_links(true) {
        let entry = entry.with_context(|| format!("walk Hook pack {}", pack.path.display()))?;
        if !entry.file_type().is_file() || !is_hook_script(entry.path()) {
            continue;
        }
        let relative = entry.path().strip_prefix(&pack.path)?;
        let flattened = relative.to_string_lossy().replace(['/', '\\'], "-");
        let destination = hooks_dir.join(format!("as-{}-{flattened}", pack.name));
        let mode = if target == Target::Cursor {
            InstallMode::Copy
        } else {
            InstallMode::Symlink
        };
        scripts.push((entry.path().to_path_buf(), destination, mode));
    }
    scripts.sort_by(|left, right| left.0.cmp(&right.0));
    Ok(scripts)
}

fn is_hook_script(path: &Path) -> bool {
    matches!(
        path.extension().and_then(|extension| extension.to_str()),
        Some("sh" | "py" | "js" | "mjs" | "ts")
    )
}

fn rewrite_commands(entry: &mut Map<String, Value>, rewrites: &[(PathBuf, PathBuf)]) {
    rewrite_value(&mut Value::Object(entry.clone()), rewrites, entry);
}

fn rewrite_value(
    value: &mut Value,
    rewrites: &[(PathBuf, PathBuf)],
    root: &mut Map<String, Value>,
) {
    fn visit(value: &mut Value, rewrites: &[(PathBuf, PathBuf)], key: Option<&str>) {
        match value {
            Value::Object(object) => {
                for (name, child) in object {
                    visit(child, rewrites, Some(name));
                }
            }
            Value::Array(array) => {
                for child in array {
                    visit(child, rewrites, key);
                }
            }
            Value::String(command) if key == Some("command") => {
                for (source, destination) in rewrites {
                    let Some(file_name) = source.file_name().and_then(|name| name.to_str()) else {
                        continue;
                    };
                    let explicit_relative = format!("./{file_name}");
                    if command.contains(&explicit_relative) {
                        *command =
                            command.replace(&explicit_relative, &destination.to_string_lossy());
                    } else if command == file_name {
                        *command = destination.to_string_lossy().into_owned();
                    }
                }
            }
            _ => {}
        }
    }

    visit(value, rewrites, None);
    if let Value::Object(object) = std::mem::take(value) {
        *root = object;
    }
}

fn merge_config(
    config: &Config,
    target: Target,
    entries: BTreeMap<String, Vec<Map<String, Value>>>,
    dry_run: bool,
) -> Result<()> {
    let path = target
        .hooks_config(&config.target_home)
        .context("supported hook target must have a config path")?;
    if entries.is_empty() && !path.exists() {
        return Ok(());
    }
    if dry_run {
        let count = entries.values().map(Vec::len).sum::<usize>();
        println!(
            "PLAN hooks/{target} -> {} ({count} entries)",
            path.display()
        );
        return Ok(());
    }

    let mut root = read_config(&path)?;
    let root_object = root
        .as_object_mut()
        .context("hook config root must be a JSON object")?;
    if target == Target::Cursor && !root_object.contains_key("version") {
        root_object.insert("version".to_owned(), Value::from(1));
    }
    let hooks = root_object
        .entry("hooks")
        .or_insert_with(|| Value::Object(Map::new()))
        .as_object_mut()
        .context("hook config 'hooks' must be a JSON object")?;

    for existing in hooks.values_mut() {
        let array = existing
            .as_array_mut()
            .context("hook event value must be an array")?;
        array.retain(|entry| {
            entry
                .get("_as")
                .and_then(Value::as_str)
                .is_none_or(|tag| !tag.starts_with(MANAGED_PREFIX))
        });
    }
    hooks.retain(|_, value| value.as_array().is_none_or(|array| !array.is_empty()));

    for (event, additions) in entries {
        let array = hooks
            .entry(event)
            .or_insert_with(|| Value::Array(Vec::new()))
            .as_array_mut()
            .context("hook event value must be an array")?;
        array.extend(additions.into_iter().map(Value::Object));
    }
    write_json_atomic(&path, &root)
}

fn expected_managed(
    config: &Config,
    packs: &[&LibraryItem],
    target: Target,
) -> Result<BTreeMap<String, Vec<Value>>> {
    let mut managed: BTreeMap<String, Vec<Value>> = BTreeMap::new();
    for pack in packs {
        if pack.manifest.excludes(target) {
            continue;
        }
        let Some(events) = pack.manifest.hooks.get(&target) else {
            continue;
        };
        let scripts = script_plan(config, pack, target)?;
        let rewrites = scripts
            .into_iter()
            .map(|(source, destination, _)| (source, destination))
            .collect::<Vec<_>>();
        for (event, entries) in events {
            let output = managed.entry(event.clone()).or_default();
            for (ordinal, entry) in entries.iter().enumerate() {
                let mut entry = entry.clone();
                rewrite_commands(&mut entry, &rewrites);
                entry.insert(
                    "_as".to_owned(),
                    Value::String(format!(
                        "agent-sync:{}:{}:{event}:{ordinal}",
                        pack.name, pack.manifest.version
                    )),
                );
                output.push(Value::Object(entry));
            }
        }
    }
    Ok(managed)
}

fn managed_entries(root: &Value) -> Result<BTreeMap<String, Vec<Value>>> {
    let mut managed = BTreeMap::new();
    let Some(hooks) = root.get("hooks") else {
        return Ok(managed);
    };
    for (event, entries) in hooks
        .as_object()
        .context("hook config 'hooks' must be a JSON object")?
    {
        let entries = entries
            .as_array()
            .context("hook event value must be an array")?
            .iter()
            .filter(|entry| {
                entry
                    .get("_as")
                    .and_then(Value::as_str)
                    .is_some_and(|tag| tag.starts_with(MANAGED_PREFIX))
            })
            .cloned()
            .collect::<Vec<_>>();
        if !entries.is_empty() {
            managed.insert(event.clone(), entries);
        }
    }
    Ok(managed)
}

fn read_config(path: &Path) -> Result<Value> {
    if !path.exists() {
        return Ok(Value::Object(Map::new()));
    }
    let text = fs::read_to_string(path).with_context(|| format!("read {}", path.display()))?;
    serde_json::from_str(&text).with_context(|| format!("parse {}", path.display()))
}

fn write_json_atomic(path: &Path, value: &Value) -> Result<()> {
    let parent = path.parent().context("hook config has no parent")?;
    fs::create_dir_all(parent)
        .with_context(|| format!("create hook config parent {}", parent.display()))?;
    let temporary = parent.join(format!(".hooks.{}.tmp", std::process::id()));
    let mut text = serde_json::to_string_pretty(value)?;
    text.push('\n');
    fs::write(&temporary, text)
        .with_context(|| format!("write temporary config {}", temporary.display()))?;
    fs::rename(&temporary, path)
        .with_context(|| format!("replace hook config {}", path.display()))?;
    Ok(())
}
